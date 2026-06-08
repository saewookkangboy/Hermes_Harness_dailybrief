#!/usr/bin/env bash
# Hermes Content Studio — cron 작업 등록 (일일 리서치 + 주간 콘텐츠)
set -euo pipefail

WORKDIR="$HOME/hermes-content-studio"
echo "=== Cron 작업 등록 (Asia/Seoul) ==="

# 기존 중복 Daily AI Marketing Brief 제거
echo "기존 중복 작업 정리..."
while read -r line; do
  id=$(echo "$line" | awk '{print $1}')
  if [ -n "$id" ]; then
    hermes cron remove "$id" 2>/dev/null && echo "  제거: $id" || true
  fi
done < <(hermes cron list 2>/dev/null | grep "Daily AI Marketing Brief" || true)

# 매일: 일일 리서치 브리프 (Top 7)
echo "등록: daily-research-brief (매일 08:00)"
hermes cron create \
  --name "daily-research-brief" \
  --workdir "$WORKDIR" \
  --skill marketing-research \
  "0 8 * * *" \
  "scripts/run-research-brief.sh 를 실행해 일일 리서치 브리프(Top 7)를 생성해. 실패 시 validate-output.sh research 로 검증." \
  2>/dev/null || echo "  (이미 존재하거나 CLI 옵션 확인 필요)"

# 수요일: 콘텐츠 패키지
echo "등록: weekly-content-package (수 09:00)"
hermes cron create \
  --name "weekly-content-package" \
  --workdir "$WORKDIR" \
  --skill content-pipeline \
  "0 9 * * 3" \
  "scripts/run-content-package.sh 를 실행해 최신 brief 기반 blog+instagram+linkedin 초안을 생성해." \
  2>/dev/null || echo "  (이미 존재하거나 CLI 옵션 확인 필요)"

# 금요일: 강의 기획
echo "등록: weekly-lecture-planning (금 09:00)"
hermes cron create \
  --name "weekly-lecture-planning" \
  --workdir "$WORKDIR" \
  --skill content-studio-slides \
  "0 9 * * 5" \
  "content-studio-slides 스킬: 이번 주 리서치에서 강의 소재 1개를 선정하고, lecture-outline 템플릿으로 기획안 + HTML 초안을 작성해줘. Getdesign.md 슬라이드 규칙 적용." \
  2>/dev/null || echo "  (이미 존재하거나 CLI 옵션 확인 필요)"

# 결정적 Commander cron (모닝 · 헬스)
"$WORKDIR/scripts/setup-commander-cron.sh" || echo "  ⚠️  Commander cron 등록 실패 — setup-commander-cron.sh 재실행"

echo ""
echo "등록된 작업:"
hermes cron list 2>/dev/null
