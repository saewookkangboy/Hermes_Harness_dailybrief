"""Convert local Markdown/HTML to Notion-flavored Markdown."""
from __future__ import annotations

import html
import re
from pathlib import Path

TEXT_EXTENSIONS = {".md", ".html", ".htm", ".txt"}
BINARY_EXTENSIONS = {".pptx", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip"}

MAX_BODY = 48000  # Notion page limit safety margin


def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return False
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return path.suffix.lower() not in BINARY_EXTENSIONS


def html_to_notion_markdown(text: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)

    def repl_heading(m: re.Match) -> str:
        level = int(m.group(1))
        content = strip_tags(m.group(2)).strip()
        prefix = "#" * min(level + 1, 3)  # h1→## (title is page property)
        return f"\n{prefix} {content}\n"

    text = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", repl_heading, text, flags=re.S | re.I)
    text = re.sub(r"<li[^>]*>", "\n- ", text, flags=re.I)
    text = re.sub(r"</li>", "", text, flags=re.I)
    text = re.sub(r"<blockquote[^>]*>", "\n> ", text, flags=re.I)
    text = re.sub(r"</blockquote>", "\n", text, flags=re.I)
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.S | re.I)
    text = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", text, flags=re.S | re.I)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.S | re.I)
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.S | re.I)
    text = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", text, flags=re.S | re.I)
    text = re.sub(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", r"[\2](\1)", text, flags=re.S | re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return normalize_markdown(text)


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def normalize_markdown(text: str) -> str:
    """Normalize markdown for Notion: preserve structure, fix common issues."""
    lines = text.splitlines()
    out: list[str] = []
    in_fence = False

    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue

        # Ensure headings have blank line before
        if re.match(r"^#{1,3}\s", line) and out and out[-1].strip():
            out.append("")
        out.append(line.rstrip())

    text = "\n".join(out)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def md_to_notion(text: str, source_path: Path, *, cat_key: str = "") -> str:
    if cat_key:
        from lib.notion_templates import normalize_category_markdown

        text = normalize_category_markdown(text, cat_key, source_path)

    if source_path.suffix.lower() in {".html", ".htm"}:
        text = html_to_notion_markdown(text)
    else:
        text = normalize_markdown(text)

    if len(text) > MAX_BODY:
        text = text[:MAX_BODY] + "\n\n… (본문 일부 생략 — 로컬 파일 전체 참조)"
    return text.strip()


def file_content_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
