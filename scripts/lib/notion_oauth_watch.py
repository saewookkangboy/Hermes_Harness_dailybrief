"""Notion OAuth 지속 감시 — 선제 refresh · 중복 알림 억제 · cron/proactive 공통."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from lib.notion_oauth import (
    NotionOAuthStatus,
    check_notion_oauth_status,
    format_oauth_alert,
    notion_token_expiry,
)

WORKDIR = Path.home() / "hermes-content-studio"
CONFIG_PATH = WORKDIR / "config" / "notion-archive.yaml"
STATE_PATH = WORKDIR / ".harness" / "notion-oauth-watch-state.json"
REAUTH_SCRIPT = "~/hermes-content-studio/scripts/reauth-notion-mcp.sh"

SEVERITY_ORDER = {"ok": 0, "warn": 1, "critical": 2, "fail": 3}


@dataclass(frozen=True)
class OAuthWatchResult:
    status: NotionOAuthStatus
    severity: str
    message: str
    should_alert: bool
    refreshed: bool = False
    refresh_detail: str = ""


def load_watch_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    watch = dict(cfg.get("oauth_watch") or {})
    watch.setdefault("enabled", True)
    watch.setdefault("warn_before_hours", 24)
    watch.setdefault("critical_before_hours", 6)
    watch.setdefault("alert_cooldown_hours", 4)
    watch.setdefault("refresh_cooldown_hours", 1)
    watch.setdefault("auto_refresh", True)
    watch.setdefault("verify_tools_on_critical", True)
    return watch


def load_watch_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_watch_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _severity_for(status: NotionOAuthStatus, watch: dict[str, Any]) -> str:
    if not status.ok:
        return "fail"
    if status.code != "expiring_soon":
        return "ok"
    remaining = status.expires_in_hours if status.expires_in_hours is not None else 999.0
    critical_h = float(watch.get("critical_before_hours", 6))
    if remaining <= critical_h:
        return "critical"
    return "warn"


def _build_message(status: NotionOAuthStatus, severity: str, *, refresh_detail: str = "") -> str:
    if severity == "ok":
        remaining = status.expires_in_hours
        if remaining is not None:
            return f"✅ Notion OAuth OK (만료까지 {remaining:.1f}h)"
        return status.detail

    if severity == "fail":
        lines = [format_oauth_alert(status)]
        if refresh_detail:
            lines.append(refresh_detail)
        lines.append(f"자동 감시: cron-notion-oauth-watch (2h)")
        return "\n".join(lines)

    icon = "🚨" if severity == "critical" else "⚠️"
    lines = [f"{icon} {status.detail}"]
    if refresh_detail:
        lines.append(refresh_detail)
    lines.append(f"복구: `{REAUTH_SCRIPT}`")
    lines.append("자동 감시: cron-notion-oauth-watch (2h)")
    return "\n".join(lines)


def _should_alert(
    severity: str,
    *,
    watch: dict[str, Any],
    state: dict[str, Any],
    expires_at: float | None,
) -> bool:
    if severity == "ok":
        return False
    if SEVERITY_ORDER[severity] >= SEVERITY_ORDER["fail"]:
        return True

    last_sev = str(state.get("last_alert_severity") or "ok")
    last_alert_at = float(state.get("last_alert_at") or 0)
    last_exp = state.get("last_expires_at")
    cooldown_h = float(watch.get("alert_cooldown_hours", 4))

    if expires_at is not None and last_exp is not None and float(last_exp) != float(expires_at):
        return True
    if SEVERITY_ORDER[severity] > SEVERITY_ORDER.get(last_sev, 0):
        return True
    age_h = (time.time() - last_alert_at) / 3600 if last_alert_at else 999.0
    return age_h >= cooldown_h


def try_silent_refresh(watch: dict[str, Any], state: dict[str, Any]) -> tuple[bool, str]:
    """refresh_token으로 MCP 연결 시 SDK silent refresh 시도."""
    if not watch.get("auto_refresh", True):
        return False, "auto_refresh disabled"

    exp_before, has_refresh = notion_token_expiry()
    if not has_refresh:
        return False, "no refresh_token"

    last_refresh = float(state.get("last_refresh_at") or 0)
    refresh_cd = float(watch.get("refresh_cooldown_hours", 1)) * 3600
    if last_refresh and (time.time() - last_refresh) < refresh_cd:
        return False, "refresh cooldown"

    try:
        from lib.notion_client import setup_mcp

        setup_mcp()
    except Exception as exc:  # noqa: BLE001
        return False, f"refresh attempt failed: {exc}"

    exp_after, _ = notion_token_expiry()
    state["last_refresh_at"] = time.time()
    if exp_before and exp_after and exp_after > exp_before + 60:
        return True, f"silent refresh OK (연장 {((exp_after - exp_before) / 3600):.1f}h)"
    if exp_after and exp_after - time.time() > float(watch.get("warn_before_hours", 24)) * 3600:
        return True, "silent refresh OK"
    return False, "refresh unchanged"


def evaluate_notion_oauth_watch(
    *,
    respect_cooldown: bool = True,
    try_refresh: bool = True,
) -> OAuthWatchResult:
    watch = load_watch_config()
    if not watch.get("enabled", True):
        status = check_notion_oauth_status()
        return OAuthWatchResult(
            status=status,
            severity="ok",
            message="oauth_watch disabled",
            should_alert=False,
        )

    state = load_watch_state()
    warn_h = float(watch.get("warn_before_hours", 24))
    status = check_notion_oauth_status(warn_before_hours=warn_h)
    refreshed = False
    refresh_detail = ""

    severity = _severity_for(status, watch)
    if try_refresh and severity in {"warn", "critical"}:
        refreshed, refresh_detail = try_silent_refresh(watch, state)
        if refreshed:
            status = check_notion_oauth_status(warn_before_hours=warn_h)
            severity = _severity_for(status, watch)

    if (
        severity in {"critical", "fail"}
        and watch.get("verify_tools_on_critical", True)
        and status.ok
    ):
        try:
            from lib.notion_client import load_config, setup_mcp

            registry = setup_mcp()
            cfg = load_config()
            from lib.notion_oauth import required_notion_tools

            tool_status = check_notion_oauth_status(
                warn_before_hours=warn_h,
                required_tools=required_notion_tools(cfg),
                registry=registry,
            )
            if not tool_status.ok:
                status = tool_status
                severity = "fail"
        except Exception as exc:  # noqa: BLE001
            status = NotionOAuthStatus(
                ok=False,
                code="tools_missing",
                detail=f"Notion MCP 연결 실패: {exc}",
            )
            severity = "fail"

    message = _build_message(status, severity, refresh_detail=refresh_detail)
    should_alert = (
        _should_alert(severity, watch=watch, state=state, expires_at=status.expires_at)
        if respect_cooldown
        else severity != "ok"
    )
    return OAuthWatchResult(
        status=status,
        severity=severity,
        message=message,
        should_alert=should_alert,
        refreshed=refreshed,
        refresh_detail=refresh_detail,
    )


def run_notion_oauth_watch(*, record_state: bool = True) -> OAuthWatchResult:
    """cron 엔트리 — 상태 기록 + 알림 여부 결정."""
    result = evaluate_notion_oauth_watch(respect_cooldown=True, try_refresh=True)
    if not record_state:
        return result

    state = load_watch_state()
    state["last_check_at"] = time.time()
    state["last_severity"] = result.severity
    state["last_expires_at"] = result.status.expires_at
    state["last_code"] = result.status.code
    if result.refreshed:
        state["last_refresh_ok"] = True
    if result.should_alert:
        state["last_alert_at"] = time.time()
        state["last_alert_severity"] = result.severity
    if result.severity == "ok":
        state.pop("last_alert_severity", None)
    save_watch_state(state)
    return result


def proactive_oauth_message() -> str | None:
    """daily-triage / health — fail·critical은 항상, warn은 cooldown 적용."""
    result = evaluate_notion_oauth_watch(respect_cooldown=True, try_refresh=False)
    if result.severity in {"fail", "critical"}:
        return result.message
    if result.severity == "warn" and result.should_alert:
        return result.message
    return None
