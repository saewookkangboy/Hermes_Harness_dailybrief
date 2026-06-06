#!/usr/bin/env bash
# Hermes Content Studio — 콘텐츠 패키지 (Brief SoT → blog · instagram · linkedin)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
SCRIPTS="$WORKDIR/scripts"
# shellcheck source=lib/studio-date.sh
source "$SCRIPTS/lib/studio-date.sh"
DATE="${1:-$(studio_today)}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

cd "$WORKDIR"
mkdir -p content/blog content/instagram content/linkedin content/packages

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

BRIEF="$WORKDIR/content/research/${DATE}_brief.md"
TODAY="$(studio_today)"

# Brief SoT: M2 진입 전 일일 최신 리서치 선행
if [[ "${HERMES_SKIP_RESEARCH:-0}" != "1" ]]; then
  NEED=0
  if [[ "${HERMES_FORCE_RESEARCH:-0}" == "1" ]]; then NEED=1; fi
  if [[ ! -f "$BRIEF" ]]; then NEED=1; fi
  if [[ "$DATE" == "$TODAY" ]]; then NEED=1; fi
  if [[ "$NEED" == "1" ]]; then
    echo "=== 0/2 Brief SoT — 일일 최신 리서치 (gather → brief Top 7) ==="
    "$SCRIPTS/run-research-brief.sh" "$DATE"
  else
    run_python - <<PY || NEED=1
import sys
sys.path.insert(0, "$SCRIPTS")
from lib.brief_gate import needs_daily_research
raise SystemExit(0 if not needs_daily_research("$DATE") else 1)
PY
    if [[ "$NEED" == "1" ]]; then
      echo "=== 0/2 Brief SoT — 신선도 미달, 리서치 재실행 ==="
      "$SCRIPTS/run-research-brief.sh" "$DATE"
    fi
  fi
fi

[[ -f "$BRIEF" ]] || { echo "❌ Brief 없음: $BRIEF" >&2; exit 1; }

echo ""
echo "=== 1/2 콘텐츠 패키지 조립 (brief → blog · instagram · linkedin) ==="
run_python "$SCRIPTS/assemble-content-package.py" "$DATE"

BLOG_HTML=$(ls -t "$WORKDIR/content/blog/${DATE}"_blog_*.html 2>/dev/null | head -1 || true)
BLOG_PKG="$WORKDIR/content/packages/${DATE}_blog-article.md"
SOC_IG="$WORKDIR/content/packages/${DATE}_instagram-context.md"
SOC_LI="$WORKDIR/content/packages/${DATE}_linkedin-context.md"
UNIFIED="$WORKDIR/content/packages/${DATE}_unified-context.md"
IG_MD=$(ls -t "$WORKDIR/content/instagram/${DATE}"_instagram_*.md 2>/dev/null | head -1 || true)
LI_MD=$(ls -t "$WORKDIR/content/linkedin/${DATE}"_linkedin_*.md 2>/dev/null | head -1 || true)

for f in "$BRIEF" "$BLOG_HTML" "$BLOG_PKG" "$SOC_IG" "$SOC_LI" "$UNIFIED" "$IG_MD" "$LI_MD"; do
  [[ -f "$f" ]] || { echo "산출물 없음: $f" >&2; exit 1; }
done

echo ""
echo "=== 2/2 품질 검증 (Brief SoT + M2 채널) ==="
"$SCRIPTS/validate-output.sh" research "$BRIEF"
"$SCRIPTS/validate-output.sh" blog-article "$BLOG_PKG"
"$SCRIPTS/validate-output.sh" blog "$BLOG_HTML"
"$SCRIPTS/validate-output.sh" instagram "$IG_MD"
"$SCRIPTS/validate-output.sh" instagram-context "$SOC_IG"
"$SCRIPTS/validate-output.sh" linkedin "$LI_MD"
"$SCRIPTS/validate-output.sh" linkedin-context "$SOC_LI"
"$SCRIPTS/validate-output.sh" unified-context "$UNIFIED"

if [[ "${HERMES_HUMANIZE:-0}" == "1" ]]; then
  echo ""
  echo "=== Hermes humanize-korean (선택, im-not-ai) ==="
  HERMES_TOOLSETS=hermes-cli HERMES_USE_CODEX=1 "$SCRIPTS/hermes-run.sh" \
    "humanize-korean: ${BLOG_PKG} blog 문체 윤문. 의미·URL·구조 유지." \
    --skills humanize-korean -t hermes-cli || true
fi

if [[ "${HERMES_ENHANCE:-0}" == "1" ]]; then
  echo ""
  echo "=== Hermes polish (선택) ==="
  HERMES_TOOLSETS=hermes-cli HERMES_USE_CODEX=1 "$SCRIPTS/hermes-run.sh" \
    "content-pipeline: ${BRIEF} 기반 blog 아티클 polish. 3000자 해요체 유지." \
    --skills content-pipeline -t hermes-cli || true
fi

echo ""
echo "=== 콘텐츠 패키지 완료 (Brief → M2) ==="
echo "Brief:  $BRIEF"
ls -la "$BLOG_PKG" "$IG_MD" "$LI_MD" "$SOC_IG" "$SOC_LI" "$UNIFIED"
