"""Build and send Hermes Content Studio daily digest to Slack."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
sys.path.insert(0, str(WORKDIR / "scripts"))

from lib.slack_notify import get_bot_token, load_env, send_long_text, send_message  # noqa: E402
from lib.common import studio_today  # noqa: E402
from lib.notify_format import format_slack_archive_summary  # noqa: E402

LOG_PATH = Path.home() / ".hermes" / "logs" / "content-studio.log"
STATE_PATH = WORKDIR / "content" / ".notion-archive-state.json"
OUTPUT_DIR = WORKDIR / "content" / "logs"


def sections_for(stamp: str) -> list[tuple[str, Path]]:
    return [
        ("Research Brief", WORKDIR / "content" / "research" / f"{stamp}_brief.md"),
        ("Blog Article", WORKDIR / "content" / "packages" / f"{stamp}_blog-article.md"),
        ("Instagram Context", WORKDIR / "content" / "packages" / f"{stamp}_instagram-context.md"),
        ("LinkedIn Context", WORKDIR / "content" / "packages" / f"{stamp}_linkedin-context.md"),
        ("Unified Context", WORKDIR / "content" / "packages" / f"{stamp}_unified-context.md"),
    ]


def channel_outputs(stamp: str) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for channel, sub in (("Blog HTML", "blog"), ("Instagram Post", "instagram"), ("LinkedIn Post", "linkedin")):
        base = WORKDIR / "content" / sub
        if not base.is_dir():
            continue
        matches = sorted(base.glob(f"{stamp}_{sub}_*"))
        if matches:
            out.append((channel, matches[-1]))
    return out


def load_notion_day(stamp: str) -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    day = (state.get("days") or {}).get(stamp)
    if isinstance(day, dict):
        return day
    if isinstance(day, str):
        return {"id": day, "url": ""}
    return {}


def notion_pages(stamp: str) -> list[dict]:
    if not STATE_PATH.exists():
        return []
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    pages = []
    prefix = f"{stamp}/"
    for key, meta in (state.get("pages") or {}).items():
        if not key.startswith(prefix) or not isinstance(meta, dict):
            continue
        if meta.get("tier") == "draft":
            continue
        pages.append(
            {
                "key": key.split("/", 1)[-1],
                "url": meta.get("url", ""),
                "path": meta.get("path", ""),
                "score": meta.get("quality_score"),
            }
        )
    pages.sort(key=lambda p: p["key"])
    return pages


def extract_log_lines(stamp: str, *, max_lines: int = 120) -> list[str]:
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    picked = [ln for ln in lines if stamp in ln]
    if picked:
        return picked[-max_lines:]
    # 날짜 문자열이 없으면 최근 파이프라인 관련 tail
    keywords = ("[Notion Archive]", "Archiving", "Done:", "ERROR:", "Skip", "brief", "content")
    tail = [ln for ln in lines if any(k in ln for k in keywords)]
    return (tail or lines)[-max_lines:]


def build_header(stamp: str) -> str:
    lines = [
        f"# Hermes Content Studio — Daily Log {stamp}",
        "",
        f"생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"워크디렉: `{WORKDIR}`",
        "",
        "## 산출물 상태",
    ]
    for label, path in sections_for(stamp) + channel_outputs(stamp):
        mark = "✅" if path.exists() else "⬜"
        lines.append(f"- {mark} {label}: `{path.relative_to(WORKDIR)}`" if path.exists() else f"- {mark} {label}")
    day = load_notion_day(stamp)
    if day.get("url"):
        lines.extend(["", f"**Notion Daily:** {day['url']}"])
    return "\n".join(lines)


def build_log_section(stamp: str) -> str:
    log_lines = extract_log_lines(stamp)
    if not log_lines:
        return "## Pipeline Log\n\n_(로그 없음)_"
    body = "\n".join(f"    {ln}" for ln in log_lines)
    return f"## Pipeline Log (`content-studio.log`)\n\n```\n{body.strip()}\n```"


def build_content_section(label: str, path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(WORKDIR)
    return f"## {label}\n\n`{rel}` · {len(text)} chars\n\n{text.rstrip()}\n"


def build_notion_section(stamp: str) -> str:
    pages = notion_pages(stamp)
    if not pages:
        return "## Notion Sync\n\n_(동기화 기록 없음)_"
    lines = ["## Notion Sync", ""]
    for p in pages:
        score = f" · score {p['score']}" if p.get("score") is not None else ""
        lines.append(f"- **{p['key']}**{score}")
        if p.get("url"):
            lines.append(f"  {p['url']}")
        if p.get("path"):
            lines.append(f"  `{p['path']}`")
    return "\n".join(lines)


def build_digest(stamp: str) -> str:
    parts = [build_header(stamp), "", build_log_section(stamp), ""]
    for label, path in sections_for(stamp):
        if path.exists():
            parts.append(build_content_section(label, path))
            parts.append("")
    for label, path in channel_outputs(stamp):
        if path.suffix == ".html":
            continue  # packages blog-article.md가 전문 대용
        if path.exists():
            parts.append(build_content_section(label, path))
            parts.append("")
    parts.append(build_notion_section(stamp))
    return "\n".join(parts).strip() + "\n"


DEFAULT_SLACK_HOME = "C0B8CN2EA05"  # #일반데이터 — config/slack-routing.yaml


def resolve_slack_channel(explicit: str) -> str:
    if explicit:
        return explicit
    env = load_env()
    channel = os.environ.get("SLACK_HOME_CHANNEL") or env.get("SLACK_HOME_CHANNEL", "")
    return channel or DEFAULT_SLACK_HOME


def build_summary_digest(stamp: str) -> str:
    """Compact Slack summary — permalinks + file checklist (no full content dump)."""
    pages = [
        {
            "icon": {"research": "📋", "blog": "📝", "instagram": "📸", "linkedin": "💼", "unified": "🔗"}.get(
                p["key"], "📄"
            ),
            "label": p["key"],
            "url": p.get("url", ""),
            "tier": "canonical",
            "quality_score": p.get("score"),
        }
        for p in notion_pages(stamp)
    ]
    day = load_notion_day(stamp)
    file_status: list[tuple[str, bool, str]] = []
    for label, path in sections_for(stamp):
        if path.exists():
            file_status.append((label, True, str(path.relative_to(WORKDIR))))
        else:
            file_status.append((label, False, ""))
    return format_slack_archive_summary(
        stamp,
        pages,
        day_url=day.get("url", ""),
        file_status=file_status,
    )


def send_digest(channel: str, digest: str, *, stamp: str, summary_only: bool = False) -> bool:
    if summary_only:
        return send_message(channel, digest)

    intro = (
        f"*📋 Hermes Daily Log — {stamp}*\n"
        f"콘텐츠·로그 전문 digest · {len(digest):,} chars\n"
        f"로컬: `content/logs/{stamp}_daily-slack-digest.md`"
    )
    if not send_message(channel, intro):
        return False

    # 섹션 단위 전송 (## 헤더 기준) — H1 제외
    body = re.sub(r"^# .+\n+", "", digest, count=1)
    parts = re.split(r"\n(?=## )", body)
    ok = True
    for i, part in enumerate(parts, start=1):
        part = part.strip()
        if not part:
            continue
        label = part.split("\n", 1)[0].lstrip("# ").strip()
        prefix = f"*{stamp} · {label}* ({i}/{len(parts)})\n"
        if not send_long_text(channel, part, prefix=prefix):
            ok = False
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/send daily content log to Slack")
    parser.add_argument("date", nargs="?", default=studio_today())
    parser.add_argument("--send", action="store_true", help="Send to Slack (SLACK_HOME_CHANNEL)")
    parser.add_argument("--channel", default="", help="Override Slack channel ID")
    parser.add_argument("--build-only", action="store_true", help="Write digest file only")
    parser.add_argument("--summary-only", action="store_true", help="Send compact summary (no full content)")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args()

    stamp = args.date
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp):
        print(f"❌ 날짜 형식 오류: {stamp}", file=sys.stderr)
        return 1

    digest = build_digest(stamp)
    summary = build_summary_digest(stamp)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{stamp}_daily-slack-digest.md"
    out_path.write_text(digest, encoding="utf-8")
    summary_path = OUTPUT_DIR / f"{stamp}_daily-slack-summary.md"
    summary_path.write_text(summary, encoding="utf-8")

    summary_data = {
        "stamp": stamp,
        "path": str(out_path),
        "summary_path": str(summary_path),
        "chars": len(digest),
        "summary_chars": len(summary),
        "sections": sum(1 for _, p in sections_for(stamp) if p.exists()),
    }

    if args.json:
        print(json.dumps(summary_data, ensure_ascii=False, indent=2))

    if args.build_only and not args.send:
        print(out_path)
        return 0

    channel = resolve_slack_channel(args.channel)
    if not get_bot_token():
        print(
            "⚠️ SLACK_BOT_TOKEN 없음 — digest 파일만 저장됨\n"
            "  → ~/hermes-content-studio/scripts/setup-slack.sh 실행 후 재시도",
            file=sys.stderr,
        )
        print(out_path)
        return 0 if args.build_only else 1

    payload = summary if args.summary_only else digest
    if send_digest(channel, payload, stamp=stamp, summary_only=args.summary_only):
        print(f"✅ Slack 전송 완료 → {channel}")
        print(out_path)
        return 0

    print("❌ Slack 전송 실패 (Bot Token·채널 invite 확인)", file=sys.stderr)
    print(out_path)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
