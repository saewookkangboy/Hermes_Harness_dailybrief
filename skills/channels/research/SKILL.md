---
name: channel-research
description: "M1 콘텐츠 전략: 일일 리서치 브리프 수집·분석·handoff (Top 7)."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [M1, research, strategy, trends]
    stage: M1
    related_skills: [content-orchestration, marketing-research, shared/validate, shared/handoff]
---

# Channel: Research (M1)

**Stage:** M1 content_strategy · **결정적:** ~15s

## Phase 맵

| Phase | Step | 스크립트/Skill | 출력 |
|-------|------|----------------|------|
| P0 | INPUT | 사용자 요청 / cron | 키워드·주제 |
| P1 | GATHER | `gather-web-research.py` | `_search_context_{date}.json` |
| P2 | ASSEMBLE | `assemble-research-brief.py` + `lib/brief_quality.py` | `{date}_brief.md` |
| P3 | VALIDATE | `validate-output.sh research` | ✅/❌ |
| P4 | HANDOFF | `shared/handoff` | M2 topic_clusters |

## 페르소나 (v2)

21년차 디지털 마케터(브랜드·콘텐츠·퍼포먼스·그로스·전략) ·  
최근 4~5년 AI 리터러시·거버넌스·책임있는 AI · AX·AI Native 컨설턴트

설정: `config/research-brief.yaml`

## 리서치 커버리지 (일일)

- 글로벌·대한민국 뉴스·데이터
- AI 마케팅 기술·Repo · LLM 4사(ChatGPT·Claude·Gemini·Perplexity)
- AX · AI 리터러시·거버넌스 · AI 실무·도입 현황
- 프롬프트·컨텍스트·하네스·Hermes Agent·AI Agent

## Insight 파이프라인

리서치 → 내용 요약 → Insight 도출 → 활용 방법 → 가이드·팁

## 실행

```bash
~/hermes-content-studio/scripts/run-research-brief.sh [YYYY-MM-DD]
```

## 출력 스키마

파일: `content/research/YYYY-MM-DD_brief.md`

필수 섹션 (validate-output.sh):
- Executive Summary
- Top 7 인사이트
- 심층 분석
- 콘텐츠 캘린더
- 출처 URL

## 분석 프레임 (strategy-prompts M1)

각 인사이트 (`scripts/lib/brief_quality.py` · 21년차 AI·AX 페르소나):
| 필드 | 설명 |
|------|------|
| 한국어 제목 | `localize_title()` |
| 리서치 영역 | AX · LLM · 거버넌스 · 에이전트 · 하네스 등 |
| 내용 요약 | 한국어 2~3문장 (영문 스니펫 금지) |
| Insight 도출 | So What — 핵심 시사점 |
| 마케터 관점 | 1인칭 현장 서술 (저는·현장에서) |
| 활용 방법 | 브랜드·콘텐츠·퍼포먼스·AX 적용 |
| 가이드·팁 | 실무 체크리스트 |
| 시장 영향 / 한국 적용 / 기회 | topic·채널별 차별화 |
| 신뢰도 | high / medium / low |

## Handoff → M2

**Brief SoT 필수** — M2는 brief + search_context 없이 실행 불가.

| 단계 | 산출물 |
|------|--------|
| P1 GATHER | `content/research/_search_context_{date}.json` |
| P2 ASSEMBLE | `content/research/{date}_brief.md` (Top 7) |
| M2 | blog · instagram · linkedin (`run-content-package.sh`) |

`run-content-package.sh`는 **당일 자동으로 M1 선행**(gather → brief) 후 M2 조립.

```json
{
  "stage": "M1",
  "channel": "research",
  "next_stage_ready": true,
  "handoff_payload": {
    "topic_clusters": [{"topic": "...", "channels": ["blog","linkedin"], "insight_ref": "#1"}],
    "executive_summary": "...",
    "content_calendar": []
  }
}
```

## LLM polish (선택)

`HERMES_ENHANCE=1` 또는 run-research-brief.sh 내 Hermes 호출 — 구조 유지, 문장만 다듬기.

## 다음

M2 실행 제안:
> "이 브리프 기반으로 M2 콘텐츠 패키지(blog+insta+linkedin)를 생성할까요?"

```bash
~/hermes-content-studio/scripts/run-content-package.sh
```
