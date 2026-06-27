"""Wiki Curator Agent — seed · lint · ingest 큐 · status (결정적 코어)."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from lib.common import studio_today, truncate
from lib.wiki_seed import seed_from_brief_graph

WORKDIR = Path.home() / "hermes-content-studio"
WIKI_ROOT = WORKDIR / "content" / "wiki"
CONCEPTS_DIR = WIKI_ROOT / "concepts"
INDEX_PATH = WIKI_ROOT / "index.md"
LOG_PATH = WIKI_ROOT / "log.md"
RAW_DIR = WORKDIR / "content" / "research" / "raw"
INGEST_QUEUE = WIKI_ROOT / "_ingest_queue.json"
LOGS_DIR = WORKDIR / "content" / "logs"
CONFIG_PATH = WORKDIR / "config" / "wiki.yaml"


def _load_wiki_cfg() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def wiki_status() -> dict[str, Any]:
    concepts = list(CONCEPTS_DIR.glob("*.md")) if CONCEPTS_DIR.is_dir() else []
    raw_files = [
        p for p in (RAW_DIR.glob("*") if RAW_DIR.is_dir() else []) if p.is_file() and p.name != ".gitkeep"
    ]
    queue = _load_ingest_queue()
    return {
        "concepts": len(concepts),
        "index_exists": INDEX_PATH.exists(),
        "raw_pending": len(raw_files),
        "ingest_queued": len(queue.get("items", [])),
        "log_exists": LOG_PATH.exists(),
    }


def _load_ingest_queue() -> dict:
    if not INGEST_QUEUE.exists():
        return {"version": 1, "items": [], "updated_at": ""}
    try:
        return json.loads(INGEST_QUEUE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "items": [], "updated_at": ""}


def _save_ingest_queue(data: dict) -> None:
    WIKI_ROOT.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    INGEST_QUEUE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_index_keys() -> set[str]:
    if not INDEX_PATH.exists():
        return set()
    keys: set[str] = set()
    for line in INDEX_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith("| topic_key"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts and parts[0] != "—":
                keys.add(parts[0])
    return keys


def lint_wiki(*, write_report: bool = True) -> dict[str, Any]:
    """결정적 wiki lint — 고아·누락·깨진 링크·빈 요약."""
    issues: list[str] = []
    concept_files = {p.stem for p in CONCEPTS_DIR.glob("*.md")} if CONCEPTS_DIR.is_dir() else set()
    index_keys = _parse_index_keys()

    orphans = sorted(concept_files - index_keys)
    missing = sorted(index_keys - concept_files)
    if orphans:
        issues.append(f"index 미등록 concept: {', '.join(orphans[:8])}")
    if missing:
        issues.append(f"index만 존재(파일 없음): {', '.join(missing[:8])}")

    for path in CONCEPTS_DIR.glob("*.md") if CONCEPTS_DIR.is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace")
        summ_m = re.search(r"## 최신 요약\n(.+?)\n\n##", text, re.S)
        summ = (summ_m.group(1).strip() if summ_m else "")
        if len(summ) < 20 or summ == path.stem:
            issues.append(f"빈/짧은 요약: {path.name}")
        for link in re.findall(r"\[\[([^\]]+)\]\]", text):
            key = link.strip().lower().replace(" ", "_")
            if key not in concept_files and key != "—":
                issues.append(f"깨진 링크: {path.name} → [[{link}]]")

    stamp = studio_today()
    report = {
        "stamp": stamp,
        "concept_count": len(concept_files),
        "index_count": len(index_keys),
        "issue_count": len(issues),
        "issues": issues,
        "ok": len(issues) == 0,
    }
    if write_report:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        path = LOGS_DIR / f"{stamp}_wiki-curator-lint.md"
        lines = [
            f"# Wiki Curator Lint — {stamp}",
            "",
            f"- concepts: {len(concept_files)} · index rows: {len(index_keys)}",
            f"- issues: {len(issues)}",
            "",
        ]
        if issues:
            lines.append("## Issues")
            lines.append("")
            lines.extend(f"- {i}" for i in issues)
        else:
            lines.append("✅ PASS")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report["report_path"] = str(path)
        _append_wiki_log("lint", f"{len(issues)} issues")
    return report


def _append_wiki_log(label: str, detail: str) -> None:
    stamp = studio_today()
    entry = f"\n## [{stamp}] curator-{label} | {detail}\n"
    if LOG_PATH.exists():
        LOG_PATH.write_text(LOG_PATH.read_text(encoding="utf-8") + entry, encoding="utf-8")
    else:
        LOG_PATH.write_text("# Wiki Log\n" + entry, encoding="utf-8")


def scan_ingest_queue() -> dict[str, Any]:
    """raw/ 신규 파일 → ingest 큐 (LLM ingest 전 단계)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    data = _load_ingest_queue()
    known = {item.get("path") for item in data.get("items", [])}
    added: list[dict] = []
    for path in sorted(RAW_DIR.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        rel = str(path.relative_to(WORKDIR))
        if rel in known:
            continue
        added.append(
            {
                "path": rel,
                "name": path.name,
                "size": path.stat().st_size,
                "status": "pending",
                "queued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    if added:
        data.setdefault("items", []).extend(added)
        _save_ingest_queue(data)
        _append_wiki_log("ingest-queue", f"+{len(added)} files")
    return {"added": len(added), "total": len(data.get("items", [])), "items": added}


def run_wiki_ingest_llm(target: str = "") -> bool:
    """HERMES_WIKI_INGEST=1 일 때만 LLM ingest 트리거."""
    if os.environ.get("HERMES_WIKI_INGEST", "0") != "1":
        return False
    cmd = [str(WORKDIR / "scripts" / "run-wiki-ingest.sh")]
    if target:
        cmd.append(target)
    subprocess.run(cmd, cwd=str(WORKDIR), check=False)
    return True


def run_wiki_curator(
    mode: str = "status",
    *,
    write_report: bool = True,
    trigger_llm: bool = False,
) -> dict[str, Any]:
    """mode: status | seed | lint | ingest | all."""
    mode = mode.lower()
    result: dict[str, Any] = {"mode": mode, "stamp": studio_today()}

    if mode in ("status", "all"):
        result["status"] = wiki_status()

    if mode in ("seed", "all"):
        seed_result = seed_from_brief_graph()
        result["seed"] = seed_result
        _append_wiki_log("seed", f"{seed_result.get('concepts', 0)} concepts")

    if mode in ("lint", "all"):
        result["lint"] = lint_wiki(write_report=write_report)

    if mode in ("ingest", "all"):
        result["ingest"] = scan_ingest_queue()
        if trigger_llm or os.environ.get("HERMES_WIKI_INGEST", "0") == "1":
            result["ingest_llm"] = run_wiki_ingest_llm()

    if mode in ("lint-llm",) and os.environ.get("HERMES_WIKI_LINT", "0") == "1":
        subprocess.run([str(WORKDIR / "scripts" / "run-wiki-lint.sh")], cwd=str(WORKDIR), check=False)
        result["lint_llm"] = True

    return result


def format_curator_summary(result: dict[str, Any]) -> str:
    mode = result.get("mode", "status")
    lines = [f"📚 Wiki Curator · {mode} · {result.get('stamp')}", ""]
    if "status" in result:
        s = result["status"]
        lines.append(
            f"concepts={s.get('concepts')} · raw_pending={s.get('raw_pending')} · "
            f"ingest_queued={s.get('ingest_queued')}"
        )
    if "seed" in result:
        lines.append(f"🌱 seed: {result['seed'].get('concepts', 0)} concepts")
    if "lint" in result:
        lint = result["lint"]
        icon = "✅" if lint.get("ok") else "⚠️"
        lines.append(f"{icon} lint: {lint.get('issue_count', 0)} issues")
        if lint.get("report_path"):
            rel = str(lint["report_path"]).replace(str(WORKDIR) + "/", "")
            lines.append(f"📋 `{rel}`")
    if "ingest" in result:
        ing = result["ingest"]
        lines.append(f"📥 ingest queue: +{ing.get('added', 0)} (total {ing.get('total', 0)})")
    return "\n".join(lines)
