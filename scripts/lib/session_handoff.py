"""Session handoff 고도화 — .harness/session-handoff.md 자동 생성."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.m4_analytics import format_m4_report
from lib.omm import format_omm_block
from lib.session_sot import load_session

WORKDIR = Path.home() / "hermes-content-studio"
HANDOFF_PATH = WORKDIR / ".harness" / "session-handoff.md"

NEXT_COMMANDS: dict[str, list[str]] = {
    "morning": [
        "hermes-agent.sh catch-up --days 3",
        "telegram-pipeline.sh pipeline",
    ],
    "catch-up": [
        "hermes-agent.sh publish linkedin --dry-run",
        "archive-to-notion.sh $(date +%Y-%m-%d) --force --notify-final",
    ],
    "publish": [
        "hermes-agent.sh linkedin",
        "validate-output.sh linkedin-context content/packages/{stamp}_linkedin-context.md",
    ],
    "deep": [
        "hermes-agent.sh bridge-sync",
        "run-research-brief.sh",
    ],
    "ask": [
        "hermes-agent.sh morning",
        "hermes-agent.sh route \"오늘 Top 3\"",
    ],
    "linkedin": [
        "archive-to-notion.sh {stamp} --force",
        "hermes-agent.sh publish linkedin",
    ],
    "traces": [
        "harness-eval.sh --record",
        "phase2-eval.sh",
    ],
}


def suggest_next_commands(session: dict[str, Any]) -> list[str]:
    intent = session.get("last_intent") or ""
    stamp = session.get("last_stamp") or "$(date +%Y-%m-%d)"
    cmds = list(NEXT_COMMANDS.get(intent, ["hermes-agent.sh morning", "telegram-pipeline.sh pipeline"]))
    return [c.replace("{stamp}", stamp) for c in cmds]


def format_resume_block(session_id: str = "cli") -> str:
    """Telegram/CLI용 이어하기 블록."""
    s = load_session(session_id)
    if not s.get("last_action"):
        return ""
    lines = [
        f"📌 세션 `{session_id}`",
        f"- 마지막: {s.get('last_stamp')} · {s.get('last_intent')} → {s.get('last_action')}",
    ]
    pending = s.get("pending_actions") or []
    if pending:
        lines.append(f"- 대기: {', '.join(pending[:3])}")
    next_cmds = suggest_next_commands(s)
    if next_cmds:
        lines.append("- 다음 제안:")
        for c in next_cmds[:2]:
            lines.append(f"  · `{c}`")
    return "\n".join(lines)


def build_handoff_markdown(session_id: str = "cli", m4_days: int = 7) -> str:
    s = load_session(session_id)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    next_cmds = suggest_next_commands(s)
    m4_block = format_m4_report(m4_days)

    lines = [
        "# Session Handoff",
        "",
        f"생성: {now} · session `{session_id}`",
        "",
        "## 마지막 Agent 세션",
        "",
        f"- **날짜(stamp):** {s.get('last_stamp') or '—'}",
        f"- **Intent:** {s.get('last_intent') or '—'}",
        f"- **Action:** {s.get('last_action') or '—'}",
        f"- **대기:** {', '.join(s.get('pending_actions') or []) or '없음'}",
        "",
        "## 이어하기 (Resume)",
        "",
        "```bash",
        "cd ~/hermes-content-studio",
        "./scripts/init.sh --skip-health",
    ]
    for c in next_cmds:
        lines.append(f"./scripts/{c}" if not c.startswith("archive") else f"./scripts/{c}")
    lines.extend(["```", "", "## OMM (실수 방어선)", "", format_omm_block(5), "", "## M4 Performance (최근 7일)", "", "```", m4_block, "```", ""])
    lines.extend(
        [
            "## Phase 2 체크",
            "",
            "- [ ] LinkedIn M3: `hermes-agent.sh linkedin`",
            "- [ ] M4 리포트: `hermes-agent.sh traces`",
            "- [ ] handoff 갱신: `hermes-agent.sh handoff`",
            "",
            "## 검증",
            "",
            "```bash",
            "./scripts/phase2-eval.sh",
            "./scripts/harness-eval.sh --quick",
            "```",
        ]
    )
    return "\n".join(lines)


def write_session_handoff(session_id: str = "cli", m4_days: int = 7) -> Path:
    HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF_PATH.write_text(build_handoff_markdown(session_id, m4_days), encoding="utf-8")
    return HANDOFF_PATH
