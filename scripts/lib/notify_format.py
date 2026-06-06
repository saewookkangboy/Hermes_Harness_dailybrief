"""Unified Telegram/Slack notification formatting for Content Studio pipeline."""
from __future__ import annotations

TOTAL_STEPS = 5

CATEGORY_BLURB = {
    "unified": "통합 컨텍스트 · 브리프 표",
    "research": "Top 7 리서치 브리프",
    "blog": "SEO/AEO 블로그 아티클",
    "instagram": "3장 캐러셀 + Gemini 프롬프트",
    "linkedin": "포스트 + 2×2 웹툰 프롬프트",
    "lecture_outline": "강의 아웃라인",
    "lecture_html": "강의 HTML",
}


def progress_bar(step: int, total: int = TOTAL_STEPS) -> str:
    step = max(0, min(step, total))
    return "█" * step + "░" * (total - step)


def format_progress(
    step: int,
    label: str,
    detail: str = "",
    *,
    total: int = TOTAL_STEPS,
    stamp: str = "",
) -> str:
    bar = progress_bar(step, total)
    date_line = f"📅 {stamp}\n" if stamp else ""
    msg = f"{date_line}[{bar}] {step}/{total} {label}"
    if detail:
        msg += f"\n{detail}"
    return msg


def pages_for_stamp(pages: list[dict], stamp: str) -> list[dict]:
    """현재 날짜(stamp) 산출물만 — path·title에 날짜 포함 여부."""
    if not stamp:
        return pages
    out: list[dict] = []
    for p in pages:
        path = p.get("path") or ""
        title = p.get("title") or p.get("label") or ""
        if stamp in path or stamp in title:
            out.append(p)
    return out or pages


def format_update_summary(pages: list[dict], stamp: str) -> list[str]:
    """이번 sync에서 갱신된 항목 요약."""
    filtered = pages_for_stamp(pages, stamp)
    if not filtered:
        return [f"📝 업데이트 ({stamp})", "", "변경·신규 페이지 없음"]
    lines = [f"📝 업데이트 요약 · {stamp}", ""]
    for p in filtered:
        icon = p.get("icon", "📄")
        label = p.get("label", p.get("title", "Page"))
        cat = p.get("category", "")
        blurb = CATEGORY_BLURB.get(cat, "")
        tier = p.get("tier", "canonical")
        score = p.get("quality_score")
        tag = "draft" if tier == "draft" else "정식"
        extra = f" · score {score}" if score is not None else ""
        detail = f" — {blurb}" if blurb else ""
        lines.append(f"• {icon} {label} ({tag}{extra}){detail}")
    return lines


def format_notion_pages_block(
    pages: list[dict],
    *,
    stamp: str = "",
    updated_only: bool = True,
) -> list[str]:
    lines: list[str] = []
    pool = pages_for_stamp(pages, stamp) if stamp else pages
    if updated_only and not pool:
        lines.append(f"⚠️ {stamp or '오늘'} 갱신된 Notion 페이지 없음")
        return lines
    if not pool:
        lines.append("⚠️ 동기화된 페이지 없음")
        return lines
    header = f"📎 Permalink · {stamp}" if stamp else "📎 Permalink:"
    lines.append(header)
    for p in pool:
        icon = p.get("icon", "📄")
        label = p.get("label", p.get("title", "Page"))
        url = p.get("url", "")
        tier = p.get("tier", "canonical")
        score = p.get("quality_score")
        suffix = ""
        if tier == "draft":
            suffix = " (draft)"
        elif score is not None and score < 80:
            suffix = f" · score {score}"
        lines.append(f"{icon} {label}{suffix}")
        if url:
            lines.append(url)
        lines.append("")
    return lines


def format_completion(
    stamp: str,
    pages: list[dict],
    *,
    day_url: str = "",
    hygiene_duplicates: int = 0,
) -> str:
    """Single final notification — latest date + updated items summary only."""
    filtered = pages_for_stamp(pages, stamp)
    lines = [
        f"✅ [{progress_bar(TOTAL_STEPS)}] {TOTAL_STEPS}/{TOTAL_STEPS} Notion 동기화 완료",
        f"📅 {stamp}",
        "",
    ]
    lines.extend(format_update_summary(filtered, stamp))
    lines.append("")
    if day_url:
        lines.extend(["📅 Daily Archive:", day_url, ""])
    lines.extend(format_notion_pages_block(filtered, stamp=stamp, updated_only=True))
    if hygiene_duplicates:
        lines.append(f"🗂️ 중복 {hygiene_duplicates}건 → Draft Archive 이동")
    return "\n".join(lines).strip()


def format_slack_archive_summary(
    stamp: str,
    pages: list[dict],
    *,
    day_url: str = "",
    file_status: list[tuple[str, bool, str]] | None = None,
) -> str:
    """Compact Slack summary after Notion sync (not full content dump)."""
    filtered = pages_for_stamp(pages, stamp)
    lines = [
        f"*📋 Hermes Content Studio — {stamp}*",
        f"Notion 동기화 · 갱신 {len(filtered)}페이지",
        "",
    ]
    if day_url:
        lines.extend(["*Daily Archive*", day_url, ""])
    summary_lines = format_update_summary(filtered, stamp)
    if len(summary_lines) > 2:
        lines.extend(summary_lines)
        lines.append("")
    if file_status:
        lines.append("*산출물*")
        for label, ok, rel in file_status:
            mark = "✅" if ok else "⬜"
            lines.append(f"{mark} {label}" + (f" · `{rel}`" if ok else ""))
        lines.append("")
    if filtered:
        lines.append("*Notion 페이지 (갱신)*")
        for p in filtered:
            icon = p.get("icon", "📄")
            label = p.get("label", p.get("title", ""))
            url = p.get("url", "")
            tier = p.get("tier", "canonical")
            tag = " _(draft)_" if tier == "draft" else ""
            lines.append(f"{icon} *{label}*{tag}")
            if url:
                lines.append(url)
        lines.append("")
    lines.append("_전문 digest: `content/logs/{0}_daily-slack-digest.md`_".format(stamp))
    return "\n".join(lines).strip()
