"""EasyTool-style compact commander prompts — 토큰 절약."""
from __future__ import annotations

from pathlib import Path
from typing import Any

WORKDIR = Path.home() / "hermes-content-studio"
EASYTOOL_PATH = WORKDIR / "config" / "commander-easytool.yaml"
TELEGRAM_ROUTING_PATH = WORKDIR / "config" / "telegram-routing.yaml"
SCRIPTS_BASE = "~/hermes-content-studio/scripts"


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_compact_channel_prompt(easytool_path: Path | None = None) -> str:
    """commander-easytool.yaml → compact channel_prompt."""
    path = easytool_path or EASYTOOL_PATH
    cfg = _load_yaml(path).get("easytool") or {}
    lines: list[str] = []

    role = (cfg.get("role") or "").strip()
    if role:
        lines.append(role)

    lines.append("")
    lines.append("Routes:")
    for name, route in (cfg.get("routes") or {}).items():
        cmd = route.get("cmd", "")
        slash = ", ".join(f"/{s}" for s in (route.get("slash") or [])[:8])
        if len(route.get("slash") or []) > 8:
            slash += "…"
        kw = ",".join((route.get("kw") or [])[:4])
        note = route.get("note", "")
        extra = f" kw:{kw}" if kw else ""
        note_s = f" ({note})" if note else ""
        lines.append(f"- {name}: {SCRIPTS_BASE}/{cmd} | {slash}{extra}{note_s}")

    lines.append("")
    lines.append("Rules:")
    for rule in cfg.get("rules") or []:
        lines.append(f"- {rule}")

    hints = cfg.get("quick_command_hints") or {}
    if hints:
        hint_line = " | ".join(f"/{k}={v}" for k, v in list(hints.items())[:5])
        lines.append(f"Hints: {hint_line}")

    return "\n".join(lines).strip()


def verbose_prompt_chars() -> int:
    if not TELEGRAM_ROUTING_PATH.exists():
        return 0
    routing = _load_yaml(TELEGRAM_ROUTING_PATH)
    prompt = (routing.get("telegram_routing") or {}).get("channel_prompt") or ""
    return len(prompt.strip())


def compact_prompt_chars(easytool_path: Path | None = None) -> int:
    return len(build_compact_channel_prompt(easytool_path))


def validate_easytool() -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not EASYTOOL_PATH.exists():
        return False, ["commander-easytool.yaml missing"]

    cfg = _load_yaml(EASYTOOL_PATH).get("easytool") or {}
    max_chars = int(cfg.get("max_prompt_chars") or 900)
    compact = build_compact_channel_prompt()
    if not compact:
        errors.append("compact prompt empty")
    if len(compact) > max_chars:
        errors.append(f"compact prompt {len(compact)} > max {max_chars}")

    verbose = verbose_prompt_chars()
    if verbose > 0 and len(compact) >= verbose:
        errors.append(f"compact {len(compact)} not shorter than verbose {verbose}")

    routes = cfg.get("routes") or {}
    for key in ("pipeline", "lecture", "personal"):
        if key not in routes:
            errors.append(f"missing route: {key}")

    hints = cfg.get("quick_command_hints") or {}
    for cmd in ("pipeline", "research", "content", "newsletter", "sync"):
        if cmd not in hints:
            errors.append(f"missing hint: {cmd}")

    return len(errors) == 0, errors
