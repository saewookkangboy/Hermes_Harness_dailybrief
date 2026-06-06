# Strategy Frameworks — 마케팅 프롬프트

[strategy-prompts](https://github.com/saewookkangboy/strategy-prompts)에서 Hermes Content Studio M1/M2에 적용할 프레임워크.

## M1 — Research / Strategy (channels/research)

| 프레임워크 | 적용 |
|-----------|------|
| MECE 이슈 트리 | Top 5 인사이트 분류 |
| SCQA / 피라미드 | Executive Summary |
| SWOT + So What | 마케터 관점 필드 |
| 콘텐츠 퍼널 | 콘텐츠 캘린더 채널 배분 |
| 채널 믹스 | blog / insta / linkedin / lecture |

### M1 프롬프트 블록 (에이전트용)

```
[역할] B2B 마케터 리서치 애널리스트
[입력] content/research/_search_context_{date}.md
[프레임] MECE + SCQA
[출력] brief.md — Executive Summary 3–5문장, Top 5, 각 항목에 콘텐츠 소재 채널 태그
[제약] 출처 URL 필수, 한국 시장 1건+, 광고성 제외
```

## M2 — Content Execution (channels/blog, instagram, linkedin)

| 프레임워크 | 채널 |
|-----------|------|
| AIDA | blog Hook, linkedin Hook 2줄 |
| 콘셉트 정교화 | unified-context 주제 1문장 |
| 크리에이티브 브리프 | packages/*-context.md |
| 콘텐츠 퍼널 | blog=고려, insta=인지, linkedin=신뢰 |

### M2 blog 프롬프트

```
[역할] SEO/AEO/GEO 콘텐츠 writer
[톤] 실무형 해요체, 3000자 이내
[구조] Direct Answer → H2×3+ → FAQ 3+ → GEO 인용 블록
[출처] brief 인사이트 #N + URL
```

### M2 LinkedIn 프롬프트

```
[역할] B2B LinkedIn Creator (1인칭 전문가)
[프레임] AIDA + feed grammar
[구조] Hook 2줄 → Context → →불릿 3–5 → CTA 질문
[제약] 1300자, 본문 URL 없음, 데이터 1+
```

## M3 — Optimization

- LinkedIn: `skills/channels/linkedin/01-analyze.md` ~ `04-validate.md`
- `HERMES_ENHANCE=1` polish 시 **구조 유지**, 문장만 개선

## 사용 규칙

1. 한 번에 **하나의 프레임워크**만 적용
2. 결정적 assemble 후 polish (순서 역전 금지)
3. `[DESCRIBE YOUR BUSINESS PROBLEM]` → brief Executive Summary로 대체

## 모델별 참고 (strategy-prompts)

| 모델 | 특성 |
|------|------|
| Claude | 단계·출력 형식 명확 |
| ChatGPT | Deliver/요청 항목 명시 |
| Gemini | 표·불릿 구조화 |
| Perplexity | 검색·출처 (gather-web-research.py가 대체) |
