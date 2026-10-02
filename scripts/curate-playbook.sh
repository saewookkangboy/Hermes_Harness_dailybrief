#!/usr/bin/env bash
# Curator — dry-run / shadow / promote 3단계.
set -euo pipefail
STUDIO="${HERMES_STUDIO:-${HERMES_WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
cd "$STUDIO"

MODE="dry-run"
RUNS=5
DELTA=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) MODE="dry-run"; shift ;;
    --shadow)  MODE="shadow";  shift ;;
    --promote) MODE="promote"; shift ;;
    --verify)  MODE="verify";  shift ;;
    --runs)    RUNS="$2"; shift 2 ;;
    --delta)   DELTA="$2"; shift 2 ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done

DELTA="${DELTA:-$(ls -1t .harness/deltas/delta-*.json 2>/dev/null | head -1 || true)}"
[[ -n "$DELTA" ]] || { echo "delta 파일 없음. ./scripts/reflect.sh --week 먼저 실행" >&2; exit 1; }
echo "delta: $DELTA"

case "$MODE" in
  dry-run)
    PYTHONPATH=scripts python3 -c "
import sys; sys.path.insert(0,'scripts')
from pathlib import Path
from lib import curator
for m in curator.apply_doc(Path('$DELTA'), dry=True): print('  ', m)"
    echo
    echo "다음: ./scripts/curate-playbook.sh --shadow --runs $RUNS"
    ;;

  shadow)
    SHADOW=".harness/shadow/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$SHADOW"
    cp -R skills "$SHADOW/skills"

    HERMES_SKILLS_ROOT="$SHADOW/skills" PYTHONPATH=scripts python3 -c "
import sys; sys.path.insert(0,'scripts')
from pathlib import Path
from lib import curator
for m in curator.apply_doc(Path('$DELTA'), dry=False): print('  ', m)"

    echo "── shadow 검증 (발행 없음) ──"
    FAIL=0
    # 전체 파이프라인 N회는 비용이 크므로 구조·플레이북 무결성 + 토큰 게이트로 대체
    # HERMES_DRY_PUBLISH=1 이 있으면 파이프라인 시도
    if [[ "${HERMES_SHADOW_PIPELINE:-0}" == "1" ]]; then
      for i in $(seq 1 "$RUNS"); do
        HERMES_SKILLS_ROOT="$SHADOW/skills" \
        HERMES_DRY_PUBLISH=1 \
        RUN_ID="shadow-$i" \
          ./scripts/run-pipeline.sh > "$SHADOW/run-$i.log" 2>&1 \
          && echo "  run $i ✓" || { echo "  run $i ✗"; FAIL=1; }
      done
    else
      echo "  (HERMES_SHADOW_PIPELINE=0 — 파이프라인 스킵, 구조 검증만)"
      echo "  shadow skills 적용 완료: $SHADOW/skills"
    fi

    ./scripts/token-gate-eval.sh 1h || FAIL=1

    if [[ "${FAIL:-0}" == "1" ]]; then
      echo "✗ shadow 실패 — 승격하지 않습니다. 로그: $SHADOW/"
      exit 1
    fi
    echo "✓ shadow 통과: $SHADOW"
    echo "다음: ./scripts/curate-playbook.sh --promote"
    ;;

  promote)
    echo "── 승격 게이트 ──"
    ./scripts/harness-eval.sh --quick || { echo "✗ harness-eval 회귀"; exit 1; }
    ./scripts/token-gate-eval.sh 7d    || { echo "✗ 토큰 게이트"; exit 1; }

    PYTHONPATH=scripts python3 -c "
import json, sys; sys.path.insert(0,'scripts')
from pathlib import Path
from lib.token_budget import load_yaml_flat
cap = ((load_yaml_flat(Path('config/harness.yaml')).get('playbook') or {})
       .get('promotion_gate') or {}).get('max_token_increase_pct', 15)
p = Path('.harness/token-baseline.jsonl')
if not p.exists():
    print('  기준선 없음 — 건너뜀'); raise SystemExit(0)
lines = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
if len(lines) >= 2:
    def tot(s): return sum(v.get('tokens_in',0) for v in s.get('agg',{}).values())
    prev, cur = tot(lines[-2]), tot(lines[-1])
    inc = (cur - prev) / prev * 100 if prev else 0
    print(f'  토큰 증가율 {inc:+.1f}% (상한 {cap}%)')
    sys.exit(1 if inc > cap else 0)
print('  기준선 부족 — 건너뜀')" || { echo "✗ 토큰 증가율 초과"; exit 1; }

    PYTHONPATH=scripts python3 -c "
import sys; sys.path.insert(0,'scripts')
from pathlib import Path
from lib import curator
for m in curator.apply_doc(Path('$DELTA'), dry=False): print('  ', m)"

    echo "✓ 승격 완료. git commit 을 검토 후 직접 실행하세요."
    ;;

  verify)
    PYTHONPATH=scripts python3 -c "
import json, sys; sys.path.insert(0,'scripts')
from datetime import date
from lib import curator, reflect
cands = curator.verify_expectations(14)
if not cands:
    print('검증 대기 엔트리 없음'); raise SystemExit(0)
doc = {'generated_at': date.today().isoformat(),
       'window': {'from': '', 'to': date.today().isoformat()},
       'deltas': cands}
p = reflect.save(doc)
print(f'✓ 검증 delta {len(cands)}건: {p}')
for c in cands: print('  ', c['skill'], c['id'], c['rationale'])"
    ;;
esac
