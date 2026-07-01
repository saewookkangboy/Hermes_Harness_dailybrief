"""Pipeline Supervisor Agent — M1→M2→(M2b)→Audit→M5 단계별 감독 (결정적)."""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from lib.brief_gate import assert_brief_ready_for_content, brief_path
from lib.common import studio_today
from lib.harness import timed_stage
from lib.quality_auditor import audit_stamp, glob_linkedin_feed
from lib.naturalness_audit import naturalness_issues_for_stamp
from lib.voice_style_audit import run_voice_audit_stamp
from lib.content_quality_config import supervised_stage_blocking
from lib.loop_budget import check_loop_budget

WORKDIR = Path.home() / "hermes-content-studio"
SCRIPTS = WORKDIR / "scripts"
HANDOFF_DIR = WORKDIR / ".harness" / "handoffs"
LOGS_DIR = WORKDIR / "content" / "logs"


@dataclass
class StageResult:
    stage_id: str
    label: str
    status: str  # PASS | FAIL | SKIP
    elapsed_seconds: float = 0.0
    detail: str = ""


@dataclass
class SupervisorReport:
    stamp: str
    stages: list[StageResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    blocked_at: str = ""

    @property
    def success(self) -> bool:
        if self.blocked_at:
            return False
        return not any(s.status == "FAIL" for s in self.stages)

    @property
    def has_warnings(self) -> bool:
        return any(s.status == "WARN" for s in self.stages)


def _run_script(args: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str]:
    import os

    merged = {**os.environ, **(env or {})}
    proc = subprocess.run(
        args,
        cwd=str(WORKDIR),
        capture_output=True,
        text=True,
        env=merged,
        check=False,
    )
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return int(proc.returncode or 0), out[-500:] if len(out) > 500 else out


def _validate_channel(vtype: str, pattern: str) -> tuple[bool, str]:
    matches = sorted(WORKDIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        return False, f"산출물 없음: {pattern}"
    path = matches[0]
    rc, out = _run_script([str(SCRIPTS / "validate-output.sh"), vtype, str(path)])
    return rc == 0, out.splitlines()[-1] if out else ("OK" if rc == 0 else "FAIL")


NotifyFn = Callable[[str], None]


def _quality_stage_status(*, has_issues: bool, blocking: bool) -> str:
    if not has_issues:
        return "PASS"
    return "FAIL" if blocking else "WARN"


def _finish(report: SupervisorReport, t0: float) -> SupervisorReport:
    report.elapsed_seconds = round(time.perf_counter() - t0, 2)
    _write_handoff(report)
    return report


def run_supervised_pipeline(
    stamp: str,
    *,
    skip_newsletter: bool = False,
    skip_notion: bool = False,
    skip_audit: bool = False,
    notify: NotifyFn | None = None,
) -> SupervisorReport:
    """M1 research → brief_gate → M2 → M2b → audit → voice → humanize? → M5."""
    t0 = time.perf_counter()
    report = SupervisorReport(stamp=stamp)
    enable_humanize = os.environ.get("HERMES_HUMANIZE", "0") == "1"
    total_steps = (5 if not skip_newsletter else 4) + (1 if not skip_audit else 0)
    if enable_humanize and not skip_audit:
        total_steps += 1
    if not skip_audit:
        total_steps += 1  # NATURALNESS
    step = 0

    def _progress(msg: str) -> None:
        if notify:
            notify(msg)

    # M1
    step += 1
    _progress(f"[█░░░░] {step}/{total_steps} M1 리서치 브리프…")
    with timed_stage("supervised_m1"):
        t1 = time.perf_counter()
        rc, detail = _run_script([str(SCRIPTS / "run-research-brief.sh"), stamp], env={"SKIP_INIT": "1"})
        elapsed = round(time.perf_counter() - t1, 2)
    st = "PASS" if rc == 0 and brief_path(stamp).exists() else "FAIL"
    report.stages.append(StageResult("M1", "research", st, elapsed, detail))
    if st == "FAIL":
        report.blocked_at = "M1"
        return _finish(report, t0)

    # brief gate
    try:
        assert_brief_ready_for_content(stamp)
        gate_detail = "Brief SoT Top 7 OK"
        gate_status = "PASS"
    except SystemExit as e:
        gate_detail = str(e)
        gate_status = "FAIL"
    report.stages.append(StageResult("GATE", "brief_gate", gate_status, 0.0, gate_detail))
    if gate_status == "FAIL":
        report.blocked_at = "GATE"
        return _finish(report, t0)

    # M2
    step += 1
    _progress(f"[██░░░] {step}/{total_steps} M2 콘텐츠 패키지…")
    with timed_stage("supervised_m2"):
        t1 = time.perf_counter()
        rc, detail = _run_script(
            [str(SCRIPTS / "run-content-package.sh"), stamp],
            env={"SKIP_INIT": "1", "HERMES_SKIP_RESEARCH": "1"},
        )
        elapsed = round(time.perf_counter() - t1, 2)
    blog_ok, blog_msg = _validate_channel("blog", f"content/blog/{stamp}_blog_*.html")
    ig_ok, ig_msg = _validate_channel("instagram", f"content/instagram/{stamp}_instagram_*.md")
    li_feed = glob_linkedin_feed(stamp)
    if li_feed:
        li_ok, li_msg = _validate_channel("linkedin", str(li_feed.relative_to(WORKDIR)))
    else:
        li_ok, li_msg = _validate_channel("linkedin", f"content/linkedin/{stamp}_linkedin_*.md")
    m2_ok = rc == 0 and blog_ok and ig_ok and li_ok
    report.stages.append(
        StageResult(
            "M2",
            "content",
            "PASS" if m2_ok else "FAIL",
            elapsed,
            f"blog={blog_msg}; ig={ig_msg}; li={li_msg}",
        )
    )
    if not m2_ok:
        report.blocked_at = "M2"
        return _finish(report, t0)

    # M2b newsletter
    if not skip_newsletter:
        step += 1
        _progress(f"[███░░] {step}/{total_steps} M2b 뉴스레터…")
        with timed_stage("supervised_m2b"):
            t1 = time.perf_counter()
            rc, detail = _run_script(
                [str(SCRIPTS / "run-newsletter.sh"), stamp, "--validate"],
                env={"SKIP_INIT": "1"},
            )
            elapsed = round(time.perf_counter() - t1, 2)
        nl_ok, nl_msg = _validate_channel("newsletter", f"content/newsletter/{stamp}_newsletter_*.md")
        st = "PASS" if rc == 0 and nl_ok else "FAIL"
        report.stages.append(StageResult("M2b", "newsletter", st, elapsed, nl_msg or detail))
        if st == "FAIL":
            report.blocked_at = "M2b"
            return _finish(report, t0)
    else:
        report.stages.append(StageResult("M2b", "newsletter", "SKIP", 0.0, "SKIP_NEWSLETTER=1"))

    # Audit
    if not skip_audit:
        step += 1
        _progress(f"[████░] {step}/{total_steps} Quality Audit…")
        t1 = time.perf_counter()
        audit = audit_stamp(stamp, write_report=True)
        elapsed = round(time.perf_counter() - t1, 2)
        st = "PASS" if audit.all_pass else "WARN"
        report.stages.append(
            StageResult(
                "AUDIT",
                "quality_audit",
                st,
                elapsed,
                f"PASS={audit.pass_count} FAIL={audit.fail_count}",
            )
        )
        # Audit WARN는 차단하지 않음 — DoD 참고만

        # Voice style (non-blocking WARN)
        step += 1
        _progress(f"[████░] {step}/{total_steps} Voice Style…")
        t1 = time.perf_counter()
        voice_issues = run_voice_audit_stamp(stamp)
        elapsed = round(time.perf_counter() - t1, 2)
        voice_blocking = supervised_stage_blocking("voice")
        voice_st = _quality_stage_status(has_issues=bool(voice_issues), blocking=voice_blocking)
        voice_detail = "; ".join(voice_issues[:3]) if voice_issues else "OK"
        report.stages.append(
            StageResult("VOICE", "voice_style", voice_st, elapsed, voice_detail)
        )
        if voice_st == "FAIL":
            report.blocked_at = "VOICE"
            return _finish(report, t0)

        if enable_humanize:
            step += 1
            _progress(f"[████░] {step}/{total_steps} Humanize Polish…")
            t1 = time.perf_counter()
            rc, detail = _run_script(
                [str(SCRIPTS / "run-humanize-polish.sh"), stamp],
                env={"HERMES_HUMANIZE": "1", "HERMES_HUMANIZE_LLM": os.environ.get("HERMES_HUMANIZE_LLM", "0")},
            )
            elapsed = round(time.perf_counter() - t1, 2)
            hum_fail = rc != 0
            hum_blocking = supervised_stage_blocking("humanize")
            hum_st = _quality_stage_status(has_issues=hum_fail, blocking=hum_blocking)
            report.stages.append(
                StageResult("HUMANIZE", "humanize_polish", hum_st, elapsed, detail[:120] or "OK")
            )
            if hum_st == "FAIL":
                report.blocked_at = "HUMANIZE"
                return _finish(report, t0)

        # Naturalness (+ optional budget gate)
        step += 1
        _progress(f"[████░] {step}/{total_steps} Naturalness…")
        t1 = time.perf_counter()
        nat_issues = naturalness_issues_for_stamp(stamp)
        budget = check_loop_budget()
        elapsed = round(time.perf_counter() - t1, 2)
        detail_parts = list(nat_issues[:3])
        if not budget.ok:
            detail_parts.append(f"budget: {budget.detail}")
        nat_detail = "; ".join(detail_parts) if detail_parts else "OK"
        content_has_issues = bool(nat_issues)
        budget_has_issues = not budget.ok
        nat_has_issues = content_has_issues or budget_has_issues
        nat_blocking = (
            content_has_issues and supervised_stage_blocking("naturalness")
        ) or (budget_has_issues and supervised_stage_blocking("budget"))
        nat_st = _quality_stage_status(has_issues=nat_has_issues, blocking=nat_blocking)
        report.stages.append(
            StageResult("NATURALNESS", "naturalness", nat_st, elapsed, nat_detail[:120])
        )
        if nat_st == "FAIL":
            report.blocked_at = "NATURALNESS"
            return _finish(report, t0)

    # M5
    if not skip_notion:
        step += 1
        _progress(f"[█████] {step}/{total_steps} M5 Notion sync…")
        with timed_stage("supervised_m5"):
            t1 = time.perf_counter()
            rc, detail = _run_script(
                [str(SCRIPTS / "archive-to-notion.sh"), stamp, "--force", "--notify-final"],
                env={"SKIP_INIT": "1"},
            )
            elapsed = round(time.perf_counter() - t1, 2)
        st = "PASS" if rc == 0 else "FAIL"
        report.stages.append(StageResult("M5", "notion_archive", st, elapsed, detail))
        if st == "FAIL":
            report.blocked_at = "M5"
    else:
        report.stages.append(StageResult("M5", "notion_archive", "SKIP", 0.0, "SKIP_NOTION=1"))

    return _finish(report, t0)


def _write_handoff(report: SupervisorReport) -> Path:
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    path = HANDOFF_DIR / f"{report.stamp}_supervised-pipeline.json"
    payload = {
        "stamp": report.stamp,
        "success": report.success,
        "blocked_at": report.blocked_at,
        "elapsed_seconds": report.elapsed_seconds,
        "stages": [
            {
                "id": s.stage_id,
                "label": s.label,
                "status": s.status,
                "elapsed_seconds": s.elapsed_seconds,
                "detail": s.detail[:200],
            }
            for s in report.stages
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"{report.stamp}_supervised-pipeline.md"
    log_path.write_text(format_supervisor_report(report), encoding="utf-8")
    return path


def format_supervisor_report(report: SupervisorReport) -> str:
    if report.success and report.has_warnings:
        icon = "⚠️"
    elif report.success:
        icon = "✅"
    else:
        icon = "❌"
    lines = [
        f"{icon} Pipeline Supervisor · {report.stamp}",
        "",
        f"⏱ {report.elapsed_seconds}s"
        + (f" · blocked at **{report.blocked_at}**" if report.blocked_at else ""),
        "",
        "| Stage | 상태 | 시간 | 상세 |",
        "|-------|------|------|------|",
    ]
    for s in report.stages:
        sym = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭"}.get(s.status, s.status)
        lines.append(
            f"| {s.stage_id} {s.label} | {sym} | {s.elapsed_seconds}s | {s.detail[:60]} |"
        )
    lines.append(f"\n📋 `content/logs/{report.stamp}_supervised-pipeline.md`")
    return "\n".join(lines)
