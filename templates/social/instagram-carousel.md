# 인스타그램 캐러셀 템플릿 (3장 · 정보형 · 4:5 · Gemini)

## 메타
- 주제: {{TOPIC}}
- 날짜: {{DATE}}
- 이미지 엔진: Gemini Nano Banana Pro 2 (`gemini-3-pro-image-preview`)
- 비율: 4:5 · 1080×1350 · 2K
- 폰트: 나눔고딕 (Nanum Gothic) · 한국어 전용

## 뉴스피드 알고리즘
- 4:5 세로 — 피드 점유·정보형 캐러셀 권장 (2026)
- 1장 훅 → 2장 가치 → 3장 저장 CTA
- 미완독 재노출 · save rate · swipe completion
- 캡션 첫 125자 훅 · 해시태그 5개

## 비주얼 컨셉
- 정보형 인포그래픽 카드 (저장형 교육 콘텐츠)
- 나눔고딕 Bold/Regular · Hangul 정확 렌더링
- 중앙 1080×1080 안전 영역 (그리드 크롭 대비)
- #FFE500 포인트 액센트

## 캐러셀 3장

### Slide 1/3 — Hook
- **헤드라인:** 2026 {{HOOK}}
- **본문:** B2B 마케팅 변화 · 스와이프 유도

### Slide 2/3 — Insight
- **헤드라인:** {{INSIGHT_TITLE}}
- **본문:** {{INSIGHT_LINE1}} · {{INSIGHT_LINE2}}

### Slide 3/3 — CTA
- **헤드라인:** 실무에 바로 써요
- **본문:** 캐러셀 저장 · 팀과 공유

## Gemini 프롬프트 규칙 (Nano Banana Pro 2)
- aspect_ratio=4:5 · 1080×1350
- 헤드라인·본문을 프롬프트에 **정확한 한국어**로 명시
- `CRITICAL: Korean Hangul legible, Nanum Gothic (나눔고딕)`
- Negative: broken Korean, 1:1 square, speech bubbles, cluttered

## 캡션 (가독성)
```
💬 {{HOOK}} — 2026 B2B 마케팅...

📌 핵심
→ {{TAKEAWAY_LINE}}

💡 한 줄 정리
{{TAKEAWAY}}

👉 캐러셀 저장 + 프로필 링크

---
{{HASHTAGS_5}}
```

## 체크리스트
- [ ] 3장 캐러셀 · 4:5 동일 비율
- [ ] 나눔고딕 · Hangul 깨짐 없음
- [ ] 저장 유도 CTA
- [ ] 슬라이드별 alt text
- [ ] 해시태그 5개
