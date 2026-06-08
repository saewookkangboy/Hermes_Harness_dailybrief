# Session Handoff

생성: 2026-06-08 08:45 UTC · session `phase2-eval`

## 마지막 Agent 세션

- **날짜(stamp):** 2026-06-08
- **Intent:** linkedin
- **Action:** linkedin_m3_pipeline
- **대기:** notion_sync

## 이어하기 (Resume)

```bash
cd ~/hermes-content-studio
./scripts/init.sh --skip-health
./scripts/archive-to-notion.sh 2026-06-08 --force
./scripts/hermes-agent.sh publish linkedin
```

## M4 Performance (최근 7일)

```
📊 M4 Performance · 최근 7일

트레이스: 50건

| Stage | n | avg | SLA | breach |
|-------|---|-----|-----|--------|
| agent_approve | 1 | 14.48s | —s | 1 |
| agent_graph | 3 | 0.01s | —s | 0 |
| agent_handoff | 3 | 0.08s | —s | 0 |
| agent_linkedin | 4 | 0.02s | —s | 0 |
| agent_morning | 12 | 0.0s | —s | 0 |
| agent_publish | 3 | 0.0s | —s | 0 |
| agent_traces | 4 | 0.16s | —s | 0 |
| full_pipeline | 16 | 24.31s | 60s | 0 |
| linkedin_m3 | 4 | 0.01s | 15s | 0 |

Notion tier: canonical 21 · draft 1 (4.5%)

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