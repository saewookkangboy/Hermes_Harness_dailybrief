#!/usr/bin/env python3
"""Keyword research entry — merge/replace/approve staging into Brief SoT."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
SCRIPTS = WORKDIR / "scripts"
RESEARCH = WORKDIR / "content" / "research"
sys.path.insert(0, str(SCRIPTS))

from lib.research_merge import (  # noqa: E402
    backup_brief,
    merge_contexts,
    require_approve_on_replace,
    restore_brief,
    write_context,
)
from lib.research_run_audit import find_same_fingerprint, fingerprint, write_run  # noqa: E402
from lib.research_staging import write_staging  # noqa: E402


def _py() -> list[str]:
    hermes = Path.home() / ".hermes/hermes-agent/venv/bin/python"
    if hermes.is_file() and os.access(hermes, os.X_OK):
        return [str(hermes)]
    return [sys.executable]


def _run(cmd: list[str], env: dict | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.check_call(cmd, cwd=str(WORKDIR), env=merged)


def _count_insights(text: str) -> int:
    return len(re.findall(r"^### \d+\.", text, re.M))


def main() -> int:
    stamp = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    keywords = (os.environ.get("HERMES_RESEARCH_KEYWORDS") or "").strip()
    replace = (os.environ.get("HERMES_RESEARCH_REPLACE") or "").strip() in ("1", "true", "True")
    approve = (os.environ.get("HERMES_RESEARCH_APPROVE") or "").strip() in ("1", "true", "True")
    mode = "replace" if replace else "merge"

    if not keywords:
        _run(_py() + [str(SCRIPTS / "gather-web-research.py"), stamp])
        _run(_py() + [str(SCRIPTS / "assemble-research-brief.py"), stamp])
        _run(
            [
                "bash",
                str(SCRIPTS / "validate-output.sh"),
                "research",
                str(RESEARCH / f"{stamp}_brief.md"),
            ]
        )
        return 0

    prior = find_same_fingerprint(stamp, keywords, mode)
    if prior and (os.environ.get("HERMES_RESEARCH_FORCE") or "") not in ("1", "true", "True"):
        print(f"skip: same fingerprint {prior.name} (set HERMES_RESEARCH_FORCE=1 to refresh)")
        return 0

    base_path = RESEARCH / f"_search_context_{stamp}.json"
    base_ctx = None
    if base_path.exists():
        base_ctx = json.loads(base_path.read_text(encoding="utf-8"))

    # Keyword-only gather into a side file (gather always writes main name — swap)
    kw_env = {
        "HERMES_RESEARCH_KEYWORDS": keywords,
        "HERMES_RESEARCH_KEYWORD_ONLY": "1",
    }
    _run(_py() + [str(SCRIPTS / "gather-web-research.py"), stamp], env=kw_env)
    kw_ctx = json.loads(base_path.read_text(encoding="utf-8"))
    write_context(stamp, kw_ctx, ".kw")

    if mode == "merge" and base_ctx is not None:
        write_context(stamp, merge_contexts(base_ctx, kw_ctx))
    elif mode == "merge" and base_ctx is None:
        write_context(stamp, kw_ctx)  # first brief of day
    else:
        write_context(stamp, kw_ctx)  # replace candidate context

    live = RESEARCH / f"{stamp}_brief.md"
    backup_brief(stamp)
    _run(_py() + [str(SCRIPTS / "assemble-research-brief.py"), stamp])
    if not live.exists():
        print("❌ assemble failed", file=sys.stderr)
        return 1
    brief_text = live.read_text(encoding="utf-8")
    try:
        _run(["bash", str(SCRIPTS / "validate-output.sh"), "research", str(live)])
    except subprocess.CalledProcessError:
        restore_brief(stamp)
        print("❌ validate failed — restored previous brief", file=sys.stderr)
        return 1

    need_stage = approve or (replace and require_approve_on_replace())
    if need_stage:
        restore_brief(stamp)
        run_id = f"{stamp}_{fingerprint(keywords, mode, stamp)}"
        write_staging(
            run_id=run_id,
            stamp=stamp,
            mode=mode,
            keywords=keywords,
            brief_text=brief_text,
            insight_count=_count_insights(brief_text),
        )
        write_run(
            stamp=stamp,
            mode=f"{mode}+staging",
            keywords=keywords,
            paths={"staging": str(RESEARCH / "_staging" / run_id)},
        )
        print(f"staging: {run_id}")
        print("use: telegram-pipeline.sh qc research-pending | research-approve")
        return 0

    write_run(
        stamp=stamp,
        mode=mode,
        keywords=keywords,
        paths={"brief": str(live)},
    )
    print(live)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
