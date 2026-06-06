# Session Handoff

## 마지막 세션 요약

- 날짜: 2026-06-06
- 활성 기능 ID: **없음** (pipe-006 passing)
- 완료: 에이전트 성능 eval + Telegram qc pipeline 30s 타임아웃 안정화

## 성능 기준선 (2026-06-06)

| 단계 | 측정 | baseline | SLA |
|------|------|----------|-----|
| research | 8s | 20s | 30s |
| content | 1s | 5s | 10s |
| full_pipeline | 9s | 45s | 60s |
| qc pipeline (Telegram) | 14s | — | 30s (command_timeout) |
| Notion sync-bg | ~22s | — | 120s |

## 안정화 변경

| 파일 | 변경 |
|------|------|
| `scripts/telegram-pipeline.sh` | `run_pipeline_qc()` — sync-bg로 30s 타임아웃 회피 |

## Telegram 사용법

```
/pipeline   리서치 + 콘텐츠 (~12s) + Notion sync-bg → Permalink Telegram
/research   브리프만
/content    소셜·블로그
/sync       Notion Permalink (동기)
/studio     상태
```

## 다음 세션

```bash
cd ~/hermes-content-studio
./scripts/init.sh
./scripts/harness-eval.sh --record
./scripts/e2e-smoke-test.sh --telegram
```

## 검증 증거

- `.harness/eval-results.json` — 2026-06-06T13:42:22Z
- `e2e-smoke-test.sh --telegram` — 11/11 PASS
- `telegram-pipeline.sh qc pipeline` — 14s (sync-bg)
