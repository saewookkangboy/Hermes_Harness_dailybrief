"""Topic Pack 품질 게이트 — relevance · coverage · diversity · blueprint · future · channel."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from lib.ax.config import load_config
from lib.ax.evidence import EvidencePack


@dataclass
class GateResult:
    name: str
    passed: bool
    blocking: bool
    detail: str
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        if self.passed:
            return "WARN" if self.warnings else "PASS"
        return "FAIL" if self.blocking else "WARN"


@dataclass
class GateReport:
    results: list[GateResult] = field(default_factory=list)

    def add(self, result: GateResult) -> GateResult:
        self.results = [r for r in self.results if r.name != result.name] + [result]
        return result

    @property
    def passed(self) -> bool:
        return all(r.passed or not r.blocking for r in self.results)

    def failures(self) -> list[GateResult]:
        return [r for r in self.results if not r.passed and r.blocking]

    def summary(self) -> str:
        return " · ".join(f"{r.name}={r.status}" for r in self.results)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "passed": self.passed,
            "summary": self.summary(),
            "results": [dict(asdict(r), status=r.status) for r in self.results],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _gcfg(name: str, cfg: dict[str, Any] | None) -> dict[str, Any]:
    return ((cfg or load_config()).get("gates") or {}).get(name) or {}


def relevance_gate(pack: EvidencePack, cfg: dict[str, Any] | None = None) -> GateResult:
    g = _gcfg("relevance", cfg)
    min_rel = int(g.get("min_relevant", 8))
    warn_ratio = float(g.get("raw_ratio_warn", 0.35))
    passed = pack.relevant_count >= min_rel
    warnings = []
    if pack.raw_count and pack.raw_ratio < warn_ratio:
        warnings.append(f"쿼리 드리프트 의심: 관련 비율 {pack.raw_ratio:.0%} < {warn_ratio:.0%}")
    return GateResult(
        "relevance",
        passed,
        bool(g.get("blocking", True)),
        f"관련 근거 {pack.relevant_count}/{pack.raw_count}건 (최소 {min_rel})",
        warnings,
        {"relevant": pack.relevant_count, "raw": pack.raw_count, "ratio": pack.raw_ratio},
    )


def coverage_gate(pack: EvidencePack, cfg: dict[str, Any] | None = None) -> GateResult:
    g = _gcfg("coverage", cfg)
    counts = pack.lens_counts()
    covered = sorted(k for k, v in counts.items() if v > 0)
    total = len((cfg or load_config()).get("lenses") or {})
    min_l, target = int(g.get("min_lenses", 4)), int(g.get("target_lenses", 5))
    warnings = [f"렌즈 커버리지 {len(covered)} < 목표 {target}"] if min_l <= len(covered) < target else []
    return GateResult(
        "coverage",
        len(covered) >= min_l,
        bool(g.get("blocking", True)),
        f"렌즈 {len(covered)}/{total} 커버 (최소 {min_l})",
        warnings,
        {"covered": covered, "lens_counts": counts},
    )


def diversity_gate(pack: EvidencePack, cfg: dict[str, Any] | None = None) -> GateResult:
    g = _gcfg("diversity", cfg)
    types = pack.source_type_counts()
    domains = len(pack.domains())
    min_t, target_t, min_d = int(g.get("min_source_types", 2)), int(g.get("target_source_types", 3)), int(g.get("min_domains", 5))
    passed = len(types) >= min_t and domains >= min_d
    warnings = [f"소스 유형 {len(types)} < 목표 {target_t}"] if passed and len(types) < target_t else []
    return GateResult(
        "diversity",
        passed,
        bool(g.get("blocking", True)),
        f"소스 유형 {len(types)}종 · 도메인 {domains}개 (최소 {min_t}종·{min_d}개)",
        warnings,
        {"source_types": types, "domains": domains},
    )


def blueprint_gate(blueprint: dict[str, Any], cfg: dict[str, Any] | None = None) -> GateResult:
    g = _gcfg("blueprint", cfg)
    opps = blueprint.get("opportunities") or []
    incomplete = [o.get("stage", "?") for o in opps if not (o.get("kpi") and o.get("hitl") and o.get("risk"))]
    min_o = int(g.get("min_opportunities", 4))
    passed = len(opps) >= min_o and not incomplete
    detail = f"자동화 기회 {len(opps)}개 (최소 {min_o})"
    if incomplete:
        detail += f" · KPI/HITL/리스크 누락: {', '.join(incomplete)}"
    return GateResult("blueprint", passed, bool(g.get("blocking", True)), detail, [], {"opportunities": len(opps)})


def future_gate(future: dict[str, Any], cfg: dict[str, Any] | None = None) -> GateResult:
    g = _gcfg("future", cfg)
    need = int(g.get("min_signals_per_prediction", 2))
    preds = future.get("predictions") or []
    weak = [p.get("horizon", "?") for p in preds if len(p.get("signals") or []) < need or not p.get("confidence")]
    passed = len(preds) >= 2 and not weak and len(future.get("actions") or []) >= 3
    detail = f"예측 {len(preds)}개 · 액션 {len(future.get('actions') or [])}개 (예측당 신호 ≥{need})"
    if weak:
        detail += f" · 근거 부족: {', '.join(weak)}"
    return GateResult("future", passed, bool(g.get("blocking", True)), detail, [], {"predictions": len(preds)})


def channel_gate(scores: dict[str, dict[str, Any]], cfg: dict[str, Any] | None = None) -> GateResult:
    g = _gcfg("channel", cfg)
    failed = [f"{ch}({s['score']}<{s['min']})" for ch, s in scores.items() if not s["passed"]]
    detail = " · ".join(f"{ch} {s['score']}" for ch, s in scores.items())
    if failed:
        detail += f" · 미달: {', '.join(failed)}"
    return GateResult("channel", not failed, bool(g.get("blocking", True)), detail, [], {"scores": scores})


def research_gates(pack: EvidencePack, report: GateReport, cfg: dict[str, Any] | None = None) -> GateReport:
    for fn in (relevance_gate, coverage_gate, diversity_gate):
        report.add(fn(pack, cfg))
    return report
