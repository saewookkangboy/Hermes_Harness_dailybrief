"""Runtime health — Gateway · Ollama · watch-telegram · proactive (cron용)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from lib.proactive_triggers import run_proactive_checks

WORKDIR = Path.home() / "hermes-content-studio"


def _pgrep(pattern: str) -> bool:
    try:
        r = subprocess.run(
            ["bash", "-lc", f"ps -ax -o command= | rg -q '{pattern}'"],
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _watch_count() -> int:
    try:
        r = subprocess.run(
            ["bash", "-lc", r"ps -ax -o command= | rg -c 'watch-telegram\.sh' || echo 0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return int((r.stdout or "0").strip() or "0")
    except (ValueError, subprocess.TimeoutExpired, OSError):
        return 0


def check_gateway() -> str | None:
    if _pgrep(r"hermes_cli\.main gateway"):
        return None
    return "❌ Hermes Gateway 미실행 — hermes gateway restart"


def check_ollama() -> str | None:
    if not _pgrep(r"^/Applications/Ollama\.app|ollama serve|/ollama"):
        if not _pgrep("ollama"):
            return "❌ Ollama 미실행 — open -a Ollama"
    try:
        r = subprocess.run(
            ["curl", "-sf", "http://127.0.0.1:11434/api/tags"],
            capture_output=True,
            timeout=5,
        )
        if r.returncode != 0:
            return "❌ Ollama API 응답 없음"
    except (subprocess.TimeoutExpired, OSError):
        return "❌ Ollama API 확인 실패"
    return None


def check_watch_singleton() -> str | None:
    n = _watch_count()
    if n == 0:
        return "⚠️ watch-telegram 미실행 — start-services.sh"
    if n > 1:
        return f"⚠️ watch-telegram {n}중 실행 — kill-stale-watch-telegram.sh"
    return None


def run_runtime_checks(stamp: str | None = None) -> list[str]:
    issues: list[str] = []
    for fn in (check_gateway, check_ollama, check_watch_singleton):
        msg = fn()
        if msg:
            issues.append(msg)
    for alert in run_proactive_checks(stamp):
        issues.append(alert.get("message", ""))
    return [m for m in issues if m]
