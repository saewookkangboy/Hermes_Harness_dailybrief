#!/usr/bin/env bash
# Hermes Content Studio — ~/.hermes/node/bin PATH (codex, mcporter 등)

HERMES_NODE_PREFIX="${HOME}/.hermes/node"
HERMES_NODE_BIN="${HERMES_NODE_PREFIX}/bin"
export PATH="${HERMES_NODE_BIN}:${PATH}"

hermes_ensure_node_path_in_shell() {
  local zshrc="${HOME}/.zshrc"
  local marker_begin='# >>> hermes-content-studio node bin >>>'
  local marker_end='# <<< hermes-content-studio node bin <<<'
  local block

  block="${marker_begin}
export PATH=\"\${HOME}/.hermes/node/bin:\${PATH}\"
${marker_end}"

  if [[ -f "$zshrc" ]] && grep -qF "$marker_begin" "$zshrc" 2>/dev/null; then
    echo "  ✓ ~/.zshrc PATH 이미 등록됨"
    return 0
  fi

  touch "$zshrc"
  {
    echo ""
    echo "$block"
  } >> "$zshrc"
  echo "  ✓ ~/.zshrc에 ~/.hermes/node/bin PATH 추가"
}
