"""Parse Hermes chat / hermes-run log output for token · USD usage."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _parse_int_commas(raw: str) -> int:
    digits = re.sub(r"[^\d]", "", raw or "")
    return int(digits) if digits else 0


def _sum_token_fields(text: str) -> int:
    """TUI verbose block — Input + Output + cache + reasoning."""
    total = 0
    for pattern in (
        r"Input tokens:\s+([\d,]+)",
        r"Output tokens:\s+([\d,]+)",
        r"Cache read tokens:\s+([\d,]+)",
        r"Cache write tokens:\s+([\d,]+)",
        r"↳ Reasoning \(subset\):\s+([\d,]+)",
    ):
        match = re.search(pattern, text, re.I)
        if match:
            total += _parse_int_commas(match.group(1))
    return total


def _sum_codex_token_usage_lines(text: str) -> int:
    """Codex DEBUG — `Token usage: prompt=..., completion=..., total=N` per API call."""
    total = 0
    for match in re.finditer(
        r"Token usage:\s*prompt=[\d,]+,\s*completion=[\d,]+,\s*total=([\d,]+)",
        text,
        re.I,
    ):
        total += _parse_int_commas(match.group(1))
    return total


def _sum_response_usage_tokens(text: str) -> int:
    """Codex DEBUG — `ResponseUsage(..., total_tokens=N)`."""
    total = 0
    for match in re.finditer(r"ResponseUsage\([^)]*?total_tokens=(\d+)", text):
        total += int(match.group(1))
    return total


def _extract_session_ids(text: str) -> list[str]:
    return list(
        dict.fromkeys(
            re.findall(r"\[(\d{8}_\d{6}_[a-f0-9]+)\]", text)
            + re.findall(r"session=(\d{8}_\d{6}_[a-f0-9]+)", text)
            + re.findall(r"Session:\s+(\d{8}_\d{6}_[a-f0-9]+)", text)
        )
    )


def _sessions_json_path() -> Path:
    return Path.home() / ".hermes" / "sessions" / "sessions.json"


def _usage_from_sessions_row(row: dict) -> dict[str, int | float]:
    if not row:
        return {"tokens": 0, "usd": 0.0}
    input_tokens = int(row.get("input_tokens") or 0)
    output_tokens = int(row.get("output_tokens") or 0)
    cache_read = int(row.get("cache_read_tokens") or 0)
    cache_write = int(row.get("cache_write_tokens") or 0)
    reasoning = int(row.get("reasoning_tokens") or 0)
    total = int(row.get("total_tokens") or 0)
    if not total:
        total = input_tokens + output_tokens + cache_read + cache_write + reasoning
    usd = float(row.get("estimated_cost_usd") or 0.0)
    return {"tokens": total, "usd": usd}


def _usage_from_sessions_json(session_id: str | None = None) -> dict[str, int | float]:
    path = _sessions_json_path()
    if not path.exists():
        return {"tokens": 0, "usd": 0.0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"tokens": 0, "usd": 0.0}
    if not isinstance(data, dict) or not data:
        return {"tokens": 0, "usd": 0.0}

    if session_id and session_id in data:
        return _usage_from_sessions_row(data[session_id])

    if session_id:
        for _key, row in data.items():
            if isinstance(row, dict) and str(row.get("session_id") or "") == session_id:
                return _usage_from_sessions_row(row)

    latest = max(
        data.values(),
        key=lambda row: str((row or {}).get("updated_at") or (row or {}).get("created_at") or ""),
    )
    return _usage_from_sessions_row(latest if isinstance(latest, dict) else {})


def _sum_codex_usd_lines(text: str) -> float:
    """Codex DEBUG — estimated cost fields in log lines."""
    total = 0.0
    for pattern in (
        r"\bestimated_cost_usd[=:]\s*\$?([\d.]+)",
    ):
        for match in re.finditer(pattern, text, re.I):
            total += float(match.group(1))
    return total


def _sum_response_usage_usd(text: str) -> float:
    total = 0.0
    for match in re.finditer(r"ResponseUsage\([^)]*?estimated_cost_usd=([\d.]+)", text):
        total += float(match.group(1))
    return total


def snapshot_sessions_map() -> dict[str, dict[str, int | float]]:
    """Session id → {tokens, usd} snapshot for delta accounting."""
    path = _sessions_json_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, int | float]] = {}
    for key, row in data.items():
        if not isinstance(row, dict):
            continue
        sid = str(row.get("session_id") or key)
        usage = _usage_from_sessions_row(row)
        out[sid] = usage
    return out


def usage_delta_from_sessions(
    log_text: str,
    before: dict[str, dict[str, int | float]],
) -> dict[str, int | float]:
    """Per-run delta from sessions.json when log contains session ids."""
    ids = _extract_session_ids(log_text)
    tokens = 0
    usd = 0.0
    for sid in ids:
        after = _usage_from_sessions_json(sid)
        prev = before.get(sid) or {"tokens": 0, "usd": 0.0}
        tokens += max(0, int(after["tokens"]) - int(prev["tokens"]))
        usd += max(0.0, float(after["usd"]) - float(prev["usd"]))
    return {"tokens": tokens, "usd": usd}


def parse_run_usage(
    log_text: str,
    *,
    sessions_before: dict[str, dict[str, int | float]] | None = None,
    prefer_delta: bool = True,
) -> dict[str, int | float]:
    """Parse usage for a single hermes-run invocation (delta when possible)."""
    direct = parse_hermes_log_usage(log_text)
    if not prefer_delta or not sessions_before:
        return direct
    delta = usage_delta_from_sessions(log_text, sessions_before)
    if delta["tokens"] or delta["usd"]:
        return delta
    return direct


def parse_hermes_log_usage(text: str) -> dict[str, int | float]:
    """Extract total tokens and USD from hermes verbose log or stdout/stderr."""
    tokens = 0
    usd = 0.0
    session_ids = _extract_session_ids(text) if text else []

    if text:
        for pattern in (
            r"Total tokens:\s+([\d,]+)",
            r"Tokens:\s+([\d,]+)",
            r"session_total_tokens[\"']?\s*[:=]\s*(\d+)",
        ):
            match = re.search(pattern, text, re.I)
            if match:
                tokens = _parse_int_commas(match.group(1))
                break

        if not tokens:
            tokens = _sum_codex_token_usage_lines(text)
        if not tokens:
            tokens = _sum_response_usage_tokens(text)
        if not tokens:
            tokens = _sum_token_fields(text)

        cost_match = re.search(
            r"Total cost:\s+(?:~?\$?\s*([\d.]+)|included|n/a)",
            text,
            re.I,
        )
        if cost_match and cost_match.group(1):
            usd = float(cost_match.group(1))
        if not usd:
            usd = _sum_codex_usd_lines(text)
        if not usd:
            usd = _sum_response_usage_usd(text)

    if not tokens or not usd:
        for sid in reversed(session_ids):
            fallback = _usage_from_sessions_json(sid)
            if not tokens and fallback["tokens"]:
                tokens = int(fallback["tokens"])
            if not usd and fallback["usd"]:
                usd = float(fallback["usd"])
            if tokens and usd:
                break

    if not tokens and not usd:
        fallback = _usage_from_sessions_json(session_ids[-1] if session_ids else None)
        tokens = int(fallback["tokens"])
        usd = float(fallback["usd"])

    return {"tokens": tokens, "usd": usd}
