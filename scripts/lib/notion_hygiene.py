"""Notion Daily Archive 중복 정리·미완성 콘텐츠 보관."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from lib.notion_client import create_page, fetch_page, log, move_pages, notion_page_id_to_url
from lib.notion_quality import assess_content
from lib.notion_templates import normalize_category_markdown

PAGE_TAG_RE = re.compile(r'<page\s+url="([^"]+)"[^>]*>([^<]*)</page>')


def hygiene_enabled(cfg: dict) -> bool:
    return bool((cfg.get("hygiene") or {}).get("enabled", True))


def category_from_title(title: str, cfg: dict) -> str | None:
    clean = title.strip()
    for key, cat in cfg.get("categories", {}).items():
        label = cat.get("label", "")
        icon = cat.get("icon", "")
        if label and label in clean:
            return key
        if icon and clean.startswith(icon):
            return key
    return None


def _url_to_page_id(page_url: str) -> str:
    compact = page_url.replace("-", "")
    id_m = re.search(r"/p/([0-9a-f]{32})", compact, re.I)
    if id_m:
        raw = id_m.group(1)
        return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
    id_m = re.search(
        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        page_url,
        re.I,
    )
    return id_m.group(1) if id_m else ""


def parse_child_pages(fetch_text: str) -> list[dict]:
    children: list[dict] = []
    for m in PAGE_TAG_RE.finditer(fetch_text):
        page_url = m.group(1)
        title = (m.group(2) or "").strip()
        page_id = _url_to_page_id(page_url)
        if page_id:
            children.append({"id": page_id, "title": title, "url": page_url})
    return children


def resolve_state_page(state: dict, stamp: str, cat_key: str) -> tuple[str, dict | None]:
    """canonical 키 우선, draft-only는 `{stamp}/{cat}@draft` fallback."""
    pages = state.get("pages", {})
    pk = f"{stamp}/{cat_key}"
    draft_pk = f"{pk}@draft"
    if pk in pages:
        return pk, pages[pk]
    if draft_pk in pages:
        return draft_pk, pages[draft_pk]
    return pk, None


def canonical_page_id(state: dict, stamp: str, cat_key: str) -> str | None:
    _, entry = resolve_state_page(state, stamp, cat_key)
    if isinstance(entry, dict):
        return entry.get("id")
    return None


def stale_state_keys(state: dict, stamp: str, cfg: dict) -> list[str]:
    """one_page_per_category 모드에서 레거시 per-file 키 제거 대상."""
    if not (cfg.get("rules") or {}).get("one_page_per_category", False):
        return []
    stale = []
    prefix = f"{stamp}/"
    canonical_suffixes = set(cfg.get("categories", {}).keys())
    for key in list(state.get("pages", {}).keys()):
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix) :]
        if "/" in rest and rest.split("/")[0] in canonical_suffixes:
            stale.append(key)
    return stale


def ensure_draft_archive(registry, cfg: dict, state: dict) -> tuple[str, str]:
    draft = state.get("draft_archive") or {}
    if draft.get("id"):
        return draft["id"], draft.get("url", notion_page_id_to_url(draft["id"]))

    hcfg = cfg.get("hygiene") or {}
    dcfg = hcfg.get("draft_archive") or {}
    root = cfg["archive"]["root_page_id"]
    title = dcfg.get("title", "Draft & Incomplete Archive")
    icon = dcfg.get("icon", "🗂️")
    content = (
        "## 미완성·중복 콘텐츠 보관\n\n"
        "정확성이 떨어지거나 완성되지 않은 텍스트, 카테고리 중복 페이지가 "
        "이곳으로 이동됩니다. 메인 Daily Archive는 **카테고리당 최신 1페이지**만 유지합니다.\n\n"
        f"생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    page_id, url = create_page(registry, cfg, root, title, content, icon)
    state["draft_archive"] = {"id": page_id, "url": url}
    return page_id, url


def ensure_draft_day_page(
    registry, cfg: dict, state: dict, stamp: str, draft_root_id: str
) -> tuple[str, str]:
    days = state.setdefault("draft_days", {})
    if stamp in days and isinstance(days[stamp], dict):
        return days[stamp]["id"], days[stamp].get("url", "")

    title = f"{stamp} — 보관"
    content = (
        f"## {stamp} 미완성·중복 보관\n\n"
        "메인 Daily Archive에서 이동된 페이지입니다.\n"
        f"갱신: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    page_id, url = create_page(registry, cfg, draft_root_id, title, content, "📦")
    days[stamp] = {"id": page_id, "url": url}
    return page_id, url


def prune_state(state: dict, stamp: str, cfg: dict) -> list[str]:
    removed = []
    for key in stale_state_keys(state, stamp, cfg):
        state["pages"].pop(key, None)
        removed.append(key)
    return removed


def find_duplicate_children(
    children: list[dict],
    stamp: str,
    cat_key: str,
    canonical_id: str,
    cfg: dict,
) -> list[dict]:
    dupes = []
    cat = cfg["categories"][cat_key]
    label = cat.get("label", "")
    icon = cat.get("icon", "")
    for child in children:
        if child["id"] == canonical_id:
            continue
        title = child["title"]
        if cat_key == category_from_title(title, cfg) or label in title or title.startswith(icon):
            dupes.append(child)
    return dupes


def run_day_hygiene(
    registry,
    cfg: dict,
    state: dict,
    stamp: str,
    *,
    dry_run: bool = False,
) -> dict:
    """일자별 중복 페이지 이동 + state 정리."""
    report = {
        "stamp": stamp,
        "moved": [],
        "pruned_state": [],
        "duplicates": 0,
        "dry_run": dry_run,
    }
    if not hygiene_enabled(cfg):
        report["skipped"] = "hygiene disabled"
        return report

    day_entry = state.get("days", {}).get(stamp)
    if not day_entry:
        report["skipped"] = "no day page in state"
        return report

    day_id = day_entry["id"] if isinstance(day_entry, dict) else day_entry
    fetch = fetch_page(registry, cfg, day_id)
    text = fetch.get("text") or fetch.get("raw") or ""
    children = parse_child_pages(text)

    draft_root_url = (state.get("draft_archive") or {}).get("url", "")
    draft_day_id = (state.get("draft_days") or {}).get(stamp, {}).get("id", "")

    if not dry_run:
        draft_root_id, draft_root_url = ensure_draft_archive(registry, cfg, state)
        draft_day_id, _ = ensure_draft_day_page(registry, cfg, state, stamp, draft_root_id)

    moved_ids: list[str] = []
    for cat_key in cfg.get("categories", {}):
        if cfg["categories"][cat_key].get("pipeline") is False and cat_key.startswith("lecture"):
            continue
        canonical_id = canonical_page_id(state, stamp, cat_key)
        if not canonical_id:
            continue
        dupes = find_duplicate_children(children, stamp, cat_key, canonical_id, cfg)
        for d in dupes:
            report["duplicates"] += 1
            if dry_run or not draft_day_id:
                report["moved"].append({"id": d["id"], "title": d["title"], "action": "would_move"})
                continue
            try:
                move_pages(registry, cfg, [d["id"]], draft_day_id)
                moved_ids.append(d["id"])
                report["moved"].append(
                    {"id": d["id"], "title": d["title"], "action": "moved", "reason": "duplicate"}
                )
                log(f"Moved duplicate → draft: {d['title']}")
            except Exception as exc:  # noqa: BLE001
                report["moved"].append(
                    {"id": d["id"], "title": d["title"], "action": "error", "error": str(exc)}
                )

    report["pruned_state"] = prune_state(state, stamp, cfg) if not dry_run else stale_state_keys(
        state, stamp, cfg
    )
    report["draft_archive_url"] = draft_root_url
    report["draft_day_id"] = draft_day_id
    return report


def resolve_sync_parent(
    registry,
    cfg: dict,
    state: dict,
    stamp: str,
    cat_key: str,
    raw_text: str,
    *,
    path: Path | None = None,
) -> tuple[str, str, dict]:
    """동기화 대상 부모 페이지 결정. (parent_id, tier, quality_result_dict)."""
    normalized = normalize_category_markdown(raw_text, cat_key, path=path)
    quality = assess_content(normalized, cat_key, cfg, path=path)
    qdict = {
        "ok": quality.ok,
        "score": quality.score,
        "tier": quality.tier,
        "issues": quality.issues,
        "fact_checked": quality.fact_checked,
        "fact_check_issues": quality.fact_check_issues,
    }
    if quality.tier == "canonical":
        day_entry = state.get("days", {}).get(stamp)
        if not day_entry:
            return "", quality.tier, qdict
        day_id = day_entry["id"] if isinstance(day_entry, dict) else day_entry
        return day_id, quality.tier, qdict

    draft_root_id, _ = ensure_draft_archive(registry, cfg, state)
    draft_day_id, _ = ensure_draft_day_page(registry, cfg, state, stamp, draft_root_id)
    return draft_day_id, quality.tier, qdict
