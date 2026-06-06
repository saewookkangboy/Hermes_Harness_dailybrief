#!/usr/bin/env bash
# Hermes Content Studio — 산출물 품질 검증 (품질 게이트 강화)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
TYPE="${1:?Usage: validate-output.sh research|blog|instagram|linkedin|lecture FILE}"
FILE="${2:?Missing file path}"

fail() { echo "❌ $1" >&2; exit 1; }
warn() { echo "⚠️  $1" >&2; }
pass() { echo "✅ $1"; }

[[ -f "$FILE" ]] || fail "파일 없음: $FILE"

SIZE=$(wc -c < "$FILE" | tr -d ' ')
(( SIZE > 200 )) || fail "파일 너무 짧음 (${SIZE} bytes): $FILE"

case "$TYPE" in
  research)
    grep -q "## Executive Summary" "$FILE" || fail "Executive Summary 섹션 없음"
    grep -q "## Top 7" "$FILE" || fail "Top 7 인사이트 섹션 없음"
    grep -q "## 페르소나" "$FILE" || fail "페르소나 섹션 없음"
    grep -q "Insight 도출" "$FILE" || fail "Insight 도출 필드 없음"
    grep -q "활용 방법" "$FILE" || fail "활용 방법 필드 없음"
    grep -q "## 심층 분석" "$FILE" || fail "심층 분석 섹션 없음"
    grep -q "## 콘텐츠 캘린더" "$FILE" || fail "콘텐츠 캘린더 섹션 없음"
    grep -qE "https?://" "$FILE" || fail "출처 URL 없음"
    python3 - <<PY || fail "브리프 품질: 마케터 관점 중복 또는 한국어 요약 부족"
from pathlib import Path
import re
text = Path("$FILE").read_text(encoding="utf-8")
views = re.findall(r"- \*\*마케터 관점:\*\* (.+)", text)
summaries = re.findall(r"- \*\*(?:내용 )?요약:\*\* (.+)", text)
if len(views) >= 2 and len(set(views)) < len(views):
    raise SystemExit("마케터 관점이 중복됩니다")
for s in summaries:
    if len(re.findall(r"[가-힣]", s)) < 20:
        raise SystemExit(f"한국어 요약 부족: {s[:40]}")
if views and all("재해석해 적용" in v for v in views):
    raise SystemExit("generic 마케터 관점 fallback만 존재")
insight_count = len(re.findall(r"^### \d+\.", text, re.M))
if insight_count < 7:
    raise SystemExit(f"Top 7 미달: {insight_count}개")
PY
    pass "research brief OK: $FILE ($SIZE bytes)"
    ;;
  blog-article)
    grep -q "한 줄 요약" "$FILE" || fail "Direct Answer(한 줄 요약) 섹션 없음"
    grep -q "FAQ" "$FILE" || fail "FAQ (AEO) 섹션 없음"
    grep -qE "GEO|GEO 인용" "$FILE" || warn "GEO 섹션 없음"
    grep -q "실무 적용" "$FILE" || fail "실무 적용 섹션 없음"
    CHARS=$(python3 -c "print(len(open('$FILE', encoding='utf-8').read()))")
    (( CHARS >= 2500 )) || warn "본문 확장 미달(2500자 미만): ${CHARS}"
    (( CHARS <= 15000 )) || warn "15000자 초과: ${CHARS}"
    pass "blog article OK: $FILE (${CHARS} chars)"
    ;;
  blog)
    grep -qi "<title>" "$FILE" || fail "HTML title 없음"
    grep -qi "meta name=\"description\"" "$FILE" || fail "meta description 없음"
    grep -qi "<h1" "$FILE" || fail "H1 없음"
    grep -qi "canonical" "$FILE" || fail "canonical URL 없음"
    grep -qi "FAQPage" "$FILE" || fail "FAQ schema (AEO) 없음"
    grep -qi "application/ld+json" "$FILE" || fail "JSON-LD 없음"
    H2_COUNT=$(grep -c "<h2" "$FILE" || true)
    (( H2_COUNT >= 3 )) || warn "H2 3개 미만 (SEO/AEO): $H2_COUNT"
    grep -qi "geo-quote\|GEO" "$FILE" || warn "GEO 인용 블록 없음"
    pass "blog HTML OK: $FILE ($SIZE bytes, H2=$H2_COUNT)"
    ;;
  instagram)
    grep -qi "Slide 1" "$FILE" || grep -qi "슬라이드" "$FILE" || fail "슬라이드 구조 없음"
    grep -qi "Nano Banana Pro 2" "$FILE" || fail "Gemini Nano Banana Pro 2 명시 없음"
    grep -qi "4:5\|1080×1350" "$FILE" || fail "4:5 피드 비율(1080×1350) 명시 없음"
    grep -qi "나눔고딕\|Nanum Gothic" "$FILE" || fail "나눔고딕 폰트 명시 없음"
    grep -qi "이미지 생성 프롬프트\|Prompt:" "$FILE" || fail "이미지 생성 프롬프트 없음"
    grep -qi "뉴스피드 알고리즘\|알고리즘" "$FILE" || warn "알고리즘 최적화 섹션 없음"
    grep -qi "Alt text" "$FILE" || warn "alt text 없음"
    grep -qi "해시태그" "$FILE" || fail "해시태그 섹션 없음"
    python3 - <<PY || fail "해시태그 5개 미달"
import re
from pathlib import Path
text = Path("$FILE").read_text(encoding="utf-8")
tags = re.findall(r"#[\w가-힣]+", text.split("## 출처")[0].split("---")[-1])
if len(tags) < 5:
    raise SystemExit(f"해시태그 {len(tags)}개")
PY
    grep -qi "캡션" "$FILE" || fail "캡션 섹션 없음"
    SLIDE_COUNT=$(grep -c "^### Slide" "$FILE" || true)
    (( SLIDE_COUNT == 3 )) || warn "캐러셀 3장 권장: $SLIDE_COUNT"
    pass "instagram OK: $FILE ($SIZE bytes, slides=$SLIDE_COUNT)"
    ;;
  linkedin)
    (( SIZE > 600 )) || fail "링크드인 포스트 너무 짧음 (${SIZE} bytes)"
    grep -q "→" "$FILE" || fail "불릿(→) 없음"
    grep -qi "댓글\|?" "$FILE" || warn "댓글 유도 CTA 없음"
    grep -qi "Gemini Nano Banana Pro 2\|Nano Banana Pro 2" "$FILE" || fail "Gemini Nano Banana Pro 2 명시 없음"
    grep -qi "2×2\|2x2" "$FILE" || fail "2×2 웹툰 레이아웃 명시 없음"
    grep -qi "이미지 생성 프롬프트" "$FILE" || fail "이미지 생성 프롬프트 섹션 없음"
    POST_CHARS=$(python3 -c "
text=open('$FILE',encoding='utf-8').read()
post=text.split('---')[0].strip()
print(len(post))
")
    (( POST_CHARS <= 1300 )) || warn "포스트 본문 1300자 초과: ${POST_CHARS}"
    pass "linkedin OK: $FILE ($SIZE bytes, post=${POST_CHARS} chars)"
    ;;
  instagram-context)
    grep -qi "Instagram 컨텍스트" "$FILE" || fail "Instagram 컨텍스트 헤더 없음"
    grep -qi "캐러셀 구조\|뉴스피드 알고리즘" "$FILE" || fail "캐러셀/알고리즘 섹션 없음"
    grep -qi "4:5\|1080×1350" "$FILE" || fail "4:5 피드 비율 명시 없음"
    grep -qi "Nano Banana Pro 2\|나눔고딕" "$FILE" || warn "Gemini/나눔고딕 스펙 없음"
    grep -qi "## Gemini 이미지 생성 프롬프트" "$FILE" || fail "Gemini 이미지 프롬프트 섹션 없음"
    grep -c "Slide [123]/3" "$FILE" | grep -q "^3$" || fail "슬라이드별 Gemini 프롬프트 3개 필요"
    pass "instagram context OK: $FILE ($SIZE bytes)"
    ;;
  linkedin-context)
    grep -qi "LinkedIn 컨텍스트" "$FILE" || fail "LinkedIn 컨텍스트 헤더 없음"
    grep -qi "포스트 구조" "$FILE" || fail "포스트 구조 섹션 없음"
    grep -qi "## Gemini 이미지 생성 프롬프트" "$FILE" || fail "Gemini 이미지 프롬프트 섹션 없음"
    grep -qi "gemini-3-pro-image-preview" "$FILE" || fail "Gemini API 모델 명시 없음"
    pass "linkedin context OK: $FILE ($SIZE bytes)"
    ;;
  unified-context)
    grep -qi "통합 콘텐츠 컨텍스트" "$FILE" || fail "통합 컨텍스트 헤더 없음"
    grep -qi "SEO / AEO / GEO" "$FILE" || fail "SEO/AEO/GEO 섹션 없음"
    grep -qi "## Research Brief 발췌" "$FILE" || fail "Research Brief 발췌 섹션 없음"
    grep -q "| # |" "$FILE" || fail "Research Brief 표 형식 없음"
    pass "unified context OK: $FILE ($SIZE bytes)"
    ;;
  lecture)
    grep -qiE "목차|outline|강의|슬라이드" "$FILE" || fail "강의 구조 없음"
    pass "lecture OK: $FILE ($SIZE bytes)"
    ;;
  *)
    fail "알 수 없는 타입: $TYPE"
    ;;
esac
