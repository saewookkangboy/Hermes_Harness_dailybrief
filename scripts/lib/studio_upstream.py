"""Shared upstream loaders for Hermes sibling studios (Tier 1)."""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

CONTENT_STUDIO = Path.home() / "hermes-content-studio"
RESEARCH_DIR = CONTENT_STUDIO / "content" / "research"
BLOG_DIR = CONTENT_STUDIO / "content" / "blog"
WIKI_CONCEPTS_DIR = CONTENT_STUDIO / "content" / "wiki" / "concepts"


@dataclass
class BriefInsight:
    index: int
    headline: str
    korean_title: str
    research_area: str
    summary: str
    insight: str
    usage: str
    channel: str
    source_url: str
    marketer_view: str = ""


@dataclass
class WikiConcept:
    topic_key: str
    title: str
    summary: str
    updated_at: str
    sources: list[str] = field(default_factory=list)


@dataclass
class SeoAuditResult:
    file_path: Path
    title: str
    scores: dict[str, int]
    overall: int
    issues: list[str]
    recommendations: list[str]
    checks: dict[str, bool] = field(default_factory=dict)


def parent_studio() -> Path:
    import os

    raw = os.environ.get("HERMES_PARENT_STUDIO", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return CONTENT_STUDIO


def brief_path(stamp: str, parent: Path | None = None) -> Path:
    root = parent or parent_studio()
    return root / "content" / "research" / f"{stamp}_brief.md"


def load_brief_text(stamp: str, parent: Path | None = None) -> str:
    path = brief_path(stamp, parent)
    if not path.exists():
        raise FileNotFoundError(f"Brief SoT 없음: {path}")
    return path.read_text(encoding="utf-8")


def _field(block: str, label: str) -> str:
    pattern = rf"- \*\*{re.escape(label)}:\*\* (.+)"
    match = re.search(pattern, block)
    return match.group(1).strip() if match else ""


def parse_brief_insights(text: str) -> list[BriefInsight]:
    section = text
    marker = "## Top 7 인사이트"
    if marker in text:
        section = text.split(marker, 1)[1]
        for stop in ("## 심층 분석", "## 콘텐츠 캘린더", "## 데이터 포인트"):
            if stop in section:
                section = section.split(stop, 1)[0]

    blocks = re.split(r"\n### (\d+)\. ", section)
    insights: list[BriefInsight] = []
    for i in range(1, len(blocks), 2):
        idx = int(blocks[i])
        body = blocks[i + 1]
        headline = body.split("\n", 1)[0].strip()
        insights.append(
            BriefInsight(
                index=idx,
                headline=headline,
                korean_title=_field(body, "한국어 제목") or headline[:80],
                research_area=_field(body, "리서치 영역"),
                summary=_field(body, "내용 요약"),
                insight=_field(body, "Insight 도출"),
                usage=_field(body, "활용 방법"),
                channel=_field(body, "콘텐츠 소재"),
                source_url=_field(body, "출처"),
                marketer_view=_field(body, "마케터 관점"),
            )
        )
    return insights


def load_brief_insights(stamp: str, parent: Path | None = None) -> list[BriefInsight]:
    return parse_brief_insights(load_brief_text(stamp, parent))


def executive_summary(text: str) -> str:
    match = re.search(r"## Executive Summary\n(.+?)\n\n", text, re.S)
    return match.group(1).strip() if match else ""


def llm_platform_pulse(text: str) -> list[str]:
    section = ""
    if "### LLM 플랫폼 펄스" in text:
        section = text.split("### LLM 플랫폼 펄스", 1)[1]
        section = section.split("\n##", 1)[0]
    return [
        line.strip()[2:].strip()
        for line in section.splitlines()
        if line.strip().startswith("- **")
    ]


def lecture_insights(insights: list[BriefInsight]) -> list[BriefInsight]:
    picked = [i for i in insights if "lecture" in i.channel.lower()]
    pool = picked if len(picked) >= 3 else list(insights)
    seen: set[str] = set()
    result: list[BriefInsight] = []
    for item in pool:
        key = item.korean_title.strip() or item.headline.strip()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= 5:
            break
    return result


def parse_pulse_line(line: str) -> tuple[str, str]:
    """Parse '- **OpenAI · ChatGPT:** body' → (name, body)."""
    text = line.strip()
    if text.startswith("- "):
        text = text[2:].strip()
    match = re.match(r"\*\*(.+?)\*\*:\s*(.+)", text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    if ":**" in text:
        left, right = text.split(":**", 1)
        return left.replace("*", "").strip(), right.strip()
    return text[:40], text


def load_wiki_concepts(parent: Path | None = None) -> list[WikiConcept]:
    root = parent or parent_studio()
    concepts_dir = root / "content" / "wiki" / "concepts"
    if not concepts_dir.exists():
        return []

    concepts: list[WikiConcept] = []
    for path in sorted(concepts_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        topic_key = path.stem
        updated_at = ""
        fm = re.match(r"^---\n(.*?)\n---", text, re.S)
        if fm:
            for line in fm.group(1).splitlines():
                if line.startswith("updated_at:"):
                    updated_at = line.split(":", 1)[1].strip()
            text = text[fm.end() :]

        title_match = re.search(r"^# (.+)$", text, re.M)
        title = title_match.group(1).strip() if title_match else topic_key
        summary_match = re.search(r"## 최신 요약\n(.+?)(?:\n\n|\n## )", text, re.S)
        summary = summary_match.group(1).strip() if summary_match else title
        sources = re.findall(r"https?://[^\s\)]+", text)
        concepts.append(
            WikiConcept(
                topic_key=topic_key,
                title=title,
                summary=summary[:200],
                updated_at=updated_at,
                sources=sources[:5],
            )
        )
    return concepts


def find_blog_html(stamp: str, parent: Path | None = None) -> Path | None:
    root = parent or parent_studio()
    blog_dir = root / "content" / "blog"
    if not blog_dir.exists():
        return None
    matches = sorted(blog_dir.glob(f"{stamp}_blog_*.html"))
    return matches[0] if matches else None


def list_blog_html(stamp: str, parent: Path | None = None) -> list[Path]:
    root = parent or parent_studio()
    blog_dir = root / "content" / "blog"
    if not blog_dir.exists():
        return []
    return sorted(blog_dir.glob(f"{stamp}_blog_*.html"))


def _extract_meta(html: str, name: str) -> str:
    pattern = rf'<meta name="{name}" content="([^"]*)"'
    match = re.search(pattern, html, re.I)
    return match.group(1).strip() if match else ""


def _extract_title(html: str) -> str:
    match = re.search(r"<title>([^<]+)</title>", html, re.I)
    return match.group(1).strip() if match else ""


def audit_blog_html(path: Path) -> SeoAuditResult:
    html = path.read_text(encoding="utf-8")
    title = _extract_title(html)
    meta_desc = _extract_meta(html, "description")
    h1_count = len(re.findall(r"<h1[\s>]", html, re.I))
    h2_count = len(re.findall(r"<h2[\s>]", html, re.I))
    has_canonical = bool(re.search(r'rel="canonical"', html, re.I))
    has_faq = "FAQPage" in html
    has_json_ld = "application/ld+json" in html
    has_geo = bool(re.search(r"geo-quote|class=\"geo", html, re.I))

    checks = {
        "title": bool(title),
        "meta_description": 30 <= len(meta_desc) <= 170,
        "h1": h1_count >= 1,
        "h2": h2_count >= 3,
        "canonical": has_canonical,
        "faq_schema": has_faq,
        "json_ld": has_json_ld,
        "geo_block": has_geo,
    }

    issues: list[str] = []
    recommendations: list[str] = []
    if not checks["title"]:
        issues.append("HTML title 없음")
        recommendations.append("`<title>` 태그 추가")
    if not checks["meta_description"]:
        issues.append(f"meta description 부적절 ({len(meta_desc)} chars)")
        recommendations.append("meta description 50–160자로 조정")
    if not checks["h1"]:
        issues.append("H1 없음")
        recommendations.append("`<h1>` 1개 추가")
    if not checks["h2"]:
        issues.append(f"H2 부족 ({h2_count}개)")
        recommendations.append("H2 섹션 3개 이상 추가")
    if not checks["canonical"]:
        issues.append("canonical URL 없음")
        recommendations.append("`<link rel=\"canonical\">` 추가")
    if not checks["faq_schema"]:
        issues.append("FAQPage schema 없음")
        recommendations.append("FAQ JSON-LD (AEO) 추가")
    if not checks["json_ld"]:
        issues.append("JSON-LD 없음")
        recommendations.append("Article/FAQ JSON-LD 추가")
    if not checks["geo_block"]:
        recommendations.append("GEO 인용 블록(geo-quote) 추가 권장")

    weights = {
        "title": 15,
        "meta_description": 15,
        "h1": 15,
        "h2": 15,
        "canonical": 10,
        "faq_schema": 15,
        "json_ld": 10,
        "geo_block": 5,
    }
    overall = sum(weights[k] for k, ok in checks.items() if ok)
    scores = {
        "Technical": sum(
            weights[k] for k in ("title", "canonical", "json_ld") if checks[k]
        ),
        "Content": sum(weights[k] for k in ("meta_description", "h1", "h2") if checks[k]),
        "AEO": sum(weights[k] for k in ("faq_schema", "geo_block") if checks[k]),
    }

    return SeoAuditResult(
        file_path=path,
        title=title,
        scores=scores,
        overall=overall,
        issues=issues,
        recommendations=recommendations,
        checks=checks,
    )


def load_intel_snapshot(studio_root: Path) -> dict[str, Any]:
    path = studio_root / ".harness" / "intel-snapshot.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_intel_snapshot(studio_root: Path, stamp: str, data: dict[str, Any]) -> Path:
    path = studio_root / ".harness" / "intel-snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"date": stamp, **data}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def detect_intel_changes(
    current: dict[str, str], previous: dict[str, Any]
) -> list[str]:
    if not previous:
        return ["초기 스냅샷 — 다음 실행부터 diff 감지"]
    prev_signals = previous.get("signals", {})
    changes: list[str] = []
    for key, value in current.items():
        old = prev_signals.get(key, "")
        if old and old != value:
            changes.append(f"{key}: 변경 감지")
        elif not old:
            changes.append(f"{key}: 신규 신호")
    return changes or ["변화 없음 (동일 신호)"]


# ── Tier 2: Personal · Wiki · Dev ─────────────────────────────


def find_mail_digest(stamp: str, parent: Path | None = None) -> Path | None:
    root = parent or parent_studio()
    personal = root / "content" / "personal"
    if not personal.is_dir():
        return None
    exact = personal / f"{stamp}_mail-digest.md"
    if exact.exists():
        return exact
    digests = sorted(personal.glob("*_mail-digest.md"), reverse=True)
    return digests[0] if digests else None


def load_inbox_candidates(stamp: str, parent: Path | None = None) -> list[dict[str, Any]]:
    root = parent or parent_studio()
    path = root / "content" / "personal" / "_inbox_candidates.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    items = data.get("candidates", [])
    dated = [c for c in items if c.get("stamp") == stamp and c.get("status") == "pending"]
    if dated:
        return dated
    return [c for c in items if c.get("status") == "pending"][:10]


def parse_mail_digest_summary(text: str) -> tuple[int, str]:
    count = 0
    m = re.search(r"\*\*건수:\*\*\s*(\d+)", text)
    if m:
        count = int(m.group(1))
    if "## ⚠️ 오류" in text:
        err_m = re.search(r"## ⚠️ 오류\n\n(.+?)(?:\n\n|$)", text, re.S)
        err = err_m.group(1).strip() if err_m else "Mail 오류"
        return count, f"Mail digest 오류 — {err[:120]}"
    subjects = re.findall(r"^### \d+\. (.+)$", text, re.M)
    if subjects:
        return count or len(subjects), f"수신 {count or len(subjects)}건 · 주요: {subjects[0][:60]}"
    return count, "받편함 요약 (mail-digest upstream)"


def build_action_items_from_candidates(candidates: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        text = (c.get("text") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        src = c.get("source", "inbox")
        short = text[:100] + ("…" if len(text) > 100 else "")
        actions.append(f"- [ ] ({src}) {short}")
        if len(actions) >= 8:
            break
    if not actions:
        actions = [
            "- [ ] 긴급 회신 필요 메일 확인",
            "- [ ] follow-up 일정 정리",
        ]
    return actions


def run_wiki_upstream(
    parent: Path | None = None,
    *,
    stamp: str,
    seed: bool = True,
) -> dict[str, Any]:
    """Lint + optional seed from parent content-studio wiki."""
    root = parent or parent_studio()
    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))

    from lib.wiki_curator import lint_wiki, scan_ingest_queue, wiki_status  # noqa: WPS433

    result: dict[str, Any] = {"stamp": stamp, "parent": str(root)}
    result["status"] = wiki_status()
    if seed:
        try:
            from lib.wiki_seed import seed_from_brief_graph  # noqa: WPS433

            result["seed"] = seed_from_brief_graph()
        except Exception as exc:  # noqa: BLE001
            result["seed"] = {"error": str(exc)}
    result["lint"] = lint_wiki(write_report=False)
    result["ingest"] = scan_ingest_queue()
    return result


def load_active_features(parent: Path | None = None) -> list[dict[str, Any]]:
    root = parent or parent_studio()
    path = root / ".harness" / "feature_list.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    features = data.get("features", [])
    active = [f for f in features if f.get("status") == "in_progress"]
    if active:
        return active
    pending = [f for f in features if f.get("status") in ("not_started", "blocked")]
    pending.sort(key=lambda f: f.get("priority", 99))
    if pending:
        return pending[:3]
    sorted_all = sorted(features, key=lambda f: f.get("priority", 99))
    return sorted_all[:1] if sorted_all else []


def load_progress_priority(parent: Path | None = None) -> str:
    root = parent or parent_studio()
    path = root / ".harness" / "progress.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"## 현재 최우선\n\n(.+?)(?:\n\n## |\Z)", text, re.S)
    if not m:
        return ""
    return m.group(1).strip().split("\n")[0][:200]


def load_studio_projects(parent: Path | None = None) -> dict[str, str]:
    root = parent or parent_studio()
    path = root / "config" / "studio.yaml"
    if not path.exists():
        return {}
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    projects = data.get("projects") or {}
    return {str(k): str(v) for k, v in projects.items()}


def pick_dev_target(
    projects: dict[str, str],
    feature: dict[str, Any] | None,
) -> tuple[str, str]:
    if not projects:
        return str(parent_studio()), "hermes-content-studio"
    default_key = "vibe-coding-navigator"
    if feature and "wiki" in feature.get("area", "").lower():
        default_key = "marketers-brain"
    key = default_key if default_key in projects else next(iter(projects))
    return projects[key], key


# ── Tier 3: Delivery · Social ─────────────────────────────────


def find_linkedin_post(stamp: str, parent: Path | None = None) -> Path | None:
    root = parent or parent_studio()
    li_dir = root / "content" / "linkedin"
    if not li_dir.is_dir():
        return None
    matches = sorted(li_dir.glob(f"{stamp}_linkedin_*.md"))
    return matches[0] if matches else None


def find_linkedin_context(stamp: str, parent: Path | None = None) -> Path | None:
    root = parent or parent_studio()
    pkg = root / "content" / "packages"
    if not pkg.is_dir():
        return None
    matches = sorted(pkg.glob(f"{stamp}_linkedin-context*.md"))
    return matches[0] if matches else None


def parse_linkedin_post(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    hook = lines[0] if lines else ""
    hook2 = lines[1] if len(lines) > 1 else ""
    cta = ""
    for ln in lines:
        if "?" in ln or "댓글" in ln or "공유" in ln:
            cta = ln
            break
    hashtags = re.findall(r"#\w+", text)
    body_lines = [
        ln for ln in lines
        if not ln.startswith("#") and not ln.startswith(">") and not ln.startswith("```")
        and not ln.startswith("---")
    ]
    char_count = len("\n".join(body_lines[:20]))
    bullets = [ln for ln in lines if ln.startswith("→")]
    return {
        "hook": hook,
        "hook2": hook2,
        "cta": cta or "팀에서 AX/에이전트, 어디부터 시작하고 계세요?",
        "hashtags": hashtags[:5],
        "char_count": char_count,
        "bullets": bullets[:5],
    }


def parse_linkedin_context(text: str) -> dict[str, Any]:
    topic_m = re.search(r"# LinkedIn 컨텍스트 — (.+)", text)
    topic = topic_m.group(1).strip() if topic_m else "LinkedIn"
    bullets = re.findall(r"^- (.+)$", text, re.M)
    bullet_items = [b for b in bullets if b.startswith("→") or "한국" in b or "Claude" in b][:5]
    sources = re.findall(r"https?://[^\s\)]+", text)
    cta_m = re.search(r"## CTA\n(.+)", text)
    cta = cta_m.group(1).strip() if cta_m else ""
    return {"topic": topic, "bullets": bullet_items, "sources": sources[:5], "cta": cta}


def load_channel_metrics(parent: Path | None = None) -> dict[str, Any]:
    root = parent or parent_studio()
    path = root / ".harness" / "channel-metrics.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_content_calendar(stamp: str, parent: Path | None = None) -> list[dict[str, str]]:
    text = load_brief_text(stamp, parent)
    section = ""
    if "## 콘텐츠 캘린더" in text:
        section = text.split("## 콘텐츠 캘린더", 1)[1]
        section = section.split("\n##", 1)[0]
    rows: list[dict[str, str]] = []
    for line in section.splitlines():
        if not line.startswith("|") or "---" in line or "요일" in line:
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 4:
            rows.append({
                "day": parts[0],
                "channel": parts[1],
                "topic": parts[2],
                "ref": parts[3],
            })
    return rows


def delivery_insights(insights: list[BriefInsight]) -> list[BriefInsight]:
    b2b = [
        i for i in insights
        if any(k in i.channel.lower() for k in ("lecture", "blog", "linkedin"))
        or "B2B" in i.research_area
        or "대한민국" in i.research_area
    ]
    if len(b2b) >= 3:
        return b2b[:5]
    return insights[:5]
