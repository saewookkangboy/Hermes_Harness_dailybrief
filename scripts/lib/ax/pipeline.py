"""Topic Pack 오케스트레이터 — M1 Discover → M2 Blueprint → M3 Resource → M4 Future → M5 Channels → M6 Archive."""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.ax.blueprint import build_blueprint, render_blueprint
from lib.ax.brief import render_brief
from lib.ax.channels import build_channels, score_channels, write_channels
from lib.ax.config import WORKDIR, artifact_path, load_config, topic_dir
from lib.ax.evidence import EvidencePack, build_evidence_pack
from lib.ax.future import build_future, render_future
from lib.ax.gates import GateReport, GateResult, blueprint_gate, channel_gate, future_gate, research_gates
from lib.ax.lens_queries import generate_queries
from lib.ax.memory import (
    prior_runs,
    prior_urls,
    record_run,
    render_topic_pack,
    update_index,
    update_lens_feedback,
)
from lib.ax.resources import build_resource_map, render_resource_map
from lib.ax.sources import fetch_all, load_fixture
from lib.ax.topic_spec import TopicSpec, build_topic_spec
from lib.harness import append_trace

STAGES = ("M1", "M2", "M3", "M4", "M5", "M6")


@dataclass
class TopicRunResult:
    spec: TopicSpec
    report: GateReport
    paths: dict[str, Path] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    notion: dict[str, Any] = field(default_factory=dict)
    stopped_at: str = ""

    @property
    def passed(self) -> bool:
        return self.report.passed and not self.stopped_at

    def summary(self) -> dict[str, Any]:
        return {
            "keyword": self.spec.keyword,
            "slug": self.spec.slug,
            "stamp": self.spec.stamp,
            "domain": self.spec.domain_label,
            "domain_id": self.spec.domain,
            "intent": self.spec.intent_label,
            "passed": self.passed,
            "stopped_at": self.stopped_at,
            "gates": self.report.summary(),
            "timings": self.timings,
            "total_seconds": round(sum(self.timings.values()), 2),
            "paths": {k: str(v) for k, v in self.paths.items()},
            "notion": self.notion,
        }


class _Stage:
    def __init__(self, result: TopicRunResult, name: str):
        self.result, self.name = result, name

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        elapsed = round(time.perf_counter() - self.start, 2)
        self.result.timings[self.name] = elapsed
        sla = (load_config().get("sla_seconds") or {}).get(self.name)
        record = {
            "stage": f"topic_{self.name}",
            "topic": self.result.spec.slug,
            "elapsed_seconds": elapsed,
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if sla and elapsed > sla:
            record["sla_breach"] = True
            print(f"⚠️  SLA 초과 [topic {self.name}]: {elapsed:.1f}s > {sla}s", flush=True)
        if os.environ.get("HERMES_TOPIC_TRACE", "1") != "0":
            append_trace(record)
        return False


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, data: Any) -> Path:
    return _write(path, json.dumps(data, ensure_ascii=False, indent=2))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def archive_notion(stamp: str) -> dict[str, Any]:
    script = WORKDIR / "scripts" / "archive-to-notion.sh"
    proc = subprocess.run(
        ["bash", str(script), stamp, "--force", "--json"],
        cwd=str(WORKDIR),
        capture_output=True,
        text=True,
        timeout=int((load_config().get("sla_seconds") or {}).get("M6", 30)) * 6,
    )
    payload: dict[str, Any] = {}
    lines = proc.stdout.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "{":
            try:
                payload = json.loads("\n".join(lines[i:]))
                break
            except json.JSONDecodeError:
                continue
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "permalink": payload.get("day_url", ""),
        "count": payload.get("count"),
        "log": (proc.stdout + proc.stderr).strip().splitlines()[-3:] if proc.returncode else [],
    }


VALIDATE_TYPES = {
    "research": "topic-brief",
    "ax-blueprint": "ax-blueprint",
    "resource-map": "resource-map",
    "future-ahead": "future-ahead",
    "threads": "threads-package",
    "topic-pack": "topic-pack",
}


def validate_artifacts(paths: dict[str, Path]) -> GateResult:
    script = WORKDIR / "scripts" / "validate-output.sh"
    failed, checked = [], 0
    for key, vtype in VALIDATE_TYPES.items():
        if key not in paths:
            continue
        checked += 1
        proc = subprocess.run(["bash", str(script), vtype, str(paths[key])], capture_output=True, text=True)
        if proc.returncode != 0:
            failed.append(f"{key}: {(proc.stderr or proc.stdout).strip().splitlines()[-1:]}")
    detail = f"validate-output {checked - len(failed)}/{checked}" + (f" · {'; '.join(failed)}" if failed else "")
    return GateResult("validate", not failed, True, detail, [], {"checked": checked})


def run_topic_pack(
    keyword: str,
    stamp: str | None = None,
    *,
    stages: tuple[str, ...] = STAGES,
    fixture: Path | None = None,
    notion: bool = False,
) -> TopicRunResult:
    stamp = stamp or datetime.now().date().isoformat()
    cfg = load_config()
    spec = build_topic_spec(keyword, stamp, cfg)
    result = TopicRunResult(spec=spec, report=GateReport())
    d = topic_dir(spec.slug)
    paths = result.paths
    runs = prior_runs(spec.slug, before_stamp=stamp)
    fixture = fixture or (Path(os.environ["HERMES_TOPIC_FIXTURE"]) if os.environ.get("HERMES_TOPIC_FIXTURE") else None)

    paths["spec"] = d / "topic_spec.json"
    spec.write(paths["spec"])
    evidence_path = artifact_path(spec.slug, stamp, "evidence", "json")
    queries = generate_queries(spec, cfg=cfg)

    if "M1" in stages:
        with _Stage(result, "M1"):
            if fixture:
                rows, errors = load_fixture(fixture), []
            else:
                rows, errors = fetch_all(queries, cfg)
            pack = build_evidence_pack(spec, rows, query_count=len(queries), errors=errors, seen_urls=prior_urls(runs), cfg=cfg)
            pack.write(evidence_path)
            paths["evidence"] = evidence_path
            research_gates(pack, result.report, cfg)
            paths["research"] = _write(artifact_path(spec.slug, stamp, "research"), render_brief(spec, pack, result.report, cfg))
    elif evidence_path.exists():
        pack = EvidencePack.from_dict(_load_json(evidence_path))
        research_gates(pack, result.report, cfg)
        paths["evidence"] = evidence_path
        research_path = artifact_path(spec.slug, stamp, "research")
        if not research_path.exists():
            _write(research_path, render_brief(spec, pack, result.report, cfg))
        paths["research"] = research_path
    else:
        raise FileNotFoundError(f"M1 결과 없음: {evidence_path} — --stages에 M1을 포함하세요")

    if not result.report.passed:
        result.stopped_at = "M1"
        paths["gates"] = artifact_path(spec.slug, stamp, "gates", "json")
        result.report.write(paths["gates"])
        return result

    blueprint = resource_map = future = None
    docs: dict[str, str] = {}
    if paths.get("research"):
        docs["research"] = paths["research"].read_text(encoding="utf-8")

    if "M2" in stages or any(s in stages for s in ("M3", "M4", "M5")):
        with _Stage(result, "M2"):
            blueprint = build_blueprint(spec, pack, cfg)
            result.report.add(blueprint_gate(blueprint, cfg))
            docs["ax-blueprint"] = render_blueprint(blueprint, cfg)
            paths["ax-blueprint"] = _write(artifact_path(spec.slug, stamp, "ax-blueprint"), docs["ax-blueprint"])
            _write_json(artifact_path(spec.slug, stamp, "ax-blueprint", "json"), blueprint)

    if blueprint and ("M3" in stages or any(s in stages for s in ("M4", "M5"))):
        with _Stage(result, "M3"):
            resource_map = build_resource_map(spec, pack, blueprint, cfg)
            docs["resource-map"] = render_resource_map(resource_map)
            paths["resource-map"] = _write(artifact_path(spec.slug, stamp, "resource-map"), docs["resource-map"])
            _write_json(artifact_path(spec.slug, stamp, "resource-map", "json"), resource_map)

    if blueprint and ("M4" in stages or "M5" in stages):
        with _Stage(result, "M4"):
            future = build_future(spec, pack, blueprint, history=runs, cfg=cfg)
            result.report.add(future_gate(future, cfg))
            docs["future-ahead"] = render_future(future)
            paths["future-ahead"] = _write(artifact_path(spec.slug, stamp, "future-ahead"), docs["future-ahead"])
            _write_json(artifact_path(spec.slug, stamp, "future-ahead", "json"), future)

    channel_paths: dict[str, Path] = {}
    if "M5" in stages and blueprint and resource_map and future and result.report.passed:
        with _Stage(result, "M5"):
            drafts = build_channels(spec, pack, blueprint, resource_map, future)
            result.report.add(channel_gate(score_channels(drafts), cfg))
            channel_paths = write_channels(spec, drafts)
            paths.update(channel_paths)

    if "M6" in stages:
        with _Stage(result, "M6"):
            paths["topic-pack"] = _write(
                artifact_path(spec.slug, stamp, "topic-pack"), render_topic_pack(spec, docs, channel_paths, result.report)
            )
            result.report.add(validate_artifacts(paths))
            result.report.write(artifact_path(spec.slug, stamp, "gates", "json"))
            record_run(spec, pack, future, result.report)
            update_index(spec, paths, result.report)
            if "M1" in stages and not fixture:
                update_lens_feedback(pack, queries)
            if notion and result.report.passed:
                result.notion = archive_notion(stamp)
    else:
        result.report.write(artifact_path(spec.slug, stamp, "gates", "json"))
    paths["gates"] = artifact_path(spec.slug, stamp, "gates", "json")
    return result
