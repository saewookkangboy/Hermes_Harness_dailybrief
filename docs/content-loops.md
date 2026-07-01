# Content Loops — Hermes Content Studio

> Loop Engineering 패턴을 **콘텐츠 공장** 도메인에 맞게 흡수한 운영 SoT  
> Harness v1.2 · 결정적 파이프라인 우선 · L1 report → L2 assisted → L3 HITL 발행만

---

## 한 줄 정의

**사람이 매일 “오늘 뭐 했지?”를 묻지 않도록**, 스케줄·검증·상태 기록이 에이전트 루프를 돌린다.  
M1→M5 **결정적 assemble**은 유지하고, LLM 루프는 triage·코칭·개인화 경로에만 쓴다.

---

## Harness vs Content Loop

| 구분 | Harness | Content Loop |
|------|---------|--------------|
| 범위 | 단일 세션·에이전트 샌드박스 | 스케줄 + 재검증 + run log |
| SoT | `.harness/progress.md`, `feature_list.json` | 동일 + `content-loop-runs.jsonl` |
| 완료 정의 | `validate-output.sh` | Harness DoD + Human Gate (아래) |

---

## 루프 목록

| ID | 패턴 | Cadence | Level | 스크립트 | 산출 |
|----|------|---------|-------|----------|------|
| **daily-content-triage** | Daily Triage | 평일 09:30 | **L1** | `cron-daily-content-triage.sh` | `content/logs/{date}_daily-triage.md` |
| morning-brief | (triage §1에 포함) | 평일 09:00 | L1 | `cron-morning-brief.sh` | stdout → Telegram |
| health-alert | (triage §3에 포함) | 10:00·18:00 | L1 | `cron-health-alert.sh` | 이상 시만 알림 |
| publish-schedule | HITL due | */15 | L1 | `cron-publish-schedule.sh` | HITL 카드 |
| competitive-watch | (triage §4, 월) | 월 09:00 | L1 | `cron-competitive-watch.sh` | watch 리포트 |
| **supervised-pipeline** | Factory run | 평일 10:00 | **L2** | `cron-supervised-pipeline.sh` | supervised 로그 · handoff JSON |
| **staging-supervised** | Blocking 회귀 | 토 11:00 | L2 | `cron-staging-supervised.sh` | staging eval · `HERMES_SUPERVISED_STAGING=1` |
| m4-coach | Performance feedback | _(P1-4 예정)_ | L1→L2 | `run-m4-coach.sh` | trait 코칭 |

---

## daily-content-triage (L1)

### 목적

오늘 콘텐츠 공장 상태를 **한 리포트**로 모은다. 자동 수정·발행 없음.

### 섹션

1. **Morning Pack** — proactive alerts + brief top3 (`hermes-agent.sh morning`, 결정적)
2. **Quality Audit** — `quality_auditor` + `validate-output` 요약
3. **Runtime Health** — Gateway · Ollama · watch-telegram
4. **Competitive Watch** — 월요일만
5. **Agents Eval A–D** — 월요일만 (`HERMES_TRIAGE_SKIP_AGENTS_EVAL=1`로 생략 가능)

### 등록

```bash
~/hermes-content-studio/scripts/setup-commander-cron.sh
# → cron-daily-triage  30 9 * * 1-5
```

### 수동 실행

```bash
~/hermes-content-studio/scripts/cron-daily-content-triage.sh
```

---

## supervised-pipeline (L2)

### 목적

M1→M2→(M2b)→Audit→M5를 **결정적 감독**으로 평일 자동 실행. triage(09:30) 이후 10:00 cron.

### 단계

| Stage | 스크립트 | 차단 |
|-------|----------|------|
| M1 | `run-research-brief.sh` | FAIL → blocked |
| GATE | `brief_gate` | FAIL → blocked |
| M2 | `run-content-package.sh` + validate | FAIL → blocked |
| M2b | `run-newsletter.sh` | FAIL → blocked |
| AUDIT | `quality_auditor` | WARN만 (차단 없음) |
| VOICE | `voice_style_audit` | WARN만 |
| HUMANIZE | `run-humanize-polish.sh` | WARN만 (`HERMES_CRON_HUMANIZE=1`) |
| NATURALNESS | `naturalness_audit` | WARN만 |
| M5 | `archive-to-notion.sh --force` | FAIL → blocked |

### Env (cron 기본값 — SoT: `config/content-quality.yaml` `supervised.cron_defaults`)

| 변수 | yaml 기본 | 설명 |
|------|-----------|------|
| `HERMES_CRON_HUMANIZE` | `1` | M2 후 결정적 humanize |
| `HERMES_CRON_SKIP_NEWSLETTER` | `0` | M2b newsletter ON |
| `HERMES_CRON_SKIP_NOTION` | `0` | M5 sync |
| `HERMES_CRON_SKIP_AUDIT` | `0` | Quality Audit |

환경 변수로 yaml 기본값 override 가능.

차단 강도 — `supervised.*_blocking` (프로덕션 2026-07-01~):

| 키 | yaml | `true` 시 |
|----|------|-----------|
| `voice_blocking` | `true` | VOICE FAIL → blocked |
| `humanize_blocking` | `false` | HUMANIZE FAIL → blocked |
| `naturalness_blocking` | `true` | naturalness 점수 FAIL → blocked |
| `budget_blocking` | `false` | budget kill/cap → NATURALNESS **FAIL** (`false`면 **WARN**) |

**스테이징** (`HERMES_SUPERVISED_STAGING=1`): `supervised.staging.*_blocking` 우선.

**주간 회귀:** `cron-staging-supervised` 토 11:00 (`setup-commander-cron.sh`).

### 등록

```bash
~/hermes-content-studio/scripts/setup-commander-cron.sh
# → cron-supervised-pipeline  0 10 * * 1-5
```

### 수동 실행

```bash
# dry-run (설정만 확인)
HERMES_CRON_SUPERVISED_DRY_RUN=1 ~/hermes-content-studio/scripts/cron-supervised-pipeline.sh

# M2b 제외 (cron 기본과 동일)
~/hermes-content-studio/scripts/cron-supervised-pipeline.sh

# M2b 포함
HERMES_CRON_SKIP_NEWSLETTER=0 ~/hermes-content-studio/scripts/cron-supervised-pipeline.sh
```

### 산출

- `content/logs/{date}_supervised-pipeline.md`
- `.harness/handoffs/{date}_supervised-pipeline.json`
- `.harness/content-loop-runs.jsonl` — 필드: `humanize`, `voice`, `naturalness`, `skip_newsletter`

실패 시 Telegram/Slack에 `blocked_at` 포함 알림. **채널 발행(HITL)은 자동 없음.**

---

## Maker / Checker (Verifier chain)

```
Implementer (결정적)          Verifier (독립)
────────────────────         ────────────────────────────
assemble-*.py                validate-output.sh
instagram_pipeline           quality_auditor.py
repurpose_pipeline           brief_gate (M2 진입 전)
```

- Implementer가 FAIL을 스스로 PASS로 바꾸지 않는다.
- Audit FAIL → L1 triage 리포트만 · L2에서 trait/coach 제안 (HITL).

---

## Human Gate (변경 금지)

| 작업 | 자동화 | 사람 |
|------|--------|------|
| M1→M2 assemble | ✅ cron/supervised 가능 | — |
| Notion M5 archive | ✅ sync 가능 | Permalink 확인 후 Telegram “완료” |
| 채널 발행 | ❌ | `publish_scheduler` → `/approve` |
| M2 LLM polish | `HERMES_ENHANCE=1`만 | `HERMES_LOOP_BUDGET_KILL=1` · cap 초과 시 `budget_blocking: true`면 FAIL, `false`면 WARN |
| M2 LLM humanize | `HERMES_HUMANIZE_LLM=1` 수동 | cron 미포함 (`cron_llm_humanize: false`) · `HERMES_ENHANCE`와 별도 경로 |
| Wiki LLM Ingest | `HERMES_WIKI_INGEST=1` | 비동기·옵션 |

참조: `config/harness.yaml` `guardrails.deny_paths`, `require_notion_sync_telegram`

---

## 상태 · Run log

| 파일 | 역할 |
|------|------|
| `.harness/progress.md` | 세션·기능 진행 SoT |
| `.harness/feature_list.json` | 단일 활성 기능 스코프 |
| `.harness/content-loop-runs.jsonl` | triage·supervised 등 루프 실행 1줄 JSON |
| `.harness/traces/` | intent 타이밍 |
| `.harness/cost-ledger.jsonl` | LLM 비용 (결정적 파이프라인 = 0 token) |
| `content/logs/{date}_daily-triage.md` | 당일 triage 전문 |
| `content/logs/{date}_supervised-pipeline.md` | supervised 파이프라인 로그 |
| `content/logs/{date}_studio-resources-spec.md` | 운영 리소스·기술 스펙 (Notion export 입력) |
| `content/logs/{date}_studio-dependency-diagrams.md` | 의존성 다이어그램 |
| `content/logs/{date}_cursor-agent-resources.md` | Cursor Agent 리소스 맵 |
| `content/.notion-architecture-state.json` | Notion 아키텍처 페이지 id/url |

`STATE.md` / `LOOP.md` 별도 파일은 **만들지 않음** — 위 경로에 흡수.

---

## Budget · Kill switch

LLM 경로 cap — SoT: `config/content-quality.yaml` `budget` 섹션

| 항목 | 값 | 설명 |
|------|-----|------|
| `daily_token_cap` | 600000 | 일 합산 (Codex humanize LIVE ~275k/채널) |
| `path_daily_token_caps.HERMES_HUMANIZE_LLM` | 400000 | humanize 경로 단독 상한 |
| `daily_usd_cap` | 2.0 | USD 상한 |
| `warn_threshold_pct` | 80 | cap 80% 이상 시 status 경고 |

| 변수 | 기본 | 설명 |
|------|------|------|
| `HERMES_LOOP_BUDGET_KILL` | `0` | `1`이면 LLM 경로 즉시 차단 |
| `HERMES_CRON_HUMANIZE` | `1` (yaml) | supervised cron 결정적 humanize |
| `HERMES_HUMANIZE_LLM` | `0` | LLM 2차 humanize-korean |
| `HERMES_HUMANIZE_LLM_CHANNELS` | `blog,linkedin,instagram` | LLM polish 대상 |
| `HERMES_HUMANIZE_LLM_TIMEOUT` | _(yaml)_ | 전역 override — 기본 `humanize_llm.default_timeout_sec` |
| `HERMES_HUMANIZE_LLM_TIMEOUT_LINKEDIN` | `120` | 채널별 override (yaml `humanize_llm.channel_timeouts`) |
| `HERMES_USE_CODEX` | `1` (LLM humanize) | Codex 경로 — Ollama 대비 ~100s linkedin |
| `HERMES_MCP_DISCOVER_ALL` | `0` | `1`이면 Notion archive 시 전체 MCP |
| `HERMES_MCP_SERVERS` | _(notion)_ | Notion MCP allowlist |
| `HERMES_SUPERVISED_STAGING` | `0` | `1`이면 staging `*_blocking` 적용 |
| `HERMES_NATURALNESS_BLOCKING` | `0` | `1`이면 naturalness FAIL → blocked |
| `HERMES_HUMANIZE_LLM_LIVE` | `0` | humanize-llm-eval LIVE 모드 |
| `HERMES_M5_E2E_LIVE` | `0` | m5-notion-eval archive --force |
| `HERMES_PLAYMCP_E2E_LIVE` | `0` | playmcp-routing-e2e LIVE (OTT 필요) |

```bash
# 자연스러움 eval
~/hermes-content-studio/scripts/naturalness-eval.sh
# Loop budget kill · cap E2E
~/hermes-content-studio/scripts/loop-budget-eval.sh
# 오늘 ledger vs cap (read-only)
~/hermes-content-studio/scripts/loop-budget-status.sh
# Studio 아키텍처 → Notion
~/hermes-content-studio/scripts/export-architecture-notion.sh
```

---

## 단계적 자율화 (로드맵)

| 주차 | 액션 | Level |
|------|------|-------|
| 1 | daily-content-triage + 본 문서 | L1 |
| 2 | supervised-pipeline cron | L2 ✅ |
| 3 | post-pipeline audit gate | L2 |
| 4 | M4 coach weekly + budget | L2 |

---

## 검증

```bash
# Hermes 품질 게이트 (필수)
~/hermes-content-studio/scripts/agents-eval.sh
~/hermes-content-studio/scripts/validate-output.sh research content/research/YYYY-MM-DD_brief.md
~/hermes-content-studio/scripts/voice-style-eval.sh
~/hermes-content-studio/scripts/content-loop-eval.sh

# Loop readiness (콘텐츠 공장 rubric — 권장 ≥70)
~/hermes-content-studio/scripts/content-loop-eval.sh
```

---

## 참고

- [Loop Engineering](https://github.com/cobusgreyling/loop-engineering) — 패턴·체크리스트
- `HARNESS.md` — Harness 5-subsystem
- `docs/LLM-WIKI-INTEGRATION.md` — 이중 메모리·결정적 공장 유지
