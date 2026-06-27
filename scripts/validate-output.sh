#!/usr/bin/env bash
# Hermes Content Studio — 산출물 품질 검증 (품질 게이트 강화)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
TYPE="${1:?Usage: validate-output.sh research|blog|instagram|linkedin|newsletter|newsletter-html|newsletter-paste|newsletter-subject-scores|lecture FILE}"
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
    grep -qi "| Newsletter |" "$FILE" || fail "Newsletter 채널 행 없음"
    pass "unified context OK: $FILE ($SIZE bytes)"
    ;;
  unified-newsletter)
    grep -qi "## Newsletter (B2B 이메일)" "$FILE" || fail "Newsletter unified 섹션 없음"
    grep -qi "권장 제목" "$FILE" || fail "권장 제목 없음"
    pass "unified newsletter patch OK: $FILE ($SIZE bytes)"
    ;;
  newsletter)
    grep -qi "## 30초 TLDR" "$FILE" || fail "TLDR 섹션 없음"
    grep -qi "## 오늘의 1가지" "$FILE" || fail "Hero 섹션 없음"
    grep -qi "## 3분 읽기" "$FILE" || fail "Insight 모듈 섹션 없음"
    grep -qi "이번 주 실습 1가지" "$FILE" || fail "Single CTA 없음"
    grep -qi "제목 후보" "$FILE" || fail "제목 A/B 없음"
    grep -qi "자동 스코어" "$FILE" || fail "제목 스코어 없음"
    grep -qi "권장 제목" "$FILE" || fail "권장 제목 없음"
    grep -qi "프리헤더" "$FILE" || fail "프리헤더 없음"
    grep -qi "다음 호" "$FILE" || fail "다음 호 예고 없음"
    MOD_COUNT=$(grep -c "^### [123]\." "$FILE" || true)
    (( MOD_COUNT >= 3 )) || fail "Insight 모듈 3개 미달: $MOD_COUNT"
    python3 - "$FILE" <<'PY' || fail "뉴스레터 길이·제목 게이트"
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
head = text.split("## 30초 TLDR")[0]
for row in re.findall(r"\|\s*\d+.*?\|\s*\d+\s*\|\s*(.+?)\s*\|", head):
    title = row.strip().strip("`")
    if len(title) > 50:
        raise SystemExit(f"제목 50자 초과: {len(title)}")
body = text.split("## 30초 TLDR", 1)[-1]
chars = len(re.sub(r"\s+", " ", body))
if chars < 600:
    raise SystemExit(f"본문 너무 짧음: {chars}")
if chars > 4500:
    raise SystemExit(f"본문 너무 김(완독 저하): {chars}")
PY
    python3 - "$FILE" <<'PY' || fail "뉴스레터 완성도·잘림 게이트"
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "hermes-content-studio/scripts"))
from lib.newsletter_complete import audit_newsletter_md
text = Path(sys.argv[1]).read_text(encoding="utf-8")
issues = audit_newsletter_md(text)
if issues:
    raise SystemExit("; ".join(issues[:5]))
PY
    pass "newsletter OK: $FILE ($SIZE bytes, modules=$MOD_COUNT)"
    ;;
  newsletter-context)
    grep -qi "Newsletter 컨텍스트" "$FILE" || fail "Newsletter 컨텍스트 헤더 없음"
    grep -qi "CTOR" "$FILE" || fail "CTOR 벤치마크 없음"
    grep -qi "모듈 체크리스트" "$FILE" || fail "모듈 체크리스트 없음"
    pass "newsletter context OK: $FILE ($SIZE bytes)"
    ;;
  newsletter-html)
    grep -qi "30초 TLDR" "$FILE" || fail "TLDR 모듈 없음"
    grep -qi "이번 주 실습" "$FILE" || fail "CTA 모듈 없음"
    grep -qi "role=\"presentation\"" "$FILE" || fail "이메일 테이블 레이아웃 없음"
    grep -qi "{{" "$FILE" && fail "미치환 플레이스홀더 남음"
    pass "newsletter HTML OK: $FILE ($SIZE bytes)"
    ;;
  newsletter-paste)
    grep -qi "붙여넣기 팩" "$FILE" || fail "붙여넣기 팩 헤더 없음"
    grep -qi "## §1 제목" "$FILE" || fail "§1 제목 섹션 없음"
    grep -qi "## §2 프리헤더" "$FILE" || fail "§2 프리헤더 섹션 없음"
    grep -qi "## §3 본문" "$FILE" || fail "§3 본문 섹션 없음"
    grep -qi "## §4 본문" "$FILE" || fail "§4 HTML 섹션 없음"
    grep -qi "## 30초 TLDR" "$FILE" || fail "본문 TLDR 코드블록 없음"
    pass "newsletter paste OK: $FILE ($SIZE bytes)"
    ;;
  newsletter-subject-scores)
    python3 - "$FILE" <<'PY' || fail "제목 스코어 JSON 게이트"
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
data = json.loads(p.read_text(encoding="utf-8"))
winner = data.get("winner") or {}
cands = data.get("candidates") or []
if not winner or not cands:
    raise SystemExit("winner/candidates 없음")
import yaml
from pathlib import Path as P
cfg_path = P.home() / "hermes-content-studio" / "config" / "newsletter.yaml"
min_score = 40
if cfg_path.exists():
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    min_score = int((cfg.get("scoring") or {}).get("min_winner_score", 40))
if winner.get("score", 0) < min_score:
    raise SystemExit(f"winner score 낮음: {winner.get('score')} < {min_score}")
for c in cands:
    if len(c.get("text", "")) > 50:
        raise SystemExit(f"제목 50자 초과: {c['text']}")
PY
    pass "newsletter subject scores OK: $FILE"
    ;;
  lecture)
    grep -qiE "목차|outline|강의|슬라이드" "$FILE" || fail "강의 구조 없음"
    pass "lecture OK: $FILE ($SIZE bytes)"
    ;;
  *)
    fail "알 수 없는 타입: $TYPE"
    ;;
esac
