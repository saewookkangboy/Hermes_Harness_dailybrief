"""Voice / 문체 품질 감사 — AI-tell · ellipsis · LinkedIn 불릿 완결성."""
from __future__ import annotations

import json
import re
from pathlib import Path

from lib.content_quality_config import ai_tell_patterns, change_rate_max
from lib.humanize_korean import humanize

WORKDIR = Path.home() / "hermes-content-studio"
FIXTURES_DIR = WORKDIR / "tests" / "fixtures" / "voice"

_MID_ELLIPSIS = re.compile(r"[^\s.!?。…」』\"']\u2026")
_MID_DOTS = re.compile(r"\.{3}(?=\S)")

_HAEYO_ENDINGS = re.compile(r"(해요|돼요|예요|이에요|세요|까요)[.!?]?\s*$")


def audit_mid_truncation(text: str) -> list[str]:
    """문장 중간 '…' 또는 '...' 절단 탐지."""
    issues: list[str] = []
    if _MID_ELLIPSIS.search(text):
        issues.append("문장 중간 '…' 생략")
    if _MID_DOTS.search(text):
        issues.append("문장 중간 '...' 절단")
    return issues


def audit_ai_tells(text: str) -> list[str]:
    issues: list[str] = []
    for tell in ai_tell_patterns():
        if tell in text:
            issues.append(f"AI-tell: {tell}")
    return issues


def audit_linkedin_post_body(body: str) -> list[str]:
    """LinkedIn 본문(--- 이전) 문체·불릿 완결성."""
    issues: list[str] = []
    issues.extend(audit_mid_truncation(body))
    issues.extend(audit_ai_tells(body))

    for line in body.splitlines():
        if not line.startswith("  "):
            continue
        detail = line.strip()
        if not detail:
            continue
        if detail[-1] not in ".!?。…":
            issues.append(f"불완전 불릿 보조줄: {detail[:48]}")
        issues.extend(audit_mid_truncation(detail))

    return issues


def audit_linkedin_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    body = text.split("---")[0].strip()
    return audit_linkedin_post_body(body)


def audit_instagram_caption(caption: str) -> list[str]:
    """Instagram 캡션 섹션 — AI-tell·ellipsis·완결 문장."""
    issues: list[str] = []
    issues.extend(audit_mid_truncation(caption))
    issues.extend(audit_ai_tells(caption))
    skip_prefixes = ("#", "📌", "💡", "👉", "💬", "---")
    for line in caption.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(skip_prefixes):
            continue
        if stripped.startswith("→") and stripped[-1] not in ".!?。…":
            issues.append(f"불완전 캡션 불릿: {stripped[:40]}")
        elif len(stripped) > 24 and stripped[-1] not in ".!?。…":
            issues.append(f"불완전 캡션 문장: {stripped[:40]}")
    return issues


def audit_instagram_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    caption_m = re.search(r"## 캡션.*?\n\n(.+?)\n\n---", text, re.S)
    caption = caption_m.group(1).strip() if caption_m else ""
    if not caption:
        return ["캡션 섹션 없음"]
    return audit_instagram_caption(caption)


def voice_trait_flags(text: str, *, channel: str) -> dict[str, bool]:
    """M4 coach용 voice trait — no_ai_tell · complete_sentences."""
    issues: list[str] = []
    issues.extend(audit_mid_truncation(text))
    issues.extend(audit_ai_tells(text))
    if channel == "linkedin":
        issues.extend(audit_linkedin_post_body(text))
    elif channel == "instagram":
        issues.extend(audit_instagram_caption(text))
    joined = " ".join(issues)
    return {
        "no_ai_tell": not any(i.startswith("AI-tell") for i in issues),
        "complete_sentences": not any(
            k in joined for k in ("불완전", "생략", "절단")
        ),
    }


def run_voice_audit_stamp(stamp: str) -> list[str]:
    """당일 LinkedIn·Instagram·builder voice 감사."""
    issues: list[str] = []
    li_matches = sorted(
        WORKDIR.glob(f"content/linkedin/{stamp}_linkedin_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if li_matches:
        issues.extend(audit_linkedin_file(li_matches[0]))
    ig_matches = sorted(
        WORKDIR.glob(f"content/instagram/{stamp}_instagram_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if ig_matches:
        issues.extend(audit_instagram_file(ig_matches[0]))
    _, fail, builder_errs = run_linkedin_builder_eval(stamp)
    if fail:
        issues.extend(builder_errs)
    return issues


def run_fixture_eval(fixtures_dir: Path | None = None) -> tuple[int, int, list[str]]:
    """Fixture JSON 기반 humanize·문체 회귀 테스트."""
    root = fixtures_dir or FIXTURES_DIR
    fixture_path = root / "ai-tell.json"
    if not fixture_path.exists():
        return 0, 1, [f"fixture 없음: {fixture_path}"]

    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    passed = 0
    failed = 0
    errors: list[str] = []

    for case in cases:
        cid = case.get("id", "?")
        genre = case.get("genre", "linkedin")
        before = case.get("before", "")
        forbidden = case.get("forbidden", [])
        must_contain = case.get("must_contain", [])

        result = humanize(before, genre=genre).text

        case_ok = True
        for f in forbidden:
            if f and f in result:
                errors.append(f"{cid}: forbidden '{f}' in output")
                case_ok = False
        for m in must_contain:
            if m and m not in result:
                errors.append(f"{cid}: missing '{m}' in output")
                case_ok = False

        if case_ok:
            passed += 1
        else:
            failed += 1

    return passed, failed, errors


def run_change_rate_eval(fixtures_dir: Path | None = None) -> tuple[int, int, list[str]]:
    """humanize change_rate ≤ cap (기본 30%)."""
    root = fixtures_dir or FIXTURES_DIR
    fixture_path = root / "ai-tell.json"
    if not fixture_path.exists():
        return 0, 1, [f"fixture 없음: {fixture_path}"]

    max_rate = change_rate_max()
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    passed = 0
    failed = 0
    errors: list[str] = []

    for case in cases:
        cid = case.get("id", "?")
        before = (case.get("before") or "").strip()
        if not before:
            continue
        genre = case.get("genre", "linkedin")
        result = humanize(before, genre=genre)
        rate = result.change_count / max(len(before), 1)
        cap = float(case.get("max_change_rate", max_rate))
        if rate > cap:
            errors.append(f"{cid}: change_rate {rate:.2f} > {cap:.2f}")
            failed += 1
        else:
            passed += 1

    return passed, failed, errors


def run_linkedin_builder_eval(stamp: str) -> tuple[int, int, list[str]]:
    """Brief → build_linkedin_post_text 완결성 스모크."""
    from lib.content_quality import build_linkedin_post_text, parse_brief

    brief_path = WORKDIR / "content" / "research" / f"{stamp}_brief.md"
    if not brief_path.exists():
        return 0, 1, [f"brief 없음: {brief_path}"]

    summary, insights = parse_brief(brief_path.read_text(encoding="utf-8"))
    post = build_linkedin_post_text(summary, insights)
    issues = audit_linkedin_post_body(post)
    if issues:
        return 0, 1, issues
    return 1, 0, []
