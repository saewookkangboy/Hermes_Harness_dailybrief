"""뉴스레터 품질 게이트 — 신선도·보일러플레이트·CTA·발행 가능 여부 (결정적)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.content_quality import Insight
from lib.newsletter_cta import cta_failures
from lib.newsletter_issue_ledger import recent_excluding
from lib.newsletter_quality import load_newsletter_config
from lib.newsletter_select import is_unsafe_insight

WORKDIR = Path.home() / "hermes-content-studio"


def banned_boilerplate(text: str, cfg: dict | None = None) -> list[str]:
    c = cfg or load_newsletter_config()
    bans = c.get("boilerplate_ban") or []
    hits = []
    for ban in bans:
        if ban and ban in text:
            hits.append(f"boilerplate:{ban}")
    # Pattern-based meta leads
    if re.search(r"\d+번째\s*인사이트", text):
        hits.append("boilerplate:nth_insight_meta")
    if "실무 실무" in text:
        hits.append("boilerplate:dup_silmu")
    return hits


def assert_freshness(stamp: str, md_text: str, cfg: dict | None = None) -> list[str]:
    """최근 호와 동일 제목/히어로 반복 검사."""
    c = cfg or load_newsletter_config()
    failures: list[str] = []
    recent = recent_excluding(stamp, c)
    m = re.search(r"\*\*권장 제목:\*\*\s*`([^`]+)`", md_text)
    subject = m.group(1).strip() if m else ""
    if subject and any(r.get("subject") == subject for r in recent):
        failures.append(f"stale_subject:{subject}")
    stale = (c.get("title_integrity") or {}).get("stale_korean_titles") or []
    if subject:
        for s in stale:
            if s and (subject == s or subject.startswith(s + " —") or subject.startswith(s + ",")):
                failures.append(f"stale_korean_subject:{subject}")
    hero_m = re.search(r"## 오늘의 1가지\n\n(.+?)\n\n---", md_text, re.S)
    hero = hero_m.group(1).strip() if hero_m else ""
    if "SEO·AEO·GEO 인용" in hero:
        failures.append("hero_process_leak")
    # Repeated / near-duplicate sentences in hero (density)
    if hero:
        from lib.newsletter_prose import sentence_similar

        sents = [s.strip() for s in re.split(r"(?<=[.!?。])\s+", hero) if s.strip()]
        norms = [re.sub(r"\s+", "", s.lower())[:36] for s in sents]
        if len(norms) >= 2 and len(norms) != len(set(norms)):
            failures.append("hero_duplicate_sentences")
        for i, a in enumerate(sents):
            for b in sents[i + 1 :]:
                if sentence_similar(a, b, threshold=0.72):
                    failures.append("hero_near_duplicate_sentences")
                    break
            else:
                continue
            break
    body = md_text
    if "## 품질 메모" in body:
        body = body.split("## 품질 메모", 1)[0]
    failures.extend(banned_boilerplate(body, c))
    if re.search(r"(?i)undress|nsfw|deepnude|nudify", body):
        failures.append("unsafe_content")
    return failures


def assert_cta_https(md_text: str) -> list[str]:
    return cta_failures(md_text)


def assert_title_body_consistency(md_text: str) -> list[str]:
    """권장 제목 키워드가 Hero에 전혀 없으면 실패."""
    m = re.search(r"\*\*권장 제목:\*\*\s*`([^`]+)`", md_text)
    if not m:
        return ["missing_winner_subject"]
    subject = m.group(1)
    hero_m = re.search(r"## 오늘의 1가지\n\n(.+?)\n\n---", md_text, re.S)
    hero = hero_m.group(1) if hero_m else ""
    # Use significant tokens from subject (hangul/latin words length>=2)
    tokens = re.findall(r"[A-Za-zAEO]{2,}|[가-힣]{2,}", subject)
    tokens = [t for t in tokens if t not in {"지금", "손댈", "곳은", "실무", "체크리스트", "분이면", "돼요"}]
    if not tokens:
        return []
    if not any(t in hero for t in tokens[:4]):
        return [f"subject_hero_mismatch:{subject}"]
    return []


def filter_safe_insights(insights: list[Insight], cfg: dict | None = None) -> list[Insight]:
    c = cfg or load_newsletter_config()
    return [i for i in insights if not is_unsafe_insight(i, c)]


def publish_status_path(stamp: str) -> Path:
    return WORKDIR / "content" / "packages" / f"{stamp}_newsletter-publish.json"


def evaluate_publishability(stamp: str, cfg: dict | None = None) -> dict[str, Any]:
    c = cfg or load_newsletter_config()
    failures: list[str] = []
    nls = [
        p
        for p in sorted(
            (WORKDIR / "content" / "newsletter").glob(f"{stamp}_newsletter_*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if "title-image" not in p.name
    ]
    if not nls:
        failures.append("missing_newsletter_md")
        return _status_payload(stamp, False, failures)

    text = nls[0].read_text(encoding="utf-8")
    failures.extend(assert_freshness(stamp, text, c))
    failures.extend(assert_cta_https(text))
    failures.extend(assert_title_body_consistency(text))

    paste = WORKDIR / "content" / "packages" / f"{stamp}_newsletter-paste.md"
    if not paste.exists():
        failures.append("missing_paste")
    else:
        pt = paste.read_text(encoding="utf-8")
        for sec in ("## §1 제목", "## §5 LinkedIn", "## §6 CTA URL", "## §7"):
            if sec not in pt:
                failures.append(f"paste_missing:{sec}")

    li = WORKDIR / "content" / "linkedin" / f"{stamp}_newsletter-article.md"
    if not li.exists():
        failures.append("missing_linkedin")

    img = WORKDIR / "content" / "newsletter" / f"{stamp}_title-image-16x9.md"
    if not img.exists():
        failures.append("missing_title_image_prompt")

    # Length band (chars) — longform email
    body = text.split("## 30초 TLDR", 1)[-1] if "## 30초 TLDR" in text else text
    if "## 품질 메모" in body:
        body = body.split("## 품질 메모", 1)[0]
    chars = len(re.sub(r"\s+", " ", body))
    if chars < 600:
        failures.append(f"body_too_short:{chars}")
    if chars > 12000:
        failures.append(f"body_too_long:{chars}")

    return _status_payload(stamp, not failures, failures)


def _status_payload(stamp: str, publishable: bool, failures: list[str]) -> dict[str, Any]:
    return {
        "stamp": stamp,
        "publishable": publishable,
        "failures": failures,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": 1,
    }


def write_publish_status(stamp: str, cfg: dict | None = None) -> Path:
    payload = evaluate_publishability(stamp, cfg)
    path = publish_status_path(stamp)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def is_publishable(stamp: str) -> bool:
    path = publish_status_path(stamp)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return bool(data.get("publishable"))
    except (json.JSONDecodeError, OSError):
        return False
