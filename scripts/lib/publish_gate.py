"""HITL Publish Gate — 채널별 승인 후 발행."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKDIR = Path.home() / "hermes-content-studio"
SCRIPTS = WORKDIR / "scripts"
QUEUE_DIR = WORKDIR / ".harness" / "publish-queue"
VALID_CHANNELS = ("blog", "instagram", "linkedin", "newsletter")


def _queue_path(stamp: str) -> Path:
    return QUEUE_DIR / f"{stamp}.json"


def load_queue(stamp: str) -> dict[str, Any]:
    path = _queue_path(stamp)
    if not path.exists():
        return {"stamp": stamp, "channels": {}, "status": "empty"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"stamp": stamp, "channels": {}, "status": "error"}


def save_queue(data: dict[str, Any]) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = _queue_path(data["stamp"])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def request_publish(stamp: str, channels: list[str] | None = None) -> dict[str, Any]:
    """HITL 대기열 생성 — 승인 전 발행 차단."""
    chs = [c.lower() for c in (channels or list(VALID_CHANNELS)) if c.lower() in VALID_CHANNELS]
    if not chs:
        chs = ["linkedin"]
    existing = load_queue(stamp)
    channel_state = existing.get("channels") or {}
    for c in chs:
        if channel_state.get(c) != "approved":
            channel_state[c] = "pending"
    data = {
        "stamp": stamp,
        "status": "awaiting_approval",
        "channels": channel_state,
        "created_at": existing.get("created_at")
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_queue(data)
    return data


def approve_channels(stamp: str, channels: list[str]) -> dict[str, Any]:
    data = load_queue(stamp)
    if data.get("status") == "empty":
        data = request_publish(stamp, channels)
    ch_map = data.get("channels") or {}
    for c in channels:
        cl = c.lower()
        if cl == "all":
            for vc in VALID_CHANNELS:
                ch_map[vc] = "approved"
        elif cl in VALID_CHANNELS:
            ch_map[cl] = "approved"
    data["channels"] = ch_map
    approved = [k for k, v in ch_map.items() if v == "approved"]
    data["status"] = "approved" if approved else "awaiting_approval"
    data["approved_channels"] = approved
    save_queue(data)
    return data


def format_telegram_approval(stamp: str, queue: dict[str, Any] | None = None) -> str:
    """Telegram/Slack용 짧은 HITL 안내."""
    q = queue or load_queue(stamp)
    ch = q.get("channels") or {}
    pending = [c for c in VALID_CHANNELS if ch.get(c) == "pending"]
    approved = [c for c in VALID_CHANNELS if ch.get(c) == "approved"]
    lines = [
        f"🛡 HITL 발행 대기 · {stamp}",
        "",
    ]
    if pending:
        lines.append("⏳ 대기: " + ", ".join(pending))
    if approved:
        lines.append("✅ 승인됨: " + ", ".join(approved))
    lines.extend(
        [
            "",
            "승인: /approve linkedin · /approve all",
            f"상태: /pending",
        ]
    )
    return "\n".join(lines)


def format_pending_status(stamp: str | None = None) -> str:
    stamp = stamp or ""
    if stamp:
        return format_approval_card(stamp, load_queue(stamp))
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    paths = sorted(QUEUE_DIR.glob("*.json"), reverse=True)
    if not paths:
        return "📭 HITL 발행 대기열 비어 있음"
    lines = ["📋 HITL Publish Queue", ""]
    for path in paths[:5]:
        s = path.stem
        q = load_queue(s)
        ch = q.get("channels") or {}
        pending = [c for c in VALID_CHANNELS if ch.get(c) == "pending"]
        pub = [c for c in VALID_CHANNELS if ch.get(c) == "published"]
        if pending:
            lines.append(f"• {s} — 대기: {', '.join(pending)}")
        elif pub:
            lines.append(f"• {s} — 발행됨: {', '.join(pub)}")
        else:
            lines.append(f"• {s} — {q.get('status', '—')}")
    lines.extend(["", "상세: hermes-agent.sh pending --date YYYY-MM-DD"])
    return "\n".join(lines)


def format_approval_card(stamp: str, queue: dict[str, Any] | None = None) -> str:
    q = queue or load_queue(stamp)
    ch = q.get("channels") or {}
    lines = [
        f"🛡 HITL Publish Gate · {stamp}",
        "",
        "승인 후 발행됩니다. `--approve` 또는 `approve` 명령 사용.",
        "",
        "| 채널 | 상태 |",
        "|------|------|",
    ]
    icons = {"pending": "⏳ 대기", "approved": "✅ 승인", "published": "📤 발행됨"}
    for c in VALID_CHANNELS:
        st = ch.get(c, "—")
        lines.append(f"| {c} | {icons.get(st, st)} |")
    lines.extend(
        [
            "",
            "승인 예:",
            f"  /approve linkedin",
            f"  /approve all",
            f"  hermes-agent.sh publish linkedin --approve --date {stamp}",
        ]
    )
    return "\n".join(lines)


def _run_channel_publish(stamp: str, channel: str) -> bool:
    env = {**dict(__import__("os").environ), "HERMES_SKIP_RESEARCH": "1"}
    if channel == "newsletter":
        subprocess.run(
            [str(SCRIPTS / "run-newsletter.sh"), stamp, "--validate"],
            check=False,
            env=env,
        )
        pkg = WORKDIR / "content" / "packages" / f"{stamp}_newsletter-context.md"
        paste = WORKDIR / "content" / "packages" / f"{stamp}_newsletter-paste.md"
        vtype = "newsletter-context"
        if paste.exists():
            subprocess.run(
                [str(SCRIPTS / "validate-output.sh"), "newsletter-paste", str(paste)],
                check=False,
                env=env,
            )
    else:
        subprocess.run([str(SCRIPTS / "run-content-package.sh"), stamp], check=False, env=env)
        pkg = WORKDIR / "content" / "packages" / f"{stamp}_{channel}-context.md"
        if channel == "blog":
            pkg = WORKDIR / "content" / "packages" / f"{stamp}_blog-article.md"
            vtype = "blog-article"
        else:
            vtype = f"{channel}-context"
    subprocess.run([str(SCRIPTS / "validate-output.sh"), vtype, str(pkg)], check=False)
    return pkg.exists()


def execute_approved_publish(stamp: str, channels: list[str] | None = None) -> dict[str, Any]:
    """승인된 채널만 validate + Notion sync (전체 Daily archive)."""
    q = load_queue(stamp)
    approved = channels or q.get("approved_channels") or [
        k for k, v in (q.get("channels") or {}).items() if v == "approved"
    ]
    if not approved:
        return {"stamp": stamp, "published": [], "error": "no_approved_channels"}

    published: list[str] = []
    for ch in approved:
        if ch in VALID_CHANNELS and _run_channel_publish(stamp, ch):
            published.append(ch)

    subprocess.run(
        [str(SCRIPTS / "archive-to-notion.sh"), stamp, "--force", "--notify-final"],
        check=False,
        cwd=str(WORKDIR),
    )

    ch_map = q.get("channels") or {}
    for ch in published:
        ch_map[ch] = "published"
    q["channels"] = ch_map
    q["status"] = "published" if published else q.get("status")
    q["published_channels"] = published
    save_queue(q)
    return {"stamp": stamp, "published": published, "queue": q}
