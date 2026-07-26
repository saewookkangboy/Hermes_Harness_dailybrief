#!/usr/bin/env bash
# /ask 토큰·품질 비교 eval. --compare 는 legacy vs graph 양쪽 실행.
set -euo pipefail
STUDIO="${HERMES_STUDIO:-${HERMES_WORKDIR:-$HOME/hermes-content-studio}}"
cd "$STUDIO"

MODE="graph"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --compare) MODE="compare"; shift ;;
    --legacy)  MODE="legacy";  shift ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done

[[ -f content/wiki/graph.db ]] || {
  echo "graph.db 없음 — wiki-graph.sh --force --rebuild 먼저" >&2
  exit 1
}

python3 - "$MODE" <<'PY'
import json, sys, re
from pathlib import Path
sys.path.insert(0, "scripts")
from lib.skill_loader import estimate_tokens
from lib import graph_context

mode = sys.argv[1]
qs_raw = Path("config/ask-eval-questions.yaml").read_text(encoding="utf-8")
questions = re.findall(r'text:\s*"([^"]+)"', qs_raw)

def legacy_tokens(q: str) -> int:
    """레거시 index-first 근사: 키워드 매칭 브리프 상위 3개 전문 크기."""
    briefs = sorted(Path("content/research").glob("*_brief.md"))[-3:]
    return sum(estimate_tokens(b.read_text(encoding="utf-8")) for b in briefs)

rows, tot_g, tot_l = [], 0, 0
for q in questions:
    _, meta = graph_context.build(q, budget_tokens=3000, hops=2)
    g = meta["tokens"]
    l = legacy_tokens(q) if mode in ("compare", "legacy") else 0
    tot_g += g; tot_l += l
    rows.append((q[:40], meta["seeds"], meta["nodes"], g, l, meta["truncated"]))

print(f"\n{'question':<42}{'seed':>5}{'node':>6}{'graph':>8}{'legacy':>8}  trunc")
print("-" * 78)
for q, s, n, g, l, t in rows:
    print(f"{q:<42}{s:>5}{n:>6}{g:>8}{l:>8}  {'!' if t else ''}")
print("-" * 78)
print(f"{'TOTAL':<42}{'':>5}{'':>6}{tot_g:>8}{tot_l:>8}")

if mode == "compare" and tot_l:
    cut = (1 - tot_g / tot_l) * 100
    print(f"\n토큰 감소율: {cut:.1f}%  (목표 40% 이상)")
    zero_seed = sum(1 for r in rows if r[1] == 0)
    print(f"시드 0건 질문: {zero_seed}/{len(rows)}  (목표 3건 이하)")
    ok = cut >= 40 and zero_seed <= 3
    print("✓ PASS" if ok else "✗ FAIL (시드/토큰 목표 미달)")
    raise SystemExit(0 if ok else 1)
elif mode == "compare":
    print("(legacy 토큰 0 — 브리프 없음)")
    raise SystemExit(0)
PY
