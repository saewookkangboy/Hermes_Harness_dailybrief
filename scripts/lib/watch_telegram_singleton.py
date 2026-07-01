"""watch-telegram 단일 인스턴스 감지 — 자식 subshell(status_loop·tail) 오탐 제외."""
from __future__ import annotations

import subprocess


def root_pids() -> list[int]:
    try:
        r = subprocess.run(
            ["ps", "-ax", "-o", "pid=,ppid=,command="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    pids: dict[int, int] = {}
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if "/watch-telegram.sh" not in line or "kill-stale" in line:
            continue
        parts = line.split(None, 2)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        pids[pid] = ppid
    return [pid for pid, ppid in pids.items() if ppid not in pids]


def root_count() -> int:
    return len(root_pids())
