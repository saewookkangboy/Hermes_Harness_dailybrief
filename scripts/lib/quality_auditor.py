"""Quality Auditor Agent — 결정적 DoD·채널 검증 일괄 감사."""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from lib.brief_gate import brief_insight_count, brief_path, load_search_context, needs_daily_research
from lib.common import studio_today
from lib.newsletter_complete import audit_newsletter_md
from lib.notion_quality import assess_content

WORKDIR = Path.home() / "hermes-content-studio"
SCRIPTS = WORKDIR / "scripts"
LOGS_DIR = WORKDIR / "content" / "logs"
NOTION_CFG = WORKDIR / "config" / "notion-archive.yaml"


@dataclass
class AuditItem:
    channel: str
    path: str
    status: str  # PASS | WARN | FAIL | SKIP
    detail: str = ""


@dataclass
class AuditReport:
    stamp: str
    items: list[AuditItem] = field(default_factory=list)
    brief_ok: bool = True
    elapsed_seconds: float = 0.0

    @property
    def pass_count(self) -> int:
        return sum(1 for i in self.items if i.status == "PASS")

    @property
    def fail_count(self) -> int:
        return sum(1 for i in self.items if i.status == "FAIL")

    @property
    def all_pass(self) -> bool:
        return self.brief_ok and self.fail_count == 0


def _notion_cfg() -> dict:
    if not NOTION_CFG.exists():
        return {}
    with NOTION_CFG.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _glob_one(pattern: str) -> Path | None:
    matches = sorted(WORKDIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def glob_linkedin_feed(stamp: str) -> Path | None:
    """Feed 포스트 — repurpose `-iN` variant 우선 (context 패키지와 쌍)."""
    matches = list(WORKDIR.glob(f"content/linkedin/{stamp}_linkedin_*.md"))
    if not matches:
        return None

    def _rank(p: Path) -> tuple[int, float]:
        m = re.search(r"-i(\d+)$", p.stem)
        idx = int(m.group(1)) if m else 0
        return (idx, p.stat().st_mtime)

    return max(matches, key=_rank)


def linkedin_context_path(stamp: str, feed_path: Path) -> Path | None:
    """Notion 품질 마커는 packages linkedin-context에 있음 (feed와 분리)."""
    m = re.search(r"-i(\d+)$", feed_path.stem)
    if m:
        ctx = WORKDIR / f"content/packages/{stamp}_linkedin-context_i{m.group(1)}.md"
        if ctx.exists():
            return ctx
    default = WORKDIR / f"content/packages/{stamp}_linkedin-context.md"
    if default.exists():
        return default
    return _glob_one(f"content/packages/{stamp}_linkedin-context*.md")


def _run_validate(vtype: str, path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [str(SCRIPTS / "validate-output.sh"), vtype, str(path)],
        cwd=str(WORKDIR),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0
    line = out.strip().splitlines()[-1] if out.strip() else ("OK" if ok else "FAIL")
    return ok, line


def _assess_file(path: Path, cat_key: str) -> tuple[str, str]:
    cfg = _notion_cfg()
    text = path.read_text(encoding="utf-8")
    result = assess_content(text, cat_key, cfg, path=path)
    if result.ok:
        return "PASS", f"score={result.score} tier={result.tier}"
    issues = "; ".join(result.issues[:3])
    status = "WARN" if result.score >= 60 else "FAIL"
    return status, f"score={result.score} — {issues}"


def audit_brief(stamp: str) -> tuple[bool, str]:
    path = brief_path(stamp)
    if not path.exists():
        return False, "Brief SoT 없음"
    ctx = load_search_context(stamp)
    if not ctx:
        return False, "search_context 없음"
    n = brief_insight_count(stamp)
    if n < 7:
        return False, f"Top 7 미달 ({n}개)"
    if needs_daily_research(stamp):
        return False, "신선도 게이트 FAIL — 리서치 재실행 권장"
    return True, f"Top {n} · search_context OK"


def audit_stamp(stamp: str, *, write_report: bool = True) -> AuditReport:
    """Brief + 채널 산출물 결정적 감사."""
    t0 = time.perf_counter()
    report = AuditReport(stamp=stamp)

    brief_ok, brief_detail = audit_brief(stamp)
    report.brief_ok = brief_ok
    report.items.append(
        AuditItem(channel="brief", path=str(brief_path(stamp)), status="PASS" if brief_ok else "FAIL", detail=brief_detail)
    )

    channel_specs: list[tuple[str, str, str]] = [
        ("research", f"content/research/{stamp}_brief.md", "research"),
        ("blog", f"content/blog/{stamp}_blog_*.html", "blog"),
        ("instagram", f"content/instagram/{stamp}_instagram_*.md", "instagram"),
        ("linkedin", f"content/linkedin/{stamp}_linkedin_*.md", "linkedin"),
        ("newsletter", f"content/newsletter/{stamp}_newsletter_*.md", "newsletter"),
    ]

    for channel, pattern, vtype in channel_specs:
        if channel == "linkedin":
            path = glob_linkedin_feed(stamp)
        elif "*" in pattern:
            path = _glob_one(pattern)
        else:
            path = Path(WORKDIR / pattern)
        if not path or not path.exists():
            report.items.append(AuditItem(channel=channel, path=pattern, status="SKIP", detail="산출물 없음"))
            continue

        ok, line = _run_validate(vtype, path)
        status = "PASS" if ok else "FAIL"
        detail = line

        if channel == "newsletter":
            issues = audit_newsletter_md(path.read_text(encoding="utf-8"))
            if issues:
                status = "FAIL"
                detail = "; ".join(issues[:5])

        if channel == "linkedin":
            ctx_path = linkedin_context_path(stamp, path)
            if ctx_path:
                q_status, q_detail = _assess_file(ctx_path, channel)
            else:
                q_status, q_detail = "WARN", "linkedin-context 패키지 없음"
        else:
            q_status, q_detail = _assess_file(path, channel)

        if status == "PASS" and q_status != "PASS":
            status = q_status
            if channel == "linkedin":
                detail = f"feed OK · {q_detail}"
            else:
                detail = q_detail

        report.items.append(AuditItem(channel=channel, path=str(path), status=status, detail=detail))

    report.elapsed_seconds = round(time.perf_counter() - t0, 3)

    if write_report:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = LOGS_DIR / f"{stamp}_audit-report.md"
        report_path.write_text(format_audit_report(report), encoding="utf-8")
        report.items.append(
            AuditItem(channel="report", path=str(report_path), status="PASS", detail="audit-report 저장")
        )

    return report


def format_audit_report(report: AuditReport) -> str:
    lines = [
        f"# Quality Audit — {report.stamp}",
        "",
        f"- **Brief SoT:** {'✅' if report.brief_ok else '❌'}",
        f"- **PASS:** {report.pass_count} · **FAIL:** {report.fail_count}",
        f"- **⏱:** {report.elapsed_seconds}s",
        "",
        "## 채널별",
        "",
        "| 채널 | 상태 | 상세 |",
        "|------|------|------|",
    ]
    for item in report.items:
        if item.channel == "report":
            continue
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭"}.get(item.status, "·")
        rel = item.path.replace(str(WORKDIR) + "/", "")
        lines.append(f"| {item.channel} | {icon} {item.status} | {item.detail[:80]} |")
    lines.extend(
        [
            "",
            "## DoD 체크리스트",
            f"- [{'x' if report.brief_ok else ' '}] Brief Top 7 + search_context",
            f"- [{'x' if report.fail_count == 0 else ' '}] validate-output.sh 전 채널",
            f"- [{'x' if report.all_pass else ' '}] 전체 PASS",
        ]
    )
    return "\n".join(lines)


def format_audit_summary(report: AuditReport) -> str:
    icon = "✅" if report.all_pass else "❌"
    lines = [
        f"{icon} Quality Audit · {report.stamp}",
        "",
        f"Brief: {'OK' if report.brief_ok else 'FAIL'} · PASS {report.pass_count} · FAIL {report.fail_count} · ⏱ {report.elapsed_seconds}s",
        "",
    ]
    for item in report.items:
        if item.channel == "report":
            continue
        sym = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭"}.get(item.status, "·")
        lines.append(f"{sym} {item.channel}: {item.detail[:60]}")
    report_path = LOGS_DIR / f"{report.stamp}_audit-report.md"
    if report_path.exists():
        lines.append(f"\n📋 `{report_path.relative_to(WORKDIR)}`")
    return "\n".join(lines)


def run_quality_audit(stamp: str | None = None, *, write_report: bool = True) -> dict[str, Any]:
    stamp = stamp or studio_today()
    report = audit_stamp(stamp, write_report=write_report)
    return {
        "stamp": stamp,
        "all_pass": report.all_pass,
        "pass_count": report.pass_count,
        "fail_count": report.fail_count,
        "elapsed_seconds": report.elapsed_seconds,
        "report_path": str(LOGS_DIR / f"{stamp}_audit-report.md"),
    }
