"""Agent Command Registry — CLI · Telegram · Cursor 공용 명령 SoT."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

WORKDIR = Path.home() / "hermes-content-studio"
SCRIPTS = WORKDIR / "scripts"
CONFIG_PATH = WORKDIR / "config" / "agent-commands.yaml"


def load_registry() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def list_intents() -> list[dict[str, Any]]:
    cfg = load_registry()
    packs = cfg.get("intent_packs") or {}
    out: list[dict[str, Any]] = []
    for intent_id, spec in packs.items():
        if not isinstance(spec, dict):
            continue
        out.append(
            {
                "id": intent_id,
                "type": "intent",
                "label": spec.get("label", intent_id),
                "aliases": spec.get("aliases", []),
                "sla_seconds": spec.get("sla_seconds"),
            }
        )
    return sorted(out, key=lambda x: x["id"])


def list_commands() -> list[dict[str, Any]]:
    cfg = load_registry()
    cmds = cfg.get("commands") or {}
    out: list[dict[str, Any]] = []
    for cmd_id, spec in cmds.items():
        if not isinstance(spec, dict):
            continue
        out.append(
            {
                "id": cmd_id,
                "type": "command",
                "label": spec.get("label", cmd_id),
                "script": spec.get("script", ""),
                "args": spec.get("args", []),
                "agent_cli": spec.get("agent_cli", f"hermes-agent.sh {cmd_id}"),
            }
        )
    return sorted(out, key=lambda x: x["id"])


def format_registry_table() -> str:
    lines = [
        "📋 Hermes Command Registry",
        "",
        "### Intent Packs",
        "| ID | Label | Aliases | SLA |",
        "|----|-------|---------|-----|",
    ]
    for item in list_intents():
        aliases = ", ".join((item.get("aliases") or [])[:3])
        sla = item.get("sla_seconds") or "—"
        lines.append(f"| {item['id']} | {item['label']} | {aliases} | {sla}s |")
    lines.extend(["", "### Script Commands", "| ID | Label | Agent CLI |", "|----|-------|-----------|"])
    for item in list_commands():
        lines.append(f"| {item['id']} | {item['label']} | `{item['agent_cli']}` |")
    return "\n".join(lines)


def resolve_command(cmd_id: str) -> dict[str, Any] | None:
    cfg = load_registry()
    spec = (cfg.get("commands") or {}).get(cmd_id)
    if isinstance(spec, dict):
        return {"id": cmd_id, **spec}
    spec = (cfg.get("intent_packs") or {}).get(cmd_id)
    if isinstance(spec, dict):
        return {"id": cmd_id, "type": "intent", **spec}
    return None


def run_script_command(cmd_id: str, stamp: str = "", extra: list[str] | None = None) -> int:
    """Run a registry script command (not intent pack)."""
    spec = resolve_command(cmd_id)
    if not spec or spec.get("type") == "intent":
        raise KeyError(f"Unknown command: {cmd_id}")
    script = spec.get("script", "")
    if not script:
        raise ValueError(f"No script for command: {cmd_id}")
    path = SCRIPTS / script if not script.startswith("/") else Path(script)
    args = [str(a).replace("{date}", stamp).replace("{stamp}", stamp) for a in (spec.get("args") or [])]
    if extra:
        args.extend(extra)
    proc = subprocess.run([str(path), *args], cwd=str(WORKDIR), check=False)
    return int(proc.returncode or 0)
