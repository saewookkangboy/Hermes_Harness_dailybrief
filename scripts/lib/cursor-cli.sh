#!/usr/bin/env bash
# Hermes Content Studio — Cursor CLI / cursor-agent helpers
#
# cursor-agent: ~/.local/bin/cursor-agent (cursor.com/install)
# cursor (IDE): /Applications/Cursor.app/Contents/Resources/app/bin/cursor

export PATH="${HOME}/.local/bin:/Applications/Cursor.app/Contents/Resources/app/bin:${PATH}"

CURSOR_APP_BIN="/Applications/Cursor.app/Contents/Resources/app/bin/cursor"
CURSOR_AGENT_BIN="${CURSOR_AGENT_BIN:-$HOME/.local/bin/cursor-agent}"
CURSOR_IDE_BIN="${CURSOR_IDE_BIN:-$HOME/.local/bin/cursor}"

cursor_cli_resolve_agent() {
  if [[ -x "$CURSOR_AGENT_BIN" ]]; then
    echo "$CURSOR_AGENT_BIN"
    return 0
  fi
  if command -v cursor-agent >/dev/null 2>&1; then
    command -v cursor-agent
    return 0
  fi
  if command -v agent >/dev/null 2>&1; then
    command -v agent
    return 0
  fi
  return 1
}

cursor_cli_resolve_ide() {
  if [[ -x "$CURSOR_IDE_BIN" ]]; then
    echo "$CURSOR_IDE_BIN"
    return 0
  fi
  if [[ -x "$CURSOR_APP_BIN" ]]; then
    echo "$CURSOR_APP_BIN"
    return 0
  fi
  if command -v cursor >/dev/null 2>&1; then
    command -v cursor
    return 0
  fi
  return 1
}

cursor_cli_agent_ready() {
  cursor_cli_resolve_agent >/dev/null 2>&1
}

cursor_cli_version() {
  local agent=""
  agent=$(cursor_cli_resolve_agent 2>/dev/null || echo "")
  if [[ -z "$agent" ]]; then
    echo ""
    return 0
  fi
  "$agent" --version 2>/dev/null || echo ""
}

cursor_cli_auth_ready() {
  [[ -n "${CURSOR_API_KEY:-}" ]] && return 0
  local agent err
  agent=$(cursor_cli_resolve_agent 2>/dev/null || return 1)
  err=$("$agent" --print --trust "ok" 2>&1 || true)
  [[ "$err" != *"Authentication required"* ]]
}

cursor_cli_ensure_symlinks() {
  mkdir -p "$HOME/.local/bin"
  if [[ -x "$CURSOR_APP_BIN" && ! -e "$CURSOR_IDE_BIN" ]]; then
    ln -sf "$CURSOR_APP_BIN" "$CURSOR_IDE_BIN"
  fi
}

cursor_cli_status_json() {
  local agent ide agent_ver=""
  agent=$(cursor_cli_resolve_agent 2>/dev/null || echo "")
  ide=$(cursor_cli_resolve_ide 2>/dev/null || echo "")
  if [[ -n "$agent" ]]; then
    agent_ver=$(cursor_cli_version)
  fi
  printf '{"agent":"%s","agent_version":"%s","ide":"%s","ready":%s}\n' \
    "$agent" "$agent_ver" "$ide" "$(cursor_cli_agent_ready && echo true || echo false)"
}
