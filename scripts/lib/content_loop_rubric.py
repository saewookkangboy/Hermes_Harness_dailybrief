"""Content Loop Engineering rubric — 콘텐츠 공장 맞춤 (loop-audit 대체)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from lib.content_quality_config import load_content_quality_config

WORKDIR = Path.home() / "hermes-content-studio"


@dataclass
class RubricItem:
    category: str
    name: str
    points: int
    max_points: int
    detail: str = ""


@dataclass
class LoopRubricReport:
    score: int = 0
    max_score: int = 100
    target: int = 70
    items: list[RubricItem] = field(default_factory=list)
    level: str = "L0"

    @property
    def passed(self) -> bool:
        return self.score >= self.target


def _exists(path: str, name: str, pts: int, cat: str) -> RubricItem:
    p = WORKDIR / path
    ok = p.exists()
    return RubricItem(cat, name, pts if ok else 0, pts, "OK" if ok else f"missing: {path}")


def run_content_loop_rubric() -> LoopRubricReport:
    cfg = load_content_quality_config()
    target = int((cfg.get("eval") or {}).get("content_loop_target_score", 70))
    report = LoopRubricReport(target=target)

    checks: list[tuple[str, str, int, str]] = [
        # Harness SoT (20)
        ("AGENTS.md", "instructions_agents", 5, "harness"),
        ("HARNESS.md", "instructions_harness", 5, "harness"),
        (".harness/feature_list.json", "state_feature_list", 5, "harness"),
        (".harness/progress.md", "state_progress", 5, "harness"),
        # Content Loop (25)
        ("docs/content-loops.md", "loop_doc", 8, "loop"),
        ("scripts/cron-daily-content-triage.sh", "loop_l1_triage", 6, "loop"),
        ("scripts/cron-supervised-pipeline.sh", "loop_l2_supervised", 6, "loop"),
        (".harness/content-loop-runs.jsonl", "loop_run_log", 5, "loop"),
        # Verification (25)
        ("scripts/validate-output.sh", "verify_validate", 6, "verify"),
        ("scripts/voice-style-eval.sh", "verify_voice_eval", 6, "verify"),
        ("scripts/agents-eval.sh", "verify_agents_eval", 6, "verify"),
        ("scripts/naturalness-eval.sh", "verify_naturalness_eval", 5, "verify"),
        ("config/content-quality.yaml", "verify_quality_sot", 2, "verify"),
        # Human Gate (15)
        ("scripts/lib/publish_scheduler.py", "human_hitl_scheduler", 8, "human"),
        ("docs/content-loops.md", "human_gate_doc", 7, "human"),
        # Observability (15)
        (".harness/handoffs", "obs_handoffs_dir", 5, "obs"),
        (".harness/traces", "obs_traces_dir", 5, "obs"),
        ("scripts/lib/pipeline_supervisor.py", "obs_supervisor", 5, "obs"),
    ]

    seen: set[str] = set()
    for path, name, pts, cat in checks:
        if name in seen:
            continue
        seen.add(name)
        item = _exists(path, name, pts, cat)
        report.items.append(item)
        report.score += item.points

    report.max_score = sum(i.max_points for i in report.items)

    # L2 bonus: VOICE stage in supervisor
    sup = (WORKDIR / "scripts/lib/pipeline_supervisor.py").read_text(encoding="utf-8")
    if 'StageResult("VOICE"' in sup:
        report.items.append(RubricItem("loop", "voice_stage_supervised", 5, 5, "VOICE stage"))
        report.score += 5
        report.max_score += 5
    if 'StageResult("HUMANIZE"' in sup:
        report.items.append(RubricItem("loop", "humanize_stage_supervised", 5, 5, "HUMANIZE stage"))
        report.score += 5
        report.max_score += 5
    if 'StageResult("NATURALNESS"' in sup:
        report.items.append(RubricItem("loop", "naturalness_stage_supervised", 5, 5, "NATURALNESS stage"))
        report.score += 5
        report.max_score += 5

    if report.score >= 90:
        report.level = "L3"
    elif report.score >= target:
        report.level = "L2"
    elif report.score >= 50:
        report.level = "L1"
    else:
        report.level = "L0"

    return report


def format_rubric_report(report: LoopRubricReport) -> str:
    lines = [
        f"# Content Loop Rubric — {report.score}/{report.max_score} ({report.level})",
        "",
        f"Target: **{report.target}+** · {'✅ PASS' if report.passed else '⚠️ BELOW TARGET'}",
        "",
        "| Category | Check | Score |",
        "|----------|-------|-------|",
    ]
    for item in report.items:
        sym = "✅" if item.points == item.max_points else "❌"
        lines.append(f"| {item.category} | {sym} {item.name} | {item.points}/{item.max_points} |")
    lines.append("")
    return "\n".join(lines)


def write_rubric_report(stamp: str) -> Path:
    report = run_content_loop_rubric()
    out = WORKDIR / "content" / "logs" / f"{stamp}_content-loop-rubric.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(format_rubric_report(report), encoding="utf-8")
    state = WORKDIR / ".harness" / "content-loop-rubric.json"
    state.write_text(
        json.dumps(
            {
                "stamp": stamp,
                "score": report.score,
                "max_score": report.max_score,
                "level": report.level,
                "target": report.target,
                "passed": report.passed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out
