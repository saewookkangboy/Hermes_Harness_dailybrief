# LinkedIn Step 1 — Analyze (M3)

**입력:** `content/research/{date}_brief.md`, `content/research/_search_context_{date}.md`
**선택:** 사용자 피드 관측 텍스트 (붙여넣기)

## 목적

리서치·관측을 바탕으로 **이번 주 LinkedIn 피드 각도**를 분석합니다.
[linkedin-feed-strategy-maker /analyze](https://github.com/saewookkangboy/linkedin-feed-strategy-maker) 패턴.

## 출력

`content/packages/{date}_linkedin-analysis.md`

```markdown
# LinkedIn 피드 분석 — {date}

## 표본 요약
- 핵심 트렌드 3개 (출처 링크)
- B2B 마케터 관점 시사점

## 경쟁·유사 포스트 패턴
- hook 패턴 (2줄 유형)
- 불릿 밀도·문단 길이

## 리스크·컴플라이언스
- 과장·허위 통계 없음
- 출처 불명 데이터 제외

## 추천 각도 (1–3)
1. ...
```

## 프롬프트 힌트 (strategy-prompts)

- MECE: 트렌드 / 실무 / 한국 시장 축
- So What: "마케터가 월요일에 올릴 한 가지"

## 다음

→ `02-strategy.md`
