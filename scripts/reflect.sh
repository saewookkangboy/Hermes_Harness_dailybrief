#!/usr/bin/env bash
# 주간 Reflector. 신호 수집은 결정적, LLM은 1회만.
set -euo pipefail
STUDIO="${HERMES_STUDIO:-${HERMES_WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
cd "$STUDIO"

DAYS=7
SIGNALS_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --week)  DAYS=7;  shift ;;
    --month) DAYS=30; shift ;;
    --days)  DAYS="$2"; shift 2 ;;
    --signals-only) SIGNALS_ONLY=1; shift ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done

SIG=$(mktemp)
PYTHONPATH=scripts python3 -c "
import sys, json; sys.path.insert(0,'scripts')
from lib import reflect
print(json.dumps(reflect.collect($DAYS), ensure_ascii=False, indent=1))" > "$SIG"

echo "── 신호 수집 완료 ──"
PYTHONPATH=scripts python3 -c "
import json
d=json.load(open('$SIG'))
print(f\"  window          : {d['window']['from']} ~ {d['window']['to']}\")
print(f\"  validate 실패   : {len(d['gate_failures'])}\")
print(f\"  SLA 초과        : {len(d['sla_breaches'])}\")
print(f\"  CTOR 저성과     : {len(d['ctor']['low'])} / 고성과 {len(d['ctor']['high'])} (n={d['ctor']['n']})\")
print(f\"  검증 대기 엔트리: {len(d['pending_verification'])}\")"

if [[ "$SIGNALS_ONLY" == "1" ]]; then
  cp "$SIG" ".harness/signals-$(date +%Y%m%d).json"
  echo "신호만 저장: .harness/signals-$(date +%Y%m%d).json"
  exit 0
fi

PROMPT=$(mktemp)
PYTHONPATH=scripts python3 -c "
import sys, json; sys.path.insert(0,'scripts')
from lib import reflect
print(reflect.build_prompt(json.load(open('$SIG'))))" > "$PROMPT"

OUT=$(mktemp)
if [[ -n "${OPENROUTER_API_KEY:-}" ]] && command -v hermes >/dev/null 2>&1; then
  hermes -z "$(cat "$PROMPT")" -t hermes-cli --json > "$OUT" || true
else
  echo "⚠ OPENROUTER_API_KEY/hermes 없음 — 프롬프트만 출력합니다."
  echo "   결과를 .harness/deltas/delta-YYYYMMDD.json 에 저장하세요."
  echo "────────────────────────────────────────"
  cat "$PROMPT"
  exit 0
fi

PYTHONPATH=scripts python3 - "$OUT" <<'PY'
import json, re, sys
sys.path.insert(0, "scripts")
from lib import reflect

raw = open(sys.argv[1], encoding="utf-8").read()
raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
# hermes --json 래퍼일 수 있음
try:
    doc = json.loads(raw)
except json.JSONDecodeError:
    m = re.search(r"\{[\s\S]*\"deltas\"[\s\S]*\}", raw)
    if not m:
        raise
    doc = json.loads(m.group(0))

assert "deltas" in doc, "deltas 키 없음"
for d in doc["deltas"]:
    assert d["op"] in ("ADD", "BUMP", "DEPRECATE"), d
    assert re.fullmatch(r"L-\d{4}", d["id"]), d
    assert d.get("evidence"), f"evidence 없음: {d}"
    if d["op"] == "ADD":
        assert d.get("text") and d.get("expected"), f"ADD 필수 필드 누락: {d}"
        assert d["expected"].get("metric") and d["expected"].get("delta")
    if d["op"] == "BUMP":
        assert d.get("signal") in ("helpful", "harmful"), d

p = reflect.save(doc)
print(f"\n✓ delta {len(doc['deltas'])}건 저장: {p}")
for d in doc["deltas"]:
    print(f"  {d['op']:<10} {d['skill']:<24} {d['id']}  {d.get('text','')[:60]}")
PY

echo
echo "다음: ./scripts/curate-playbook.sh --dry-run"
