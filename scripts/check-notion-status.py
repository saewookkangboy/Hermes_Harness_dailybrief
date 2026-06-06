#!/usr/bin/env python3
"""Notion 아카이브 상태 점검 — 로컬·state·Notion 3-way 감사."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from fnmatch import fnmatch
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
sys.path.insert(0, str(WORKDIR / "scripts"))

from lib.markdown_notion import file_content_hash, is_text_file  # noqa: E402
from lib.notion_client import fetch_page, load_config, load_state, log, setup_mcp  # noqa: E402
from lib.notion_hygiene import (  # noqa: E402
    canonical_page_id,
    category_from_title,
    find_duplicate_children,
    hygiene_enabled,
    parse_child_pages,
    prune_state,
    run_day_hygiene,
    stale_state_keys,
)
from lib.notion_quality import assess_content  # noqa: E402


def local_canonical_files(stamp: str, cfg: dict) -> dict[str, Path]:
    one_per = (cfg.get("rules") or {}).get("one_page_per_category", False)
    found: dict[str, Path] = {}
    for key, cat in cfg.get("categories", {}).items():
        if cat.get("pipeline") is False and key.startswith("lecture"):
            continue
        paths = []
        for p in sorted(WORKDIR.glob(cat["glob"])):
            if stamp not in p.name:
                continue
            if any(fnmatch(p.name, ex) for ex in cat.get("exclude", [])):
                continue
            if p.name.startswith("_") or not is_text_file(p):
                continue
            paths.append(p)
        if paths:
            found[key] = sorted(paths, key=lambda x: x.name)[-1] if one_per else paths[-1]
    return found


def audit_date(stamp: str, *, fix: bool = False, dry_run: bool = False) -> dict:
    cfg = load_config()
    state = load_state()
    report: dict = {
        "stamp": stamp,
        "ok": True,
        "categories": [],
        "issues": [],
        "summary": {
            "synced": 0,
            "stale_local": 0,
            "missing_notion": 0,
            "duplicates": 0,
            "incomplete": 0,
            "stale_state_keys": 0,
        },
    }

    local_files = local_canonical_files(stamp, cfg)
    registry = None
    day_children: list[dict] = []

    day_entry = state.get("days", {}).get(stamp)
    if day_entry:
        registry = setup_mcp()
        day_id = day_entry["id"] if isinstance(day_entry, dict) else day_entry
        try:
            fetch = fetch_page(registry, cfg, day_id)
            day_children = parse_child_pages(fetch.get("text") or "")
        except Exception as exc:  # noqa: BLE001
            report["issues"].append(f"Notion fetch 실패: {exc}")
            report["ok"] = False

    stale_keys = stale_state_keys(state, stamp, cfg)
    report["summary"]["stale_state_keys"] = len(stale_keys)
    if stale_keys:
        report["issues"].append(f"레거시 state 키 {len(stale_keys)}건 (per-file → per-category)")
        report["ok"] = False

    for cat_key, cat in sorted(
        cfg.get("categories", {}).items(),
        key=lambda x: x[1].get("order", 99),
    ):
        if cat.get("pipeline") is False and cat_key.startswith("lecture"):
            continue

        entry = {
            "category": cat_key,
            "label": cat.get("label", cat_key),
            "local": None,
            "notion_id": None,
            "notion_url": None,
            "hash_match": None,
            "quality": None,
            "duplicates": 0,
            "status": "ok",
        }

        local_path = local_files.get(cat_key)
        pk = f"{stamp}/{cat_key}"
        state_page = state.get("pages", {}).get(pk)

        if local_path:
            raw = local_path.read_text(encoding="utf-8")
            chash = file_content_hash(raw)
            quality = assess_content(raw, cat_key, cfg, path=local_path)
            entry["local"] = str(local_path)
            entry["quality"] = {
                "score": quality.score,
                "tier": quality.tier,
                "issues": quality.issues,
            }
            if quality.tier == "draft":
                report["summary"]["incomplete"] += 1
                entry["status"] = "incomplete"
                report["issues"].append(
                    f"{cat_key}: 미완성 (score={quality.score}) — Draft Archive 대상"
                )
                report["ok"] = False

            if state_page:
                entry["notion_id"] = state_page.get("id")
                entry["notion_url"] = state_page.get("url")
                entry["hash_match"] = state_page.get("hash") == chash
                if not entry["hash_match"]:
                    report["summary"]["stale_local"] += 1
                    entry["status"] = "stale"
                    report["issues"].append(f"{cat_key}: 로컬 변경됨 (Notion 재동기화 필요)")
                    report["ok"] = False
                else:
                    report["summary"]["synced"] += 1
            else:
                report["summary"]["missing_notion"] += 1
                entry["status"] = "missing"
                report["issues"].append(f"{cat_key}: Notion 페이지 없음 (state 미등록)")
                report["ok"] = False
        elif state_page:
            entry["notion_id"] = state_page.get("id")
            entry["notion_url"] = state_page.get("url")
            entry["status"] = "orphan_notion"
            report["issues"].append(f"{cat_key}: Notion만 존재 (로컬 파일 없음)")

        canonical_id = canonical_page_id(state, stamp, cat_key)
        if canonical_id and day_children:
            dupes = find_duplicate_children(day_children, stamp, cat_key, canonical_id, cfg)
            entry["duplicates"] = len(dupes)
            if dupes:
                report["summary"]["duplicates"] += len(dupes)
                entry["status"] = "duplicates"
                report["issues"].append(
                    f"{cat_key}: Notion 중복 {len(dupes)}건 — Draft Archive 이동 대상"
                )
                report["ok"] = False

        report["categories"].append(entry)

    draft = state.get("draft_archive") or {}
    if draft.get("url"):
        report["draft_archive_url"] = draft["url"]

    if fix and hygiene_enabled(cfg):
        if registry is None:
            registry = setup_mcp()
        hygiene = run_day_hygiene(registry, cfg, state, stamp, dry_run=dry_run)
        if not dry_run:
            prune_state(state, stamp, cfg)
            from lib.notion_client import save_state

            save_state(state)
        report["hygiene"] = hygiene
        if hygiene.get("duplicates"):
            report["ok"] = False

    return report


def format_human(report: dict) -> str:
    s = report["summary"]
    lines = [
        f"📊 Notion 상태 — {report['stamp']}",
        f"  ✅ 동기화: {s['synced']}  ⚠️ 로컬 변경: {s['stale_local']}  "
        f"❌ 미등록: {s['missing_notion']}",
        f"  🔄 중복: {s['duplicates']}  📦 미완성: {s['incomplete']}  "
        f"🗑️ 레거시 state: {s['stale_state_keys']}",
    ]
    if report.get("draft_archive_url"):
        lines.append(f"  🗂️ Draft Archive: {report['draft_archive_url']}")
    if report["issues"]:
        lines.append("")
        lines.append("이슈:")
        for issue in report["issues"][:12]:
            lines.append(f"  • {issue}")
        if len(report["issues"]) > 12:
            lines.append(f"  … 외 {len(report['issues']) - 12}건")
    lines.append("")
    lines.append("전체 OK" if report["ok"] else "조치 필요")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Notion archive status")
    parser.add_argument("date", nargs="?", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fix", action="store_true", help="Run hygiene (move duplicates)")
    parser.add_argument("--dry-run", action="store_true", help="With --fix, report only")
    args = parser.parse_args()

    try:
        report = audit_date(args.date, fix=args.fix, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(format_human(report))
        return 0 if report["ok"] else 1
    except Exception as exc:  # noqa: BLE001
        log(f"ERROR: {exc}", prefix="Notion Status")
        print(f"❌ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
