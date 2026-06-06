---
name: harness-ops
description: "Harness engineering 운영: init, eval, 성능 게이트, 세션 핸드오프. awesome-harness-engineering 기반."
version: 1.2.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [harness, performance, eval, observability, init]
    related_skills: [content-pipeline, telegram-commander, marketing-research]
---

# Harness Ops — 성능·신뢰성 운영

[awesome-harness-engineering](https://github.com/walkinglabs/awesome-harness-engineering) 5-Subsystem 기반.

## 세션 시작 (Mandatory)

```bash
~/hermes-content-studio/scripts/init.sh
cat ~/hermes-content-studio/.harness/progress.md
```

## 성능 Eval

```bash
# 구조 검증 (빠름, ~1s)
~/hermes-content-studio/scripts/harness-eval.sh --quick

# 벤치마크 + 회귀 검출 (~30s)
~/hermes-content-studio/scripts/harness-eval.sh --record
```

## 결정적 파이프라인 (권장)

LLM 없이 ~45초:

```bash
~/hermes-content-studio/scripts/run-pipeline.sh
```

LLM polish (선택, 2-5분 추가):

```bash
HERMES_ENHANCE=1 ~/hermes-content-studio/scripts/run-pipeline.sh
```

## 완료 정의

1. `validate-output.sh` 통과
2. `.harness/progress.md` 업데이트
3. Telegram 요청 시 Notion 100% + Permalink
4. 성능 회귀 없음 (`harness-eval.sh`)

## 상태 파일

| 파일 | 용도 |
|------|------|
| `.harness/feature_list.json` | 기능 범위·검증 |
| `.harness/progress.md` | 진행 SoT |
| `.harness/session-handoff.md` | 다음 세션 |
| `.harness/traces/` | 타이밍 트레이스 |
| `.harness/eval-results.json` | 벤치마크 기록 |

## Anti-patterns

- init.sh 없이 파이프라인 실행
- 검증 없이 완료 선언
- 결정적 가능한 작업에 LLM 전체 재생성
- deny_paths (`~/.hermes/.env` 등) 접근

## 참조

- `HARNESS.md` — 전체 스펙
- `config/harness.yaml` — SLA·가드레일
