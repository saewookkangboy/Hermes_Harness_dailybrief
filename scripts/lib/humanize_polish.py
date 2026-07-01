"""HERMES_HUMANIZE=1 — 채널 산출물 결정적 문체 재정렬 + 선택 LLM polish."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from lib.content_quality import (
    build_linkedin_post_text,
    is_garbage_korean_title,
    parse_brief,
    polish_display_title,
)
from lib.brief_quality import polish_brief_prose
from lib.content_quality_config import humanize_llm_timeout, humanize_llm_use_codex
from lib.hermes_cost import parse_run_usage, snapshot_sessions_map
from lib.humanize_korean import humanize, humanize_linkedin_post
from lib.newsletter_complete import audit_newsletter_md
from lib.voice_style_audit import audit_instagram_caption, audit_linkedin_post_body

WORKDIR = Path.home() / "hermes-content-studio"
SCRIPTS = WORKDIR / "scripts"


@dataclass
class PolishResult:
    stamp: str
    channels: list[str] = field(default_factory=list)
    llm_attempted: bool = False
    warnings: list[str] = field(default_factory=list)


def _glob_one(pattern: str) -> Path | None:
    matches = sorted(WORKDIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _polish_linkedin_file(path: Path, stamp: str) -> bool:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 1)
    body = parts[0].rstrip()
    tail = f"---{parts[1]}" if len(parts) > 1 else ""

    brief_path = WORKDIR / "content" / "research" / f"{stamp}_brief.md"
    if brief_path.exists():
        summary, insights = parse_brief(brief_path.read_text(encoding="utf-8"))
        body = build_linkedin_post_text(summary, insights)
    else:
        body = humanize_linkedin_post(body).text

    issues = audit_linkedin_post_body(body)
    if issues:
        return False
    path.write_text(f"{body}\n\n{tail}".rstrip() + "\n", encoding="utf-8")
    return True


def _polish_instagram_caption(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"(## 캡션[^\n]*\n\n)(.+?)(\n\n---)", text, re.S)
    if not m:
        return False
    prefix, caption, suffix = m.group(1), m.group(2).strip(), m.group(3)
    lines: list[str] = []
    for line in caption.splitlines():
        raw = line.strip()
        if not raw:
            lines.append(line)
            continue
        if raw.startswith(("📌", "💡", "👉")):
            lines.append(line)
            continue
        if raw.startswith("💬"):
            core = re.sub(r"^💬\s*", "", raw)
            polished = humanize(core, genre="instagram").text
            lines.append(f"💬 {polished}")
            continue
        if raw.startswith("→"):
            polished = humanize(raw, genre="instagram").text
            if not polished.rstrip().endswith((".", "!", "?", "。")):
                polished = f"{polished.rstrip()}."
            lines.append(polished)
        else:
            lines.append(humanize(raw, genre="instagram").text)
    new_caption = "\n".join(lines)
    if audit_instagram_caption(new_caption):
        return False
    new_text = text[: m.start()] + prefix + new_caption + suffix + text[m.end() :]
    path.write_text(new_text, encoding="utf-8")
    return True


def _polish_brief_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    changed = False

    m = re.search(r"(## Executive Summary\n)(.+?)(\n\n##)", text, re.S)
    if m:
        polished = polish_brief_prose(m.group(2).strip(), max_chars=480, max_sentences=4)
        if polished != m.group(2).strip():
            text = text[: m.start(2)] + polished + text[m.end(2) :]
            changed = True

    def repl_field(match: re.Match[str]) -> str:
        nonlocal changed
        label = match.group(1)
        body = match.group(2).strip()
        max_c = 300 if label == "Insight 도출" else 220
        polished = polish_brief_prose(body, max_chars=max_c, max_sentences=3)
        if polished != body:
            changed = True
        return f"- **{label}:** {polished}"

    new_text = re.sub(
        r"- \*\*(마케터 관점|Insight 도출|활용 방법):\*\* (.+)$",
        repl_field,
        text,
        flags=re.M,
    )
    if new_text != text:
        text = new_text
        changed = True

    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


def _fix_newsletter_title(title: str) -> str:
    fixed = polish_display_title((title or "").strip())
    if is_garbage_korean_title(fixed):
        return "2026 AI·마케팅 실무 인사이트"
    return fixed


def _polish_newsletter_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    changed = False

    def repl_tldr(m: re.Match[str]) -> str:
        nonlocal changed
        title = _fix_newsletter_title(m.group(1))
        body = humanize(m.group(2).lstrip(), genre="linkedin").text
        if title != m.group(1).strip():
            changed = True
        return f"- **{title}** — {body}"

    new_text = re.sub(r"^- \*\*([^*]+)\*\* — (.+)$", repl_tldr, text, flags=re.M)

    def repl_mod(m: re.Match[str]) -> str:
        nonlocal changed
        title = _fix_newsletter_title(m.group(2))
        if title != m.group(2).strip():
            changed = True
        return f"{m.group(1)}**{title}**{m.group(3)}"

    new_text = re.sub(r"^(### \d+\.\s*)\*\*([^*]+)\*\*(.*)$", repl_mod, new_text, flags=re.M)

    def repl_teaser(m: re.Match[str]) -> str:
        nonlocal changed
        title = _fix_newsletter_title(m.group(1))
        if title != m.group(1).strip():
            changed = True
        return f"**다음 호 예고:** {title}{m.group(2)}"

    new_text = re.sub(r"^\*\*다음 호 예고:\*\* (.+?)( — .+)$", repl_teaser, new_text, flags=re.M)

    issues = audit_newsletter_md(new_text)
    if issues:
        return False
    if changed:
        path.write_text(new_text, encoding="utf-8")
    return changed


def _polish_blog_article(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    out_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("#") or line.startswith("|") or line.startswith("- **"):
            out_lines.append(line)
            continue
        if line.strip() and not line.startswith("```"):
            out_lines.append(humanize(line, genre="blog").text)
        else:
            out_lines.append(line)
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return True


def _run_llm_polish(stamp: str, result: PolishResult) -> None:
    from lib.harness import append_cost
    from lib.loop_budget import check_loop_budget

    budget = check_loop_budget()
    if not budget.ok:
        result.warnings.append(f"LLM polish skipped — budget: {budget.detail}")
        return

    blog = WORKDIR / f"content/packages/{stamp}_blog-article.md"
    li = _glob_one(f"content/linkedin/{stamp}_linkedin_*.md")
    ig = _glob_one(f"content/instagram/{stamp}_instagram_*.md")
    nl = _glob_one(f"content/newsletter/{stamp}_newsletter_*.md")
    channel_map = {
        "blog": blog,
        "linkedin": li,
        "instagram": ig,
        "newsletter": nl,
    }
    allow_raw = os.environ.get("HERMES_HUMANIZE_LLM_CHANNELS", "blog,linkedin,instagram")
    allow = {c.strip() for c in allow_raw.split(",") if c.strip()}

    targets: list[tuple[str, Path]] = []
    for channel, path in channel_map.items():
        if channel in allow and path and path.exists():
            targets.append((channel, path))
    if not targets:
        result.warnings.append("LLM polish 대상 없음")
        return

    result.llm_attempted = True
    hermes_run = SCRIPTS / "hermes-run.sh"
    if not hermes_run.exists():
        result.warnings.append("hermes-run.sh 없음 — LLM polish 생략")
        return

    for channel, path in targets:
        channel_timeout = humanize_llm_timeout(channel)
        sessions_before = snapshot_sessions_map()
        log_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".log", delete=False, prefix="hermes-humanize-"
            ) as tf:
                log_path = Path(tf.name)
            run_env = {**os.environ, "HERMES_RUN_LOG": str(log_path)}
            if humanize_llm_use_codex():
                run_env["HERMES_USE_CODEX"] = "1"
            proc = subprocess.run(
                [
                    str(hermes_run),
                    f"humanize-korean: {path} {channel} 문체 윤문. 의미·URL·구조 유지.",
                    "--skills",
                    "humanize-korean",
                    "-t",
                    "hermes-cli",
                ],
                cwd=str(WORKDIR),
                capture_output=True,
                text=True,
                check=False,
                timeout=channel_timeout,
                env=run_env,
            )
        except subprocess.TimeoutExpired:
            result.warnings.append(f"LLM {channel} polish timeout ({channel_timeout}s)")
            if log_path:
                log_path.unlink(missing_ok=True)
            continue

        log_text = ""
        if log_path and log_path.exists():
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            log_path.unlink(missing_ok=True)

        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "")[-240:]
            result.warnings.append(f"LLM {channel} polish exit {proc.returncode}: {tail}")
            continue
        combined = "\n".join(filter(None, [proc.stdout, proc.stderr, log_text]))
        usage = parse_run_usage(combined, sessions_before=sessions_before, prefer_delta=True)
        append_cost(
            {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "path": "HERMES_HUMANIZE_LLM",
                "channel": channel,
                "stamp": stamp,
                "tokens": int(usage["tokens"]),
                "usd": float(usage["usd"]),
                "note": f"hermes-run humanize-korean codex={humanize_llm_use_codex()} delta=1",
            }
        )


def run_humanize_polish(stamp: str, *, use_llm: bool = False) -> PolishResult:
    """결정적 humanize 재적용 · use_llm 시 hermes-run humanize-korean (non-blocking)."""
    result = PolishResult(stamp=stamp)

    brief = WORKDIR / f"content/research/{stamp}_brief.md"
    if brief.exists() and _polish_brief_file(brief):
        result.channels.append("brief")

    blog = WORKDIR / f"content/packages/{stamp}_blog-article.md"
    if blog.exists() and _polish_blog_article(blog):
        result.channels.append("blog")

    li = _glob_one(f"content/linkedin/{stamp}_linkedin_*.md")
    if li and _polish_linkedin_file(li, stamp):
        result.channels.append("linkedin")

    ig = _glob_one(f"content/instagram/{stamp}_instagram_*.md")
    if ig and _polish_instagram_caption(ig):
        result.channels.append("instagram")

    nl = _glob_one(f"content/newsletter/{stamp}_newsletter_*.md")
    if nl and _polish_newsletter_file(nl):
        result.channels.append("newsletter")

    if use_llm:
        _run_llm_polish(stamp, result)

    if not result.channels:
        result.warnings.append("polish 대상 채널 없음")
    return result
