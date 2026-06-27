# Session Handoff

생성: 2026-06-10 01:53 UTC · session `phase2-eval`

## 마지막 Agent 세션

- **날짜(stamp):** 2026-06-09
- **Intent:** linkedin
- **Action:** linkedin_m3_pipeline
- **대기:** notion_sync

## 이어하기 (Resume)

```bash
cd ~/hermes-content-studio
./scripts/init.sh --skip-health
./scripts/archive-to-notion.sh 2026-06-09 --force
./scripts/hermes-agent.sh publish linkedin
```

## M4 Performance (최근 7일)

```
📊 M4 Performance · 최근 7일

트레이스: 102건

| Stage | n | avg | SLA | breach |
|-------|---|-----|-----|--------|
| agent_approve | 1 | 14.48s | —s | 1 |
| agent_graph | 6 | 0.01s | —s | 0 |
| agent_handoff | 5 | 0.1s | —s | 0 |
| agent_linkedin | 6 | 0.02s | —s | 0 |
| agent_morning | 33 | 0.0s | —s | 0 |
| agent_newsletter | 1 | 0.01s | —s | 0 |
| agent_publish | 4 | 0.0s | —s | 0 |
| agent_traces | 6 | 0.19s | —s | 0 |
| full_pipeline | 23 | 21.83s | 70s | 0 |
| linkedin_m3 | 6 | 0.01s | 15s | 0 |
| newsletter | 11 | 0.36s | 10s | 0 |

Notion tier: canonical 33 · draft 2 (5.7%)

✅ SLA 회귀 없음
```

## Phase 2 체크

- [ ] LinkedIn M3: `hermes-agent.sh linkedin`
- [ ] M4 리포트: `hermes-agent.sh traces`
- [ ] handoff 갱신: `hermes-agent.sh handoff`

## 검증

```bash
./scripts/phase2-eval.sh
./scripts/harness-eval.sh --quick
```