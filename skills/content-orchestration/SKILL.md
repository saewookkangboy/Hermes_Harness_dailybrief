---
name: content-orchestration
description: "M1~M5 마케팅 콘텐츠 오케스트레이션: 전략→실행→최적화→아카이브. marketing-ai-orchestration-harness + harness-100 패턴."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [orchestration, marketing, M1, M2, M3, pipeline, harness]
    related_skills: [content-pipeline, channels/research, channels/blog, channels/instagram, channels/linkedin, shared/handoff, shared/validate, notion-archive, telegram-commander]
---

# Content Orchestration — M1~M5 마케팅 하네스

Hermes Content Studio의 **마스터 오케스트레이터**.
[marketing-ai-orchestration-harness](https://github.com/saewookkangboy/marketing-ai-orchestration-harness) M1~M5 + [harness-100](https://github.com/saewookkangboy/harness-100) 3-layer skill 패턴을 적용합니다.

## M 단계 ↔ Hermes 매핑

| Stage | 이름 | Hermes | 스크립트 | Skill |
|-------|------|--------|----------|-------|
| **M1** | 콘텐츠 전략 | research brief | `run-research-brief.sh` | `channels/research` |
| **M2** | 콘텐츠 실행 | blog + insta + linkedin | `run-content-package.sh` | `channels/*` |
| **M3** | 최적화 | LinkedIn analyze→draft | (skill 내) | `channels/linkedin` |
| **M4** | 성과 분석 | 시뮬레이션 | — | `harness-ops` |
| **M5** | 아카이브·보고 | Notion + Permalink | `archive-to-notion.sh` | `notion-archive` |
| **SYNTH** | 통합 요약 | unified-context | — | `shared/handoff` |

설정 SoT: `config/content-orchestration.yaml` · 스키마: `schemas/handoff.schema.json`

## 공통 5-Phase (모든 채널)

```
P0 INPUT → P1 CONTEXT → P2 ASSEMBLE → P3 VALIDATE → P4 ARCHIVE → [P5 ENHANCE]
```

| Phase | 역할 | 산출물 패턴 |
|-------|------|-------------|
| P0 | brief·search_context·사용자 요청 | `{date}_brief.md` |
| P1 | 채널 컨텍스트 | `packages/{date}_{channel}-context.md` |
| P2 | 결정적 조립 | `content/{channel}/{date}_{channel}_{slug}.{ext}` |
| P3 | 품질 게이트 | `validate-output.sh` |
| P4 | Notion + Telegram | Permalink |
| P5 | LLM polish (선택) | `HERMES_ENHANCE=1` |

## Scale Modes (harness-100)

| 모드 | 명령 | 단계 |
|------|------|------|
| **full** | `run-pipeline.sh` | M1→M2→M5 |
| **reduced** | `run-content-package.sh` | M2 (brief 존재 시) |
| **single_channel** | 채널 skill만 | M2 subset |
| **enhance** | `HERMES_ENHANCE=1 run-content-package.sh` | M2 + M3 polish |
| **telegram** | `telegram-pipeline.sh pipeline` | M1→M2→M5 (~15s) |

## 빠른 실행

```bash
# 결정적 전체 (권장, ~45s)
~/hermes-content-studio/scripts/run-pipeline.sh

# M1만
~/hermes-content-studio/scripts/run-research-brief.sh

# M2만 (brief 필요)
~/hermes-content-studio/scripts/run-content-package.sh

# Telegram E2E
~/hermes-content-studio/scripts/telegram-pipeline.sh pipeline
```

## Handoff 규칙

1. 각 단계 완료 시 `handoff_payload`를 다음 stage 입력으로 전달
2. `inputs_used`에 `content/research/_search_context_*.md` 경로 기록
3. `next_stage_ready: false`면 해당 stage 재실행 — 건너뛰기 금지
4. `artifacts.conditions_applied`에 `content_output_conditions` 반영 내역 기록

Handoff skill: `shared/handoff`

## 채널 Skill 라우팅

| 채널 | Index Skill | 결정적 스크립트 |
|------|-------------|-----------------|
| research | `channels/research` | `assemble-research-brief.py` |
| blog | `channels/blog` | `assemble-content-package.py` |
| instagram | `channels/instagram` | `assemble-content-package.py` |
| linkedin | `channels/linkedin` | `assemble-content-package.py` + analyze→draft |
| lectures | `content-studio-slides` | `run-lecture-slides.sh` |

## 프롬프트 자산

- **전략·마케팅:** `skills/prompts/strategy-frameworks.md` ([strategy-prompts](https://github.com/saewookkangboy/strategy-prompts))
- **LinkedIn 파이프:** `skills/prompts/linkedin-pipeline.md` ([linkedin-feed-strategy-maker](https://github.com/saewookkangboy/linkedin-feed-strategy-maker))

## 품질 게이트 (완료 전 필수)

1. `scripts/validate-output.sh` 통과
2. 산출물 `content/{channel}/` 저장
3. Telegram 요청 시 `archive-to-notion.sh --force` + Permalink
4. `.harness/progress.md` 업데이트

## Anti-patterns

- M2를 LLM으로 전체 재생성 (결정적 파이프라인 가능 시)
- handoff 없이 채널 skill 단독 실행 후 "완료" 선언
- LinkedIn 본문 URL 삽입 (첫 댓글 전략 위반)
- 검증 없이 Notion 동기화만 전송

## Harness

세션 시작: `scripts/init.sh` → `.harness/progress.md`
성능 eval: `scripts/harness-eval.sh --quick`
도구 마스킹: `-t hermes-cli` (MCP·브라우저 제외)
