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
