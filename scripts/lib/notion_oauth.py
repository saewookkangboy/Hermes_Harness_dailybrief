"""Notion MCP OAuth preflight — 토큰 만료·툴 미등록 조기 감지."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TOKEN_PATH = Path.home() / ".hermes" / "mcp-tokens" / "notion.json"
REAUTH_CMD = "hermes mcp login notion"
DEFAULT_WARN_HOURS = 24


@dataclass(frozen=True)
class NotionOAuthStatus:
    ok: bool
    code: str
    detail: str
    expires_at: float | None = None
    expires_in_hours: float | None = None
    has_refresh_token: bool = False
    missing_tools: tuple[str, ...] = ()

    def recovery_hint(self) -> str:
        if self.ok:
            return ""
        if self.code in {"expired", "missing", "refresh_failed", "tools_missing"}:
            return f"복구: 대화형 터미널에서 `{REAUTH_CMD}` 실행 후 `hermes mcp test notion`"
        return self.detail


def _load_token_file() -> dict[str, Any] | None:
    if not TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def notion_token_expiry() -> tuple[float | None, bool]:
    """Return (expires_at_epoch, has_refresh_token)."""
    data = _load_token_file()
    if not data:
        return None, False
    expires_at = data.get("expires_at")
    try:
        exp = float(expires_at) if expires_at is not None else None
    except (TypeError, ValueError):
        exp = None
    if exp is None and data.get("expires_in") is not None:
        try:
            exp = TOKEN_PATH.stat().st_mtime + float(data["expires_in"])
        except (OSError, TypeError, ValueError):
            exp = None
    refresh = bool(data.get("refresh_token"))
    return exp, refresh


def check_notion_oauth_status(
    *,
    warn_before_hours: float = DEFAULT_WARN_HOURS,
    required_tools: list[str] | None = None,
    registry: Any | None = None,
) -> NotionOAuthStatus:
    """OAuth 파일·만료·(선택) MCP 툴 등록 상태를 점검."""
    exp, has_refresh = notion_token_expiry()
    if exp is None and not _load_token_file():
        return NotionOAuthStatus(
            ok=False,
            code="missing",
            detail="Notion OAuth 토큰 없음",
            has_refresh_token=False,
        )

    now = time.time()
    if exp is not None:
        remaining_h = (exp - now) / 3600
        if remaining_h <= 0:
            return NotionOAuthStatus(
                ok=False,
                code="expired",
                detail=f"Notion OAuth 만료 ({abs(remaining_h):.0f}h 경과)",
                expires_at=exp,
                expires_in_hours=remaining_h,
                has_refresh_token=has_refresh,
            )
        if remaining_h <= warn_before_hours:
            return NotionOAuthStatus(
                ok=True,
                code="expiring_soon",
                detail=f"Notion OAuth {remaining_h:.0f}h 내 만료 예정",
                expires_at=exp,
                expires_in_hours=remaining_h,
                has_refresh_token=has_refresh,
            )

    tools = list(required_tools or [])
    if registry is not None and tools:
        missing = tuple(t for t in tools if not registry.get_entry(t))
        if missing:
            return NotionOAuthStatus(
                ok=False,
                code="tools_missing",
                detail=(
                    "Notion MCP 툴 미등록 — OAuth 재인증 필요 "
                    f"({', '.join(missing[:2])}{'…' if len(missing) > 2 else ''})"
                ),
                expires_at=exp,
                expires_in_hours=(exp - now) / 3600 if exp else None,
                has_refresh_token=has_refresh,
                missing_tools=missing,
            )

    return NotionOAuthStatus(
        ok=True,
        code="ok",
        detail="Notion OAuth OK",
        expires_at=exp,
        expires_in_hours=(exp - now) / 3600 if exp else None,
        has_refresh_token=has_refresh,
    )


def required_notion_tools(cfg: dict) -> list[str]:
    mcp = cfg.get("mcp") or {}
    names = [
        mcp.get("create_tool", "mcp_notion_notion_create_pages"),
        mcp.get("update_tool", "mcp_notion_notion_update_page"),
        mcp.get("fetch_tool", "mcp_notion_notion_fetch"),
    ]
    return [str(n) for n in names if n]


def assert_notion_oauth_ready(
    cfg: dict,
    *,
    registry: Any | None = None,
    blocking: bool = True,
) -> NotionOAuthStatus:
    """Archive/M5 전 preflight. 실패 시 명확한 RuntimeError."""
    status = check_notion_oauth_status(
        required_tools=required_notion_tools(cfg),
        registry=registry,
    )
    if status.ok or not blocking:
        return status
    hint = status.recovery_hint()
    raise RuntimeError(f"{status.detail}. {hint}".strip())


def format_oauth_alert(status: NotionOAuthStatus) -> str:
    if status.ok:
        return ""
    icon = "❌" if status.code in {"expired", "missing", "tools_missing", "refresh_failed"} else "⚠️"
    lines = [f"{icon} {status.detail}"]
    hint = status.recovery_hint()
    if hint:
        lines.append(hint)
    return "\n".join(lines)
