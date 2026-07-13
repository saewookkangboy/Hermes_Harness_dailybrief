# Hermes Content Studio — Harness Engineering

> [awesome-harness-engineering](https://github.com/walkinglabs/awesome-harness-engineering) 기반 성능·신뢰성 하네스

## 5-Subsystem 모델

| 서브시스템 | 아티팩트 | 역할 |
|-----------|---------|------|
| Instructions | `AGENTS.md`, `HARNESS.md` | 시작 경로, 규칙, 완료 정의 |
| State | `.harness/feature_list.json`, `.harness/progress.md` | 진행·범위·다음 단계 |
| Verification | `scripts/init.sh`, `scripts/validate-output.sh`, `scripts/harness-eval.sh` | 완료 전 필수 검증 |
| Scope | `feature_list.json` 단일 활성 기능 | 과잉 작업 방지 |
| Lifecycle | `init.sh` → 작업 → `session-handoff.md` | 세션 재개 |

## 세션 시작 (필수)

```bash
cd ~/hermes-content-studio
./scripts/init.sh
cat .harness/progress.md
```

## 성능 고도화 원칙

### 1. 결정적 파이프라인 우선 (Control)

LLM 호출 없이 `assemble-*.py`로 산출물 생성 (~25초).
`HERMES_ENHANCE=1`일 때만 Hermes polish (2-5분).

```bash
./scripts/run-pipeline.sh          # 결정적 전체 M1+M2+M2b (~70s)
HERMES_ENHANCE=1 ./scripts/run-pipeline.sh  # LLM polish 추가
./scripts/run-newsletter.sh [DATE] --validate  # M2b 단독
./scripts/newsletter-eval.sh · newsletter-p2-eval.sh · newsletter-p3-eval.sh
```

### 2. 컨텍스트 백프레셔 (Agency)

- **사전 검색:** `gather-web-research.py` — 에이전트가 `web_search` 호출 생략
- **도구 마스킹:** 콘텐츠 스킬은 `-t hermes-cli`만 (MCP·브라우저 제외)
- **파일시스템 메모리:** `.harness/` + `content/research/_search_context_*.md`
- **이중 메모리 (선택):** 일별 `{date}_brief.md` SoT + 누적 `content/wiki/` — `docs/LLM-WIKI-INTEGRATION.md`
  - 결정적 Seed: `HERMES_WIKI_SEED=1 wiki-seed.sh` · LLM Ingest/Lint는 비동기만

### 3. 관측성 (Runtime)

- **트레이스:** `.harness/traces/trace-YYYYMMDD.jsonl`
- **비용 원장:** `.harness/cost-ledger.jsonl`
- **성능 eval:** `scripts/harness-eval.sh --record`

### 4. 가드레일

`config/harness.yaml` `guardrails.deny_paths`:
- `~/.hermes/.env`, `~/.ssh`, `**/.env`, credentials

Telegram 요청: Notion 100% 동기화 + Permalink 필수.

## Voice · Naturalness · Budget (P4–P14)

결정적 humanize는 cron 기본 ON (`HERMES_CRON_HUMANIZE=1`). LLM humanize는 수동만 (`cron_llm_humanize: false`).

### 프로덕션 blocking (2026-07-01~)

| 키 | yaml | 효과 |
|----|------|------|
| `voice_blocking` | `true` | VOICE FAIL → supervised blocked |
| `naturalness_blocking` | `true` | naturalness 점수 FAIL → blocked |
| `budget_blocking` | `false` | cap/kill 초과 → NATURALNESS **WARN** (FAIL 아님) |
| `humanize_blocking` | `false` | HUMANIZE FAIL → WARN |

`HERMES_SUPERVISED_STAGING=1` → `supervised.staging.*_blocking` 우선. 주간 `cron-staging-supervised` 토 11:00.

### Env

| 변수 | 기본 | 역할 |
|------|------|------|
| `HERMES_CRON_HUMANIZE` | `1` | supervised 결정적 polish |
| `HERMES_HUMANIZE_LLM` | `0` | hermes-run humanize-korean (budget 연동) |
| `HERMES_USE_CODEX` | `1` (LLM 시) | Codex 경로 (~100s linkedin) |
| `HERMES_SUPERVISED_STAGING` | `0` | staging blocking 프로필 |
| `HERMES_NATURALNESS_BLOCKING` | `0` | env로 naturalness FAIL 강제 |
| `HERMES_LOOP_BUDGET_KILL` | `0` | LLM 경로 즉시 차단 |

### Budget cap (`config/content-quality.yaml` `budget`)

| 항목 | 값 | 근거 |
|------|-----|------|
| `daily_token_cap` | 600000 | Codex humanize LIVE ~275k/채널 × 2 + 여유 |
| `path_daily_token_caps.HERMES_HUMANIZE_LLM` | 400000 | humanize 경로 단독 상한 |
| `warn_threshold_pct` | 80 | `loop-budget-status.sh` 근접 경고 |
| `daily_usd_cap` | 2.0 | included 구독 시 ledger usd=0 가능 |

## 아키텍처 문서

| 문서 | 역할 |
|------|------|
| `docs/architecture/SYSTEM-LOGIC.md` | **v2.0** 현행 시스템 로직 + Mermaid |
| `docs/architecture/README.md` | 버전 타임라인 · archive 인덱스 |
| `docs/architecture/archive/` | v1.0–v2.0 구현 단계 동결 스냅샷 |

```bash
./scripts/generate-architecture-md.py
./scripts/export-architecture-notion.sh
./scripts/voice-style-eval.sh [DATE]
./scripts/naturalness-eval.sh [DATE]
./scripts/humanize-llm-eval.sh [DATE]
HERMES_HUMANIZE_LLM_LIVE=1 ./scripts/humanize-llm-eval.sh [DATE]
./scripts/loop-budget-eval.sh
./scripts/loop-budget-status.sh
./scripts/staging-supervised-eval.sh [DATE]
HERMES_M5_E2E_LIVE=1 ./scripts/m5-notion-eval.sh [DATE]
HERMES_PLAYMCP_E2E_LIVE=1 ./scripts/playmcp-routing-e2e.sh
HERMES_CRON_SKIP_NOTION=1 ./scripts/cron-supervised-pipeline.sh
```

Notion 아키텍처 (Daily Archive 루트 하위, state: `content/.notion-architecture-state.json`):
- [운영 리소스·기술 스펙](https://www.notion.so/379fb3b5e389810f9630cd8cbfed942b)
- [의존성 다이어그램](https://www.notion.so/379fb3b5e38981c2a947ec8af87330b4)
- [Cursor Agent 리소스 맵](https://www.notion.so/379fb3b5e38981a4ba83f2a9d3af9979)

비용 원장: `.harness/cost-ledger.jsonl` — `lib/hermes_cost.py`가 TUI·Codex verbose(`Token usage`/`ResponseUsage`/`estimated_cost_usd`)·`sessions.json`에서 tokens/USD 파싱 · **per-run delta** (`parse_run_usage`).

`HERMES_ENHANCE=1` (content-pipeline polish)와 `HERMES_HUMANIZE_LLM=1`은 별도 LLM 경로이며 동일 `budget` cap·`cost-ledger`를 공유한다.

## CAR 분해 (HarnessCard)

- **Control:** AGENTS.md, feature_list, validate-output, deny_paths
- **Agency:** deterministic_pipeline, tool_masking, context_backpressure
- **Runtime:** init.sh, traces, session_handoff, health_gates

## 검증 워크플로

```bash
# 구조만 (빠름)
./scripts/harness-eval.sh --quick

# 성능 벤치마크 + 회귀 검출
./scripts/harness-eval.sh --record

# 산출물 품질
./scripts/validate-output.sh research content/research/YYYY-MM-DD_brief.md
```

## SLA (초)

| 단계 | SLA | 기준선 |
|------|-----|--------|
| research | 30 | 20 |
| content | 10 | 5 |
| full_pipeline | 60 | 45 |
| claude-design | 300 | — |

설정: `config/harness.yaml`

## 참고 자료

- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [12 Factor Agents](https://www.humanlayer.dev/blog/12-factor-agents)
- [learn-harness-engineering](https://github.com/walkinglabs/learn-harness-engineering)
