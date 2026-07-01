"""자연스러움(인간다움) 결정적 스코어 — regex + 구조 신호."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from lib.content_quality_config import naturalness_min_score
from lib.voice_style_audit import (
    audit_ai_tells,
    audit_instagram_caption,
    audit_linkedin_post_body,
    audit_mid_truncation,
)

WORKDIR = Path.home() / "hermes-content-studio"
FIXTURES_DIR = WORKDIR / "tests" / "fixtures" / "voice"

_FIRST_PERSON = re.compile(r"(저는|제가|돌려보니|현장에서|컨설팅 현장)")
_HAEYO = re.compile(r"(해요|돼요|예요|이에요|세요|까요)")
_FORMAL = re.compile(r"(습니다|됩니다|입니다)")
_ROBOTIC_OPENERS = re.compile(r"^(또한|따라서|나아가|게다가|아울러),?\s", re.M)


@dataclass
class NaturalnessScore:
    channel: str
    score: int
    flags: dict[str, bool] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.score >= naturalness_min_score(self.channel)


def _sentence_endings(text: str) -> tuple[int, int]:
    """해요체 vs 합니다 비율 (문장 수 기준)."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。])\s+", text) if s.strip()]
    if not sentences:
        return 0, 0
    haeyo = sum(1 for s in sentences if _HAEYO.search(s))
    formal = sum(1 for s in sentences if _FORMAL.search(s))
    return haeyo, formal


def score_naturalness(text: str, *, channel: str) -> NaturalnessScore:
    """0–100 자연스러움 스코어 (결정적)."""
    body = (text or "").strip()
    result = NaturalnessScore(channel=channel, score=50)
    if not body:
        result.issues.append("빈 텍스트")
        result.score = 0
        return result

    issues: list[str] = []
    issues.extend(audit_mid_truncation(body))
    issues.extend(audit_ai_tells(body))
    result.issues = issues

    if channel == "linkedin":
        issues.extend(audit_linkedin_post_body(body))
        hook = "\n".join(body.splitlines()[:6])
        result.flags["first_person"] = bool(_FIRST_PERSON.search(hook))
        result.flags["question_cta"] = "?" in body[-200:]
        result.flags["bullet_arrows"] = body.count("→") >= 3
        haeyo, formal = _sentence_endings(body)
        result.flags["haeyo_register"] = haeyo >= formal and haeyo >= 2
        result.flags["no_robotic_opener"] = not _ROBOTIC_OPENERS.search(body)

        score = 40
        if result.flags["first_person"]:
            score += 15
        if result.flags["question_cta"]:
            score += 12
        if result.flags["bullet_arrows"]:
            score += 10
        if result.flags["haeyo_register"]:
            score += 15
        if result.flags["no_robotic_opener"]:
            score += 8
        if issues:
            score -= min(30, 8 * len(issues))
        result.score = max(0, min(100, score))

    elif channel == "instagram":
        issues.extend(audit_instagram_caption(body))
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        hook_text = ""
        for ln in lines:
            stripped = re.sub(r"^[💬📌💡👉\s]+", "", ln).strip()
            if stripped and not stripped.startswith("→"):
                hook_text = stripped
                break
        result.flags["caption_hook"] = len(hook_text) >= 18
        haeyo, formal = _sentence_endings(body)
        result.flags["haeyo_register"] = haeyo >= max(1, formal)
        emoji_count = len(re.findall(r"[\U0001F300-\U0001FAFF💬📌💡👉]", body))
        result.flags["minimal_emoji"] = emoji_count <= 6
        result.flags["save_cta"] = "저장" in body and "공유" in body
        result.flags["question_cta"] = "?" in body[-220:]

        score = 32
        if result.flags["caption_hook"]:
            score += 20
        if result.flags["haeyo_register"]:
            score += 20
        if result.flags["minimal_emoji"]:
            score += 10
        if result.flags["save_cta"]:
            score += 8
        if result.flags["question_cta"]:
            score += 6
        if audit_ai_tells(body):
            score -= 18
        if formal and haeyo == 0:
            score -= 15
        if issues:
            score -= min(28, 7 * len(issues))
        result.score = max(0, min(100, score))

    elif channel == "newsletter":
        from lib.newsletter_complete import _GARBAGE_TITLE

        haeyo, formal = _sentence_endings(body)
        result.flags["haeyo_register"] = haeyo >= max(1, formal)
        result.flags["no_garbage_title"] = not _GARBAGE_TITLE.search(body)
        result.flags["question_cta"] = "?" in body[-300:] or "보세요" in body[-200:]
        result.flags["first_person"] = bool(_FIRST_PERSON.search(body))
        result.flags["no_ai_tell"] = len(audit_ai_tells(body)) == 0

        score = 36
        if result.flags["haeyo_register"]:
            score += 18
        if result.flags["no_garbage_title"]:
            score += 20
        else:
            score -= 22
        if result.flags["question_cta"]:
            score += 10
        if result.flags["first_person"]:
            score += 10
        if result.flags["no_ai_tell"]:
            score += 12
        else:
            score -= 15
        if issues:
            score -= min(24, 6 * len(issues))
        result.score = max(0, min(100, score))

    elif channel == "brief":
        result.flags["no_persona_dup"] = "21년차 디지털 마케터" not in body
        result.flags["complete_sentences"] = len(audit_mid_truncation(body)) == 0
        result.flags["no_ai_tell"] = len(audit_ai_tells(body)) == 0

        score = 40
        if result.flags["no_persona_dup"]:
            score += 22
        else:
            score -= 18
        if result.flags["complete_sentences"]:
            score += 15
        if result.flags["no_ai_tell"]:
            score += 18
        else:
            score -= 22
        result.score = max(0, min(100, score))

    elif channel == "blog":
        haeyo, formal = _sentence_endings(body)
        result.flags["formal_register"] = formal >= haeyo
        result.flags["no_haeyo_mix"] = haeyo <= max(2, formal // 3)
        result.flags["no_ai_tell"] = not audit_ai_tells(body)

        score = 42
        if result.flags["formal_register"]:
            score += 25
        if result.flags["no_haeyo_mix"]:
            score += 18
        if result.flags["no_ai_tell"]:
            score += 15
        if issues:
            score -= min(25, 6 * len(issues))
        result.score = max(0, min(100, score))

    else:
        result.score = max(0, 50 - 10 * len(issues))

    result.issues = list(dict.fromkeys(issues))
    return result


def run_naturalness_fixture_eval(fixtures_dir: Path | None = None) -> tuple[int, int, list[str]]:
    root = fixtures_dir or FIXTURES_DIR
    path = root / "naturalness.json"
    if not path.exists():
        return 0, 1, [f"fixture 없음: {path}"]

    cases = json.loads(path.read_text(encoding="utf-8"))
    passed = failed = 0
    errors: list[str] = []

    for case in cases:
        cid = case.get("id", "?")
        channel = case.get("channel", "linkedin")
        text = case.get("text", "")
        ns = score_naturalness(text, channel=channel)
        min_s = case.get("min_score")
        max_s = case.get("max_score")
        ok = True
        if min_s is not None and ns.score < int(min_s):
            errors.append(f"{cid}: score {ns.score} < min {min_s}")
            ok = False
        if max_s is not None and ns.score > int(max_s):
            errors.append(f"{cid}: score {ns.score} > max {max_s}")
            ok = False
        if ok:
            passed += 1
        else:
            failed += 1

    return passed, failed, errors


def audit_stamp_naturalness(stamp: str) -> list[tuple[str, NaturalnessScore]]:
    """당일 채널 산출물 자연스러움 감사."""
    results: list[tuple[str, NaturalnessScore]] = []

    brief = WORKDIR / f"content/research/{stamp}_brief.md"
    if brief.exists():
        text = brief.read_text(encoding="utf-8")
        m = re.search(r"## Executive Summary\n(.+?)\n\n##", text, re.S)
        if m:
            ns = score_naturalness(m.group(1).strip(), channel="brief")
            results.append(("brief", ns))

    li = sorted(WORKDIR.glob(f"content/linkedin/{stamp}_linkedin_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if li:
        body = li[0].read_text(encoding="utf-8").split("---")[0].strip()
        results.append(("linkedin", score_naturalness(body, channel="linkedin")))

    ig = sorted(WORKDIR.glob(f"content/instagram/{stamp}_instagram_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if ig:
        text = ig[0].read_text(encoding="utf-8")
        cap = re.search(r"## 캡션.*?\n\n(.+?)\n\n---", text, re.S)
        if cap:
            results.append(("instagram", score_naturalness(cap.group(1).strip(), channel="instagram")))

    blog = WORKDIR / f"content/packages/{stamp}_blog-article.md"
    if blog.exists():
        raw = blog.read_text(encoding="utf-8")
        prose = "\n".join(
            ln for ln in raw.splitlines()
            if ln.strip() and not ln.startswith("#") and not ln.startswith("|")
        )[:2000]
        results.append(("blog", score_naturalness(prose, channel="blog")))

    nl = sorted(WORKDIR.glob(f"content/newsletter/{stamp}_newsletter_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if nl:
        text = nl[0].read_text(encoding="utf-8")
        chunks: list[str] = []
        for heading in ("## 30초 TLDR", "## 오늘의 1가지"):
            sec = re.search(rf"{re.escape(heading)}\n(.+?)(?=\n## |\Z)", text, re.S)
            if sec:
                chunks.append(sec.group(1).strip())
        if chunks:
            results.append(("newsletter", score_naturalness("\n".join(chunks)[:2500], channel="newsletter")))

    return results


def naturalness_issues_for_stamp(stamp: str) -> list[str]:
    issues: list[str] = []
    for channel, ns in audit_stamp_naturalness(stamp):
        if not ns.passed:
            issues.append(f"{channel}: naturalness {ns.score} < {naturalness_min_score(channel)}")
    return issues


def _naturalness_fail_message(channel: str, ns: NaturalnessScore) -> str:
    return f"{channel} naturalness {ns.score} < {naturalness_min_score(channel)}"


def audit_research_brief_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"## Executive Summary\n(.+?)\n\n##", text, re.S)
    if not m:
        return ["Executive Summary 없음"]
    ns = score_naturalness(m.group(1).strip(), channel="brief")
    return [] if ns.passed else [_naturalness_fail_message("brief", ns)]


def audit_newsletter_file_naturalness(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    chunks: list[str] = []
    for heading in ("## 30초 TLDR", "## 오늘의 1가지"):
        sec = re.search(rf"{re.escape(heading)}\n(.+?)(?=\n## |\Z)", text, re.S)
        if sec:
            chunks.append(sec.group(1).strip())
    if not chunks:
        return ["newsletter TLDR/Hero 없음"]
    ns = score_naturalness("\n".join(chunks)[:2500], channel="newsletter")
    return [] if ns.passed else [_naturalness_fail_message("newsletter", ns)]


def audit_blog_html_naturalness(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    prose = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    prose = re.sub(r"<style[^>]*>.*?</style>", " ", prose, flags=re.I | re.S)
    prose = re.sub(r"<[^>]+>", " ", prose)
    prose = re.sub(r"\s+", " ", prose).strip()[:2000]
    if len(prose) < 80:
        return ["blog 본문 추출 부족"]
    ns = score_naturalness(prose, channel="blog")
    return [] if ns.passed else [_naturalness_fail_message("blog", ns)]


def audit_blog_article_md_naturalness(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("#") or line.startswith("|") or line.startswith("- **"):
            continue
        if line.strip() and not line.startswith("```"):
            lines.append(line.strip())
    prose = re.sub(r"\s+", " ", " ".join(lines)).strip()[:2000]
    if len(prose) < 80:
        return ["blog-article 본문 추출 부족"]
    ns = score_naturalness(prose, channel="blog")
    return [] if ns.passed else [_naturalness_fail_message("blog-article", ns)]


def audit_newsletter_html_naturalness(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    prose = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    prose = re.sub(r"<style[^>]*>.*?</style>", " ", prose, flags=re.I | re.S)
    prose = re.sub(r"<[^>]+>", " ", prose)
    prose = re.sub(r"\s+", " ", prose).strip()[:2500]
    if len(prose) < 80:
        return ["newsletter HTML 본문 추출 부족"]
    ns = score_naturalness(prose, channel="newsletter")
    return [] if ns.passed else [_naturalness_fail_message("newsletter-html", ns)]


def audit_newsletter_paste_naturalness(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    sec = re.search(r"## §3 본문.*?\n```[\w]*\n(.+?)```", text, re.S)
    chunk = sec.group(1).strip() if sec else text[:2500]
    if len(chunk) < 60:
        return ["newsletter paste 본문 추출 부족"]
    ns = score_naturalness(chunk, channel="newsletter")
    return [] if ns.passed else [_naturalness_fail_message("newsletter-paste", ns)]
