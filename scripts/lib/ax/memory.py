"""M6 Archive & Learn — 주제 메모리(delta) · 주제 인덱스 · 렌즈 적중률 피드백 · Topic Pack 문서."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.ax.config import index_path, lens_feedback_path, topic_dir
from lib.ax.evidence import EvidencePack
from lib.ax.gates import GateReport
from lib.ax.lens_queries import LensQuery
from lib.ax.topic_spec import TopicSpec

MAX_RUNS = 10


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def memory_path(slug: str) -> Path:
    return topic_dir(slug) / "memory.json"


def load_memory(slug: str) -> dict[str, Any]:
    return _read_json(memory_path(slug), {"runs": []})


def prior_runs(slug: str, before_stamp: str | None = None) -> list[dict[str, Any]]:
    runs = load_memory(slug).get("runs") or []
    if before_stamp:
        runs = [r for r in runs if r.get("stamp") != before_stamp]
    return runs


def prior_urls(runs: list[dict[str, Any]]) -> set[str]:
    return {u for r in runs for u in r.get("urls") or []}


def record_run(spec: TopicSpec, pack: EvidencePack, future: dict[str, Any] | None, report: GateReport) -> dict[str, Any]:
    mem = load_memory(spec.slug)
    runs = [r for r in mem.get("runs") or [] if r.get("stamp") != spec.stamp]
    runs.append(
        {
            "stamp": spec.stamp,
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "urls": [ev.url for ev in pack.items],
            "lens_counts": pack.lens_counts(),
            "terms": [w["term"] for w in (future or {}).get("weak_signals") or []],
            "relevant_count": pack.relevant_count,
            "new_count": pack.new_count(),
            "gates_passed": report.passed,
        }
    )
    mem.update({"keyword": spec.keyword, "slug": spec.slug, "runs": runs[-MAX_RUNS:]})
    _write_json(memory_path(spec.slug), mem)
    return mem


def update_index(spec: TopicSpec, paths: dict[str, Path], report: GateReport) -> dict[str, Any]:
    idx = _read_json(index_path(), {})
    entry = idx.get(spec.slug) or {"keyword": spec.keyword, "runs": 0}
    entry.update(
        {
            "keyword": spec.keyword,
            "domain": spec.domain,
            "intent": spec.intent,
            "last_stamp": spec.stamp,
            "runs": int(entry.get("runs") or 0) + 1,
            "gates": report.summary(),
            "paths": {k: str(v) for k, v in paths.items()},
        }
    )
    idx[spec.slug] = entry
    _write_json(index_path(), idx)
    return entry


def update_lens_feedback(pack: EvidencePack, queries: list[LensQuery]) -> dict[str, Any]:
    """렌즈별 쿼리당 관련 근거 수(yield) 누적 평균 → 다음 실행 쿼리 수 조정."""
    fb = _read_json(lens_feedback_path(), {"lenses": {}})
    q_count = Counter(q.lens for q in queries)
    hits = Counter(ev.lens for ev in pack.items)
    for lens, n in q_count.items():
        stats = fb["lenses"].get(lens) or {"runs": 0, "avg_yield": 0.0}
        runs = int(stats["runs"]) + 1
        current = hits.get(lens, 0) / n
        stats["avg_yield"] = round((float(stats["avg_yield"]) * (runs - 1) + current) / runs, 3)
        stats["runs"] = runs
        stats["last_yield"] = round(current, 3)
        fb["lenses"][lens] = stats
    fb["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_json(lens_feedback_path(), fb)
    return fb


def render_topic_pack(spec: TopicSpec, docs: dict[str, str], channel_paths: dict[str, Path], report: GateReport) -> str:
    """Notion 아카이브용 단일 문서 (Brief + Blueprint + Resource + Future + 채널 목록)."""
    out = [
        f"# [Topic Pack] {spec.keyword}",
        "",
        f"> {spec.stamp} · {spec.domain_label} · {spec.intent_label} · 게이트 {'PASS' if report.passed else 'FAIL'}",
        "",
        f"- 게이트: {report.summary()}",
        "- 채널 초안: " + ", ".join(f"{ch} ({p.name})" for ch, p in channel_paths.items()),
        "",
    ]
    for key in ("research", "ax-blueprint", "resource-map", "future-ahead"):
        if docs.get(key):
            out += ["---", "", _demote(docs[key]), ""]
    return "\n".join(out)


def _demote(md: str) -> str:
    return "\n".join(f"#{ln}" if ln.startswith("#") else ln for ln in md.splitlines())
