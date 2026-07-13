#!/usr/bin/env bash
# Hermes cron (~/.hermes/scripts 복사본) — 워크스페이스 scripts 경로 SoT
# Hermes gateway subprocess: cwd=~/.hermes/scripts, HERMES_WORKDIR 미전달 가능
set -euo pipefail

cron_resolve_workdir() {
  local wd cfg cwd _cfg
  if [[ -n "${HERMES_WORKDIR:-}" && -d "${HERMES_WORKDIR}/scripts/lib" ]]; then
    printf '%s' "${HERMES_WORKDIR}"
    return 0
  fi
  for _cfg in "${HERMES_HOME:-}/config.yaml" "${HOME}/.hermes/config.yaml"; do
    [[ -z "$_cfg" || ! -f "$_cfg" ]] && continue
    cwd=$(python3 -c "
import pathlib, re
text = pathlib.Path('${_cfg}').read_text(encoding='utf-8')
m = re.search(r'^\\s*cwd:\\s*(.+)$', text, re.M)
if m:
    p = pathlib.Path(m.group(1).strip().strip('\"').strip(\"'\"))
    print(p.expanduser())
" 2>/dev/null || true)
    if [[ -n "$cwd" && -d "${cwd}/scripts/lib" ]]; then
      printf '%s' "$cwd"
      return 0
    fi
  done
  for wd in "${HOME}/hermes-content-studio"; do
    if [[ -d "${wd}/scripts/lib" ]]; then
      printf '%s' "$wd"
      return 0
    fi
  done
  return 1
}

WORKDIR="$(cron_resolve_workdir)" || {
  echo "ERROR: Hermes workspace not found (set HERMES_WORKDIR or config.yaml terminal.cwd)" >&2
  exit 1
}
export HERMES_WORKDIR="$WORKDIR"
SCRIPTS_DIR="${SCRIPTS_DIR:-$WORKDIR/scripts}"
export PYTHONPATH="${SCRIPTS_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
HERMES_PY="${HERMES_PY:-$HOME/.hermes/hermes-agent/venv/bin/python}"

cron_run_py() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

cron_py_path() {
  printf '%s' "$SCRIPTS_DIR"
}
