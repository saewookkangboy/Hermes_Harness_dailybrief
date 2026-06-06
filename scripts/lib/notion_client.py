"""Hermes Content Studio — Notion MCP 공통 클라이언트."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

WORKDIR = Path.home() / "hermes-content-studio"
CONFIG_PATH = WORKDIR / "config" / "notion-archive.yaml"
STATE_PATH = WORKDIR / "content" / ".notion-archive-state.json"
LOG_PATH = Path.home() / ".hermes" / "logs" / "content-studio.log"
HERMES_AGENT = Path.home() / ".hermes" / "hermes-agent"
HERMES_PY = HERMES_AGENT / "venv" / "bin" / "python"


def log(msg: str, *, prefix: str = "Notion") -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [{prefix}] {msg}"
    print(line)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"days": {}, "pages": {}, "draft_archive": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def setup_mcp():
    sys.path.insert(0, str(HERMES_AGENT))
    from dotenv import load_dotenv

    load_dotenv(Path.home() / ".hermes" / ".env")
    from tools import mcp_tool
    from tools.registry import registry

    mcp_tool.discover_mcp_tools()
    return registry


def normalize_mcp_result(data) -> dict:
    if isinstance(data, str):
        try:
            return normalize_mcp_result(json.loads(data))
        except json.JSONDecodeError:
            return {"raw": data}
    if isinstance(data, dict):
        if "pages" in data:
            return data
        if "result" in data:
            inner = data["result"]
            if isinstance(inner, str):
                try:
                    return normalize_mcp_result(json.loads(inner))
                except json.JSONDecodeError:
                    pass
            elif isinstance(inner, (dict, list)):
                return normalize_mcp_result(inner)
        if "error" in data:
            return data
    return data if isinstance(data, dict) else {"raw": data}


def mcp_call(registry, tool_name: str, args: dict) -> dict:
    entry = registry.get_entry(tool_name)
    if not entry:
        raise RuntimeError(f"MCP tool not found: {tool_name}")
    raw = entry.handler(args)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = normalize_mcp_result(raw)
    result = normalize_mcp_result(data)
    if result.get("error"):
        raise RuntimeError(f"MCP {tool_name} failed: {result['error']}")
    return result


def notion_page_id_to_url(page_id: str) -> str:
    clean = page_id.replace("-", "")
    return f"https://www.notion.so/{clean}"


def fetch_page(registry, cfg: dict, page_id: str) -> dict:
    tool = cfg["mcp"].get("fetch_tool", "mcp_notion_notion_fetch")
    return mcp_call(registry, tool, {"id": page_id})


def move_pages(registry, cfg: dict, page_ids: list[str], parent_id: str) -> dict:
    tool = cfg["mcp"].get("move_tool", "mcp_notion_notion_move_pages")
    return mcp_call(
        registry,
        tool,
        {
            "page_or_database_ids": page_ids,
            "new_parent": {"type": "page_id", "page_id": parent_id},
        },
    )


def create_page(
    registry,
    cfg: dict,
    parent_id: str,
    title: str,
    content: str,
    icon: str = "",
) -> tuple[str, str]:
    tool = cfg["mcp"]["create_tool"]
    page: dict = {"properties": {"title": title}, "content": content}
    if icon:
        page["icon"] = icon
    payload = {
        "parent": {"page_id": parent_id, "type": "page_id"},
        "pages": [page],
    }
    result = mcp_call(registry, tool, payload)
    pages = result.get("pages") or []
    if not pages:
        raise RuntimeError(f"Notion create failed: {result}")
    page_id = pages[0].get("id", "")
    url = pages[0].get("url") or notion_page_id_to_url(page_id)
    log(f"Created: {title} → {url}")
    return page_id, url
