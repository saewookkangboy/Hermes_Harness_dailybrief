#!/usr/bin/env python3
"""Hermes Studio — 운영 리소스·의존성 다이어그램을 Notion 별도 페이지로보내기."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.markdown_notion import md_to_notion  # noqa: E402
from lib.notion_client import (  # noqa: E402
    create_page,
    load_config,
    log,
    setup_mcp,
    update_page_content,
)

WORKDIR = Path.home() / "hermes-content-studio"
LOGS = WORKDIR / "content" / "logs"
STATE_PATH = WORKDIR / "content" / ".notion-architecture-state.json"


def _strip_h1(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].lstrip().startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).lstrip()


def _date_tag() -> str:
    env = __import__("os").environ.get("STUDIO_DATE", "")
    if env:
        return env
    for p in sorted(LOGS.glob("*_studio-resources-spec.md"), reverse=True):
        m = re.match(r"(\d{4}-\d{2}-\d{2})_", p.name)
        if m:
            return m.group(1)
    return datetime.now().strftime("%Y-%m-%d")


def _paths(date: str) -> dict[str, Path]:
    return {
        "resources": LOGS / f"{date}_studio-resources-spec.md",
        "diagrams": LOGS / f"{date}_studio-dependency-diagrams.md",
        "cursor": LOGS / f"{date}_cursor-agent-resources.md",
        "guide": LOGS / f"{date}_studio-architecture-guide.md",
    }


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"date": "", "pages": {}}


def _notion_body(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    return md_to_notion(_strip_h1(raw), path)


def _save_state(date: str, pages: dict) -> None:
    state = {"date": date, "pages": pages, "updated_at": datetime.now().isoformat()}
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    date = _date_tag()
    paths = _paths(date)
    missing = [k for k, p in paths.items() if k != "guide" and not p.exists()]
    if missing:
        log(f"Missing MD files for {date}: {missing}", prefix="ArchExport")
        return 1

    cfg = load_config()
    root = cfg["archive"]["root_page_id"]
    registry = setup_mcp()
    prior = _load_state()
    prior_pages = prior.get("pages") or {}

    exports = [
        (
            "resources",
            f"Hermes Studio — 운영 리소스·기술 스펙 ({date})",
            "📋",
            paths["resources"],
        ),
        (
            "diagrams",
            f"Hermes Studio — 의존성 다이어그램 ({date})",
            "🗺️",
            paths["diagrams"],
        ),
        (
            "cursor",
            f"Hermes Studio — Cursor Agent 리소스 맵 ({date})",
            "🤖",
            paths["cursor"],
        ),
    ]

    pages: dict[str, dict] = {}
    for key, title, icon, src in exports:
        body = _notion_body(src)
        existing = prior_pages.get(key) or {}
        page_id = existing.get("id", "")
        if page_id:
            url = update_page_content(registry, cfg, page_id, body)
            pages[key] = {"id": page_id, "url": url, "title": title, "local": str(src)}
        else:
            page_id, url = create_page(registry, cfg, root, title, body, icon)
            pages[key] = {"id": page_id, "url": url, "title": title, "local": str(src)}

    _save_state(date, pages)

    print("\n=== Notion Architecture Export ===")
    for key, meta in pages.items():
        print(f"  [{key}] {meta['url']}")
    print(f"  state → {STATE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
