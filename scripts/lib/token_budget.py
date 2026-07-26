"""단계별 토큰 예산 판정. harness.yaml sla.*.tokens_* 기준."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import ledger

CONFIG = ledger.STUDIO / "config" / "harness.yaml"


def load_yaml_flat(path: Path) -> dict:
    """최소 YAML 로더 (pyyaml 의존 회피). 2-space · 스칼라 전제."""
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if line.startswith("- "):
            parent = stack[-1][1]
            parent.setdefault("_list", []).append(_coerce(line[2:]))
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if val == "" or val.startswith("&") or val.startswith("*"):
            # 앵커/빈 값은 자식 노드로 취급
            if val.startswith("&") or val.startswith("*") or val == "":
                node: dict = {}
                parent[key] = node
                stack.append((indent, node))
            continue
        # 인라인 리스트 [a, b] 는 문자열로 보존
        parent[key] = _coerce(val)
        if isinstance(parent[key], dict):
            stack.append((indent, parent[key]))
    return root


def _coerce(v: str):
    v = v.strip().strip('"').strip("'")
    if v in ("null", "~", ""):
        return None
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


class Violation(dict):
    pass


def check(since: str = "7d") -> tuple[list[Violation], dict]:
    cfg = load_yaml_flat(CONFIG)
    sla = cfg.get("sla", {}) or {}
    gate = cfg.get("token_gate", {}) or {}
    tol = (gate.get("tolerance_pct") or 15) / 100.0
    strict = bool(gate.get("deterministic_strict", True))

    agg = ledger.aggregate(since)
    violations: list[Violation] = []

    for stage, spec in sla.items():
        if not isinstance(spec, dict):
            continue
        actual = agg.get(stage)
        if not actual:
            continue

        det = bool(spec.get("deterministic"))
        for axis in ("tokens_in", "tokens_out"):
            budget = spec.get(axis)
            if budget is None:
                continue
            observed = actual["avg_in"] if axis == "tokens_in" else actual["avg_out"]

            if det and strict and budget == 0 and observed > 0:
                violations.append(
                    Violation(
                        stage=stage,
                        axis=axis,
                        budget=0,
                        observed=observed,
                        severity="critical",
                        reason="결정적 단계에 LLM 호출이 누출됨",
                    )
                )
                continue

            limit = budget * (1 + tol)
            if observed > limit:
                violations.append(
                    Violation(
                        stage=stage,
                        axis=axis,
                        budget=budget,
                        observed=observed,
                        severity="warn",
                        reason=f"예산 {budget} + 허용 {int(tol * 100)}% 초과",
                    )
                )
    return violations, agg


def main() -> int:
    since = sys.argv[1] if len(sys.argv) > 1 else "7d"
    cfg = load_yaml_flat(CONFIG)
    mode = (cfg.get("token_gate", {}) or {}).get("mode", "warn")
    violations, _ = check(since)

    if not violations:
        print(f"✓ token gate PASS (since={since})")
        return 0

    for v in violations:
        icon = "✗" if v["severity"] == "critical" else "⚠"
        print(
            f"{icon} {v['stage']}.{v['axis']}: "
            f"observed={v['observed']} budget={v['budget']} — {v['reason']}"
        )

    has_critical = any(v["severity"] == "critical" for v in violations)
    if has_critical or mode == "fail":
        return 1
    print("(mode=warn — 실패로 처리하지 않음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
