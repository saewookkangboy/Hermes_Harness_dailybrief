# Session Handoff — 2026-07-26

## 완료
- Harness v1.3.0: F1 token gates · F2 wiki graph · F3 ask graph-context · F4 playbook loop (infra)
- Architecture docs **v2.1**: `docs/architecture/SYSTEM-LOGIC.md` + `archive/v2.1-graph-token-playbook.md`
- Full System Retest **PASS** · perf P1–P3 (content 2s · graph incr ~260ms · ask −82%)
- 핸드오프: `content/drafts/cursor-handoff/HANDOFF-00`~`04`

## 남은 수동 작업
1. `./scripts/reflect.sh --week` (클라우드 키) 후 `--promote` 검토
2. `content/wiki/ask-eval-baseline.md` 품질 수동 판정
3. Notion 아키텍처 재동기화: `./scripts/export-architecture-notion.sh`

## 롤백
- `HERMES_WIKI_GRAPH=0` · `HERMES_ASK_GRAPH=0` · `HERMES_PLAYBOOK=stable`

## 이어하기
```bash
cd ~/hermes-content-studio
./scripts/init.sh --skip-health
cat docs/architecture/SYSTEM-LOGIC.md
./scripts/curate-playbook.sh --dry-run
```
