#!/usr/bin/env bash
# Hermes Content Studio — 날짜 SoT (Asia/Seoul 기본)
# 모든 파이프라인·Notion sync는 studio_today() 사용

studio_today() {
  # TZ 명시 시 로컬 자정 기준 일자 고정
  TZ="${STUDIO_TZ:-Asia/Seoul}" date +%Y-%m-%d
}

studio_refresh_date() {
  DATE="$(studio_today)"
  export DATE
}

# content/packages 또는 research에 해당 날짜 산출물 존재 여부
studio_has_content_for() {
  local d="${1:-$(studio_today)}"
  local w="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
  [[ -f "$w/content/research/${d}_brief.md" ]] && return 0
  [[ -f "$w/content/packages/${d}_unified-context.md" ]] && return 0
  return 1
}

# Notion sync용: 인자 없으면 오늘, 오늘 산출물 없으면 최신 brief 날짜(경고)
studio_resolve_archive_date() {
  local requested="${1:-}"
  local w="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
  local today
  today="$(studio_today)"

  if [[ -n "$requested" ]]; then
    echo "$requested"
    return 0
  fi

  if studio_has_content_for "$today"; then
    echo "$today"
    return 0
  fi

  # 최신 brief 날짜 (fallback — stderr 경고)
  local latest
  latest=$(ls -t "$w/content/research/"*_brief.md 2>/dev/null | grep -v SEED | head -1 || true)
  if [[ -n "$latest" ]]; then
    local d
    d=$(basename "$latest" | sed 's/_brief.md//')
    echo "⚠️  오늘($today) 산출물 없음 — ${d} 아카이브 (studio_resolve_archive_date)" >&2
    echo "$d"
    return 0
  fi

  echo "$today"
}
