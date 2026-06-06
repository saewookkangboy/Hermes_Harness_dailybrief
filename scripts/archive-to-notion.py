#!/usr/bin/env python3
"""Archive Hermes Content Studio outputs to Notion with Telegram notifications.

Uses Hermes Notion MCP OAuth. Returns JSON with permalinks for Telegram sync.
- 카테고리당 최신 1페이지 유지 (replace_content)
- 중복·미완성 콘텐츠는 Draft Archive로 이동
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from fnmatch import fnmatch
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
sys.path.insert(0, str(WORKDIR / "scripts"))

from lib.markdown_notion import file_content_hash, is_text_file, md_to_notion  # noqa: E402
from lib.notion_templates import build_archive_page_body  # noqa: E402
from lib.notify_format import (  # noqa: E402
    TOTAL_STEPS,
    format_completion,
    format_progress,
    format_slack_archive_summary,
)
from lib.notion_client import (  # noqa: E402
    create_page,
    load_config,
    load_state,
    log,
    mcp_call,
    notion_page_id_to_url,
    save_state,
    setup_mcp,
)
from lib.notion_hygiene import hygiene_enabled, resolve_sync_parent, run_day_hygiene  # noqa: E402
from lib.telegram_notify import send_message  # noqa: E402
from lib.slack_notify import send_message as slack_send  # noqa: E402


def push_notify(
    telegram_chat: str,
    slack_channel: str,
    text: str,
    *,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    if telegram_chat:
        send_message(telegram_chat, text)
    if slack_channel:
        slack_send(slack_channel, text)


def files_for_date(stamp: str, cfg: dict) -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = {}
    for key, cat in cfg["categories"].items():
        paths = []
        for p in sorted(WORKDIR.glob(cat["glob"])):
            if stamp not in p.name:
                continue
            excluded = any(fnmatch(p.name, ex) for ex in cat.get("exclude", []))
            if excluded or p.name.startswith("_"):
                continue
            if not is_text_file(p):
                log(f"Skip (binary): {p.name}")
                continue
            paths.append(p)
        if paths:
            found[key] = paths
    return found


def page_key(day: str, category: str, filename: str = "", *, one_per_category: bool = False) -> str:
    if one_per_category:
        return f"{day}/{category}"
    return f"{day}/{category}/{filename}"


def update_page_content(registry, cfg: dict, page_id: str, content: str) -> str:
    """Notion 페이지 본문 전체 교체 (replace_content)."""
    tool = cfg["mcp"].get("update_tool", "mcp_notion_notion_update_page")
    payload = {
        "page_id": page_id,
        "command": "replace_content",
        "new_str": content,
        "allow_deleting_content": True,
    }
    result = mcp_call(registry, tool, payload)
    url = result.get("url") or notion_page_id_to_url(page_id)
    log(f"Replaced content: {page_id} → {url}")
    return url


def build_page_body(
    label: str,
    stamp: str,
    path: Path,
    body: str,
    cfg: dict,
    *,
    tier: str = "canonical",
    quality_score: int | None = None,
    quality_issues: list[str] | None = None,
) -> str:
    return build_archive_page_body(
        label,
        stamp,
        path,
        body,
        tier=tier,
        quality_score=quality_score,
        quality_issues=quality_issues,
    )


def file_status_for_stamp(stamp: str) -> list[tuple[str, bool, str]]:
    rows: list[tuple[str, bool, str]] = []
    checks = [
        ("Research Brief", WORKDIR / "content" / "research" / f"{stamp}_brief.md"),
        ("Blog", WORKDIR / "content" / "packages" / f"{stamp}_blog-article.md"),
        ("Instagram", WORKDIR / "content" / "packages" / f"{stamp}_instagram-context.md"),
        ("LinkedIn", WORKDIR / "content" / "packages" / f"{stamp}_linkedin-context.md"),
        ("Unified", WORKDIR / "content" / "packages" / f"{stamp}_unified-context.md"),
    ]
    for label, path in checks:
        if path.exists():
            try:
                rel = str(path.relative_to(WORKDIR))
            except ValueError:
                rel = path.name
            rows.append((label, True, rel))
        else:
            rows.append((label, False, ""))
    return rows


def pending_with_content(
    stamp: str,
    cfg: dict,
    state: dict,
    force: bool = False,
) -> dict[str, list[tuple[Path, str, str, str]]]:
    """Return files needing sync: (path, notion_body, content_hash, raw_text)."""
    min_chars = (cfg.get("rules") or {}).get("min_body_chars", 1)
    one_per = (cfg.get("rules") or {}).get("one_page_per_category", False)
    result: dict[str, list[tuple[Path, str, str, str]]] = {}

    for cat_key, paths in files_for_date(stamp, cfg).items():
        if one_per and paths:
            paths = [sorted(paths, key=lambda p: p.name)[-1]]

        items = []
        for path in paths:
            try:
                raw = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                log(f"Skip (encoding): {path.name}")
                continue
            body = md_to_notion(raw, path, cat_key=cat_key)
            if len(body.strip()) < min_chars:
                log(f"Skip (empty): {path.name}")
                continue
            chash = file_content_hash(raw)
            pk = page_key(stamp, cat_key, path.name, one_per_category=one_per)
            prev = state.get("pages", {}).get(pk)
            if not force and prev and prev.get("hash") == chash:
                continue
            items.append((path, body, chash, raw))
        if items:
            result[cat_key] = items
    return result


def ensure_day_page(
    registry,
    cfg: dict,
    state: dict,
    stamp: str,
) -> tuple[str, str]:
    if stamp in state.get("days", {}):
        day = state["days"][stamp]
        if isinstance(day, dict):
            return day.get("id", ""), day.get("url", "")
        return day, notion_page_id_to_url(day)

    root = cfg["archive"]["root_page_id"]
    title = f"{stamp} — Daily Archive"
    content = (
        f"## {stamp} 콘텐츠 아카이브\n\n"
        f"자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "### 카테고리 (하위 페이지)\n"
        "| 순서 | 페이지 | 설명 |\n"
        "|------|--------|------|\n"
        "| 1 | 🔗 Unified Context | SEO/AEO/GEO 통합 컨텍스트 |\n"
        "| 2 | 📋 Research Brief | 심층 리서치·분석 |\n"
        "| 3 | 📝 Blog | 3000자 SEO/AEO 아티클 |\n"
        "| 4 | 📸 Instagram Context | 캐러셀 기획 컨텍스트 |\n"
        "| 5 | 💼 LinkedIn Context | 피드 포스트 컨텍스트 |\n\n"
        "> 강의 자료(Lecture)는 `/lecture` 명령으로 별도 생성됩니다.\n"
        "> 미완성·중복 페이지는 **Draft & Incomplete Archive**로 이동됩니다."
    )
    day_id, day_url = create_page(registry, cfg, root, title, content, "📅")
    state.setdefault("days", {})[stamp] = {"id": day_id, "url": day_url}
    save_state(state)
    return day_id, day_url


def archive_date(
    stamp: str,
    *,
    force: bool = False,
    telegram_chat: str = "",
    slack_channel: str = "",
    notify_steps: bool = True,
    notify_mode: str = "full",
    hygiene_only: bool = False,
) -> dict:
    cfg = load_config()
    state = load_state()

    if hygiene_only:
        registry = setup_mcp()
        hygiene_report = run_day_hygiene(registry, cfg, state, stamp)
        save_state(state)
        return {"stamp": stamp, "hygiene": hygiene_report, "count": 0}

    pending = pending_with_content(stamp, cfg, state, force=force)

    show_progress = notify_steps and notify_mode == "full" and (telegram_chat or slack_channel)
    send_final = notify_steps and notify_mode in ("full", "final") and (telegram_chat or slack_channel)

    if show_progress:
        push_notify(
            telegram_chat,
            slack_channel,
            format_progress(1, "Notion 동기화 준비", f"날짜: {stamp}", stamp=stamp),
        )

    if not pending:
        log(f"No new/changed content for {stamp}")
        registry = setup_mcp()
        hygiene_report = None
        if hygiene_enabled(cfg):
            hygiene_report = run_day_hygiene(registry, cfg, state, stamp)
            save_state(state)
        if send_final and not show_progress:
            msg = "⚠️ Notion 동기화: 신규/변경 콘텐츠 없음\n"
            if hygiene_report and hygiene_report.get("duplicates"):
                msg += f"중복 정리: {hygiene_report['duplicates']}건 이동\n"
            msg += f"로컬: ~/hermes-content-studio/content/*/{stamp}_*"
            push_notify(telegram_chat, slack_channel, msg)
        elif show_progress:
            msg = "⚠️ Notion 동기화: 신규/변경 콘텐츠 없음\n"
            if hygiene_report and hygiene_report.get("duplicates"):
                msg += f"중복 정리: {hygiene_report['duplicates']}건 이동\n"
            msg += f"로컬: ~/hermes-content-studio/content/*/{stamp}_*"
            push_notify(telegram_chat, slack_channel, msg)
        return {
            "day_url": state.get("days", {}).get(stamp, {}).get("url", "")
            if isinstance(state.get("days", {}).get(stamp), dict)
            else "",
            "pages": [],
            "count": 0,
            "hygiene": hygiene_report,
        }

    total = sum(len(v) for v in pending.values())
    log(f"Archiving {stamp} ({total} file(s))")

    if show_progress:
        push_notify(
            telegram_chat,
            slack_channel,
            format_progress(2, "Notion 페이지 동기화", f"{total}건", stamp=stamp),
        )

    registry = setup_mcp()
    day_id, day_url = ensure_day_page(registry, cfg, state, stamp)
    synced_pages: list[dict] = []
    count = 0
    one_per = (cfg.get("rules") or {}).get("one_page_per_category", False)
    order_map = {k: v.get("order", 99) for k, v in cfg["categories"].items()}

    for cat_key in sorted(pending.keys(), key=lambda k: order_map.get(k, 99)):
        items = pending[cat_key]
        cat = cfg["categories"][cat_key]
        label = cat["label"]
        icon = cat.get("icon", "📄")

        for path, body, chash, raw in items:
            pk = page_key(stamp, cat_key, path.name, one_per_category=one_per)
            parent_id, tier, qdict = resolve_sync_parent(
                registry, cfg, state, stamp, cat_key, raw, path=path
            )
            if not parent_id:
                if tier == "canonical":
                    parent_id = day_id
                else:
                    log(f"Skip (no parent): {pk}")
                    continue

            content = build_page_body(
                label,
                stamp,
                path,
                body,
                cfg,
                tier=tier,
                quality_score=qdict.get("score"),
                quality_issues=qdict.get("issues"),
            )
            title = f"{label} — {stamp}"
            if tier == "draft":
                title = f"[draft] {title}"

            prev = state.get("pages", {}).get(pk)
            draft_pk = f"{pk}@draft"
            store_key = pk if tier == "canonical" else draft_pk

            if tier == "canonical" and prev and prev.get("id") and (force or prev.get("hash") != chash):
                try:
                    url = update_page_content(registry, cfg, prev["id"], content)
                    page_id = prev["id"]
                except Exception as exc:  # noqa: BLE001
                    log(f"Replace failed, creating new: {exc}")
                    page_id, url = create_page(
                        registry, cfg, parent_id, f"{icon} {title}", content, icon
                    )
            elif tier == "canonical" and prev and prev.get("id") and not force:
                url = prev.get("url", notion_page_id_to_url(prev["id"]))
                page_id = prev["id"]
                log(f"Unchanged (skip): {pk}")
            else:
                page_id, url = create_page(
                    registry, cfg, parent_id, f"{icon} {title}", content, icon
                )

            state.setdefault("pages", {})[store_key] = {
                "id": page_id,
                "url": url,
                "hash": chash,
                "path": str(path),
                "tier": tier,
                "quality_score": qdict.get("score"),
            }
            synced_pages.append(
                {
                    "category": cat_key,
                    "label": label,
                    "icon": icon,
                    "title": title,
                    "url": url,
                    "path": str(path),
                    "tier": tier,
                    "quality_score": qdict.get("score"),
                    "issues": qdict.get("issues", []),
                }
            )
            count += 1

    hygiene_report = None
    if hygiene_enabled(cfg):
        hygiene_report = run_day_hygiene(registry, cfg, state, stamp)

    save_state(state)
    log(f"Done: {count} page(s) archived for {stamp}")

    result = {
        "day_url": day_url,
        "pages": synced_pages,
        "count": count,
        "stamp": stamp,
        "hygiene": hygiene_report,
    }

    dup_count = (hygiene_report or {}).get("duplicates") or 0

    if send_final:
        completion = format_completion(
            stamp,
            synced_pages,
            day_url=day_url or "",
            hygiene_duplicates=dup_count,
        )
        push_notify(telegram_chat, "", completion)
        if slack_channel:
            slack_msg = format_slack_archive_summary(
                stamp,
                synced_pages,
                day_url=day_url or "",
                file_status=file_status_for_stamp(stamp),
            )
            push_notify("", slack_channel, slack_msg)
    elif show_progress:
        push_notify(
            telegram_chat,
            slack_channel,
            format_progress(3, "동기화 검증", f"{count}건 완료", stamp=stamp),
        )
        push_notify(
            telegram_chat,
            slack_channel,
            format_completion(stamp, synced_pages, day_url=day_url or ""),
        )
        if dup_count:
            push_notify(
                telegram_chat,
                slack_channel,
                f"🗂️ 중복 {dup_count}건 → Draft Archive 이동",
            )
        if day_url:
            push_notify(
                telegram_chat,
                slack_channel,
                format_progress(TOTAL_STEPS, "완료", f"Daily Archive:\n{day_url}", stamp=stamp),
            )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive content to Notion")
    parser.add_argument("date", nargs="?", default=date.today().isoformat())
    parser.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-force", action="store_true", help="Skip unchanged files (hash match)")
    parser.add_argument("--hygiene-only", action="store_true", help="Run duplicate cleanup only")
    parser.add_argument("--telegram-chat", default="", help="Telegram chat ID for notifications")
    parser.add_argument("--slack-channel", default="", help="Slack channel ID for notifications")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    parser.add_argument("--no-notify", action="store_true", help="Skip Telegram/Slack notifications")
    parser.add_argument(
        "--notify-final",
        action="store_true",
        help="Send one completion message only (for telegram-post-sync)",
    )
    args = parser.parse_args()

    chat = args.telegram_chat or ""
    slack = args.slack_channel or ""
    notify_mode = "none"
    if not args.no_notify:
        if args.notify_final:
            notify_mode = "final"
        elif chat or slack:
            notify_mode = "full"

    force = not args.no_force

    try:
        result = archive_date(
            args.date,
            force=force,
            telegram_chat=chat,
            slack_channel=slack,
            notify_steps=notify_mode != "none",
            notify_mode=notify_mode,
            hygiene_only=args.hygiene_only,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["count"] >= 0 else 1
    except Exception as exc:  # noqa: BLE001
        log(f"ERROR: {exc}")
        if chat or slack:
            push_notify(chat, slack, f"❌ Notion 동기화 실패\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
