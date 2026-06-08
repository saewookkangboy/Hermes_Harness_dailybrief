#!/usr/bin/env bash
# Hermes Content Studio — Codex (ChatGPT 구독 OAuth) 연동 헬퍼
#
# HERMES_USE_CODEX=1 이거나 claude-design 계열 스킬이면 Codex provider 사용.
# 기본 cron 파이프라인은 Ollama 유지, 품질 경로만 Codex로 라우팅.

export HERMES_CODEX_PROVIDER="${HERMES_CODEX_PROVIDER:-openai-codex}"
# gpt-5.3-codex retired on ChatGPT Codex OAuth (2026-06) — use gpt-5.5
export HERMES_CODEX_MODEL="${HERMES_CODEX_MODEL:-gpt-5.5}"
export PATH="${HOME}/.hermes/node/bin:${PATH}"

hermes_should_use_codex() {
  local skills="${1:-}"
  if [[ "${HERMES_USE_CODEX:-0}" == "1" ]]; then
    return 0
  fi
  case "$skills" in
    *claude-design*|claude-design*)
      return 0
      ;;
    *personal-assistant*|personal-assistant*)
      return 0
      ;;
    *personal*|*automate*)
      return 0
      ;;
  esac
  return 1
}

hermes_codex_provider_args() {
  local skills="${1:-}"
  if hermes_should_use_codex "$skills"; then
    printf '%s\n' "--provider" "$HERMES_CODEX_PROVIDER" "-m" "$HERMES_CODEX_MODEL"
  fi
}

hermes_codex_status_label() {
  local skills="${1:-}"
  if hermes_should_use_codex "$skills"; then
    echo "Codex"
  else
    echo "Ollama"
  fi
}
