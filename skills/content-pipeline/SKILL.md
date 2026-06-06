---
name: content-pipeline
description: "일일 콘텐츠 파이프라인: Brief SoT → blog · instagram · linkedin."
version: 1.3.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [content, marketing, pipeline, orchestration]
    related_skills: [content-orchestration, channels/research, channels/blog, channels/instagram, channels/linkedin, shared/validate, shared/handoff, content-studio-slides, notion-archive, telegram-commander]
---

# Content Pipeline — 오케스트레이션 라우터

> **v1.3.0:** 상세 워크플로는 `content-orchestration` + `channels/*`로 분리.
> 이 skill은 **트리거·스케줄·라우팅**만 담당합니다.

## 마스터 Skill

**`content-orchestration`** — M1~M5 전체 정의, handoff, scale modes.
설정: `config/content-orchestration.yaml`

## M 단계 요약

| Stage | 작업 | Skill | 스크립트 |
|-------|------|-------|----------|
| M1 | 리서치 브리프 | `channels/research` | `run-research-brief.sh` |
| M2 | blog + insta + linkedin | `channels/*` | `run-content-package.sh` |
| M3 | LinkedIn 최적화 | `channels/linkedin` | (선택 enhance) |
| M5 | Notion 아카이브 | `notion-archive` | `archive-to-notion.sh` |

## Brief SoT (M2 진입 조건)

1. **M1 선행:** `gather-web-research.py` → `{date}_brief.md` (Top 7)
2. **M2 자동:** `run-content-package.sh`가 당일 brief 재수집 후 조립
3. **건너뛰기:** `HERMES_SKIP_RESEARCH=1` (기존 brief 재사용)
4. **강제 갱신:** `HERMES_FORCE_RESEARCH=1`

## 일일 스케줄

| 시각 | Stage | 명령 |
|------|-------|------|
| 매일 08:00 | M1+M2 | `run-pipeline.sh` 또는 `run-content-package.sh` |
| Telegram | M1→M2→M5 | `telegram-pipeline.sh pipeline` |

## 빠른 실행

```bash
# 전체 (M1→M2)
~/hermes-content-studio/scripts/run-pipeline.sh

# M2만
~/hermes-content-studio/scripts/run-content-package.sh

# Telegram
~/hermes-content-studio/scripts/telegram-pipeline.sh pipeline
```

## 채널 Skill Index

| 채널 | Skill | 출력 |
|------|-------|------|
| research | `skills/channels/research/` | `content/research/` |
| blog | `skills/channels/blog/` | `content/blog/` + `packages/*_blog-article.md` |
| instagram | `skills/channels/instagram/` | `content/instagram/` |
| linkedin | `skills/channels/linkedin/` | `content/linkedin/` + analyze→draft |
| lectures | `content-studio-slides` | `content/lectures/` |

## 프롬프트 자산

- `skills/prompts/strategy-frameworks.md` — [strategy-prompts](https://github.com/saewookkangboy/strategy-prompts)
- `skills/prompts/linkedin-pipeline.md` — [linkedin-feed-strategy-maker](https://github.com/saewookkangboy/linkedin-feed-strategy-maker)

## 완료 정의

1. `shared/validate` — validate-output.sh 통과
2. `content/{channel}/` 저장
3. Telegram → `archive-to-notion.sh --force` + Permalink
4. `.harness/progress.md` 업데이트

## Hermes CLI

```bash
~/hermes-content-studio/scripts/hermes-run.sh "..." --skills content-orchestration -t hermes-cli
```

## Anti-patterns

- 이 skill만 로드하고 channel skill 생략
- 결정적 파이프라인 가능한데 LLM 전체 재생성
- 검증 없이 완료 선언
