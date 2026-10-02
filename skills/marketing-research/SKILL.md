<!--
이 파일은 두 섹션으로 나뉩니다.
  ## STABLE   — 브랜드 규칙·품질 게이트. 사람만 편집.
  ## LEARNED  — 경험적 학습. scripts/curate-playbook.sh 만 편집.
                append-only + tombstone. 삭제 금지.
-->

---
name: marketing-research
description: "M1 콘텐츠 전략: 주간 리서치 브리프 — channels/research 위임."
version: 1.2.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [M1, research, marketing, ai, trends]
    stage: M1
    related_skills: [content-orchestration, channels/research, shared/handoff, shared/validate, prompts/strategy-frameworks]
---

# Marketing Research — M1 (Legacy Alias)

> **v1.2.0:** 상세 워크플로는 `channels/research` + `content-orchestration` M1.
> 이 skill은 **하위 호환 alias** — cron·Telegram·hermes-run 기존 호출 유지.

## Stage

**M1 content_strategy** — [marketing-ai-orchestration-harness](https://github.com/saewookkangboy/marketing-ai-orchestration-harness) M1에 해당.

## 실행 (결정적, ~15s)

```bash
~/Hermes_Harness_dailybrief/scripts/run-research-brief.sh
~/Hermes_Harness_dailybrief/scripts/run-pipeline.sh         # M1+M2
```

## 상세 Skill

`skills/channels/research/SKILL.md` 참조:
- P1 GATHER → `gather-web-research.py`
- P2 ASSEMBLE → `assemble-research-brief.py`
- P3 VALIDATE → `validate-output.sh research`
- Handoff → M2 `topic_clusters`

## 프레임워크

`skills/prompts/strategy-frameworks.md` — MECE, SCQA, SWOT, 콘텐츠 퍼널

## 출력

`content/research/YYYY-MM-DD_brief.md`

## 후속 (M2)

```bash
~/Hermes_Harness_dailybrief/scripts/run-content-package.sh
```

> "이 브리프 기반으로 M2 콘텐츠 패키지(blog+insta+linkedin)를 생성할까요?"

## Hermes CLI

```bash
hermes chat -q "..." -s marketing-research -t hermes-cli
# 권장: content-orchestration 또는 channels/research
```

## LEARNED
<!-- Curator 전용. 사람이 직접 편집하지 말 것. -->

