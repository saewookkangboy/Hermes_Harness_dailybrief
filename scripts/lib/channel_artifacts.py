"""채널 산출물 canonical 선택 — unified-context SoT · 중복 slug 정리."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
STALE_ROOT = WORKDIR / "content" / "_stale"

_CHANNEL_PATTERNS: dict[str, str] = {
    "blog": "content/blog/{stamp}_blog_{slug}.html",
    "instagram": "content/instagram/{stamp}_instagram_{slug}.md",
    "linkedin": "content/linkedin/{stamp}_linkedin_{slug}.md",
    "newsletter": "content/newsletter/{stamp}_newsletter_{slug}.md",
    "newsletter_html": "content/newsletter/{stamp}_newsletter_{slug}.html",
}


def _slug_from_unified(stamp: str) -> str | None:
    unified = WORKDIR / "content" / "packages" / f"{stamp}_unified-context.md"
    if not unified.exists():
        return None
    text = unified.read_text(encoding="utf-8")
    # packages/blog-article.md 또는 channel/{stamp}_blog_{slug}.html
    m = re.search(
        rf"content/(?:blog|instagram|linkedin|newsletter)/{re.escape(stamp)}_[a-z]+_([a-z0-9-]+)\.",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1)
    m = re.search(rf"{re.escape(stamp)}_blog_([a-z0-9-]+)\.html", text, re.IGNORECASE)
    return m.group(1) if m else None


def canonical_slug(stamp: str) -> str | None:
    """unified-context → blog 패키지 경로 순으로 canonical slug 추론."""
    slug = _slug_from_unified(stamp)
    if slug:
        return slug
    blog_pkg = WORKDIR / "content" / "packages" / f"{stamp}_blog-article.md"
    if blog_pkg.exists():
        matches = sorted(WORKDIR.glob(f"content/blog/{stamp}_blog_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        if matches:
            stem = matches[0].stem
            prefix = f"{stamp}_blog_"
            if stem.startswith(prefix):
                return stem[len(prefix) :]
    return None


def glob_channel_matches(stamp: str, channel: str) -> list[Path]:
    patterns = {
        "blog": f"content/blog/{stamp}_blog_*.html",
        "instagram": f"content/instagram/{stamp}_instagram_*.md",
        "linkedin": f"content/linkedin/{stamp}_linkedin_*.md",
        "newsletter": f"content/newsletter/{stamp}_newsletter_*.md",
        "newsletter_html": f"content/newsletter/{stamp}_newsletter_*.html",
    }
    pattern = patterns.get(channel)
    if not pattern:
        return []
    return sorted(WORKDIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)


def glob_channel_artifact(stamp: str, channel: str) -> Path | None:
    """canonical slug 우선, 없으면 최신 mtime."""
    slug = canonical_slug(stamp)
    if slug and channel in _CHANNEL_PATTERNS:
        candidate = WORKDIR / _CHANNEL_PATTERNS[channel].format(stamp=stamp, slug=slug)
        if candidate.exists():
            return candidate
    matches = glob_channel_matches(stamp, channel)
    return matches[0] if matches else None


def glob_linkedin_feed(stamp: str) -> Path | None:
    """Feed 포스트 — repurpose `-iN` variant 우선 (quality_auditor 호환)."""
    matches = list(WORKDIR.glob(f"content/linkedin/{stamp}_linkedin_*.md"))
    if not matches:
        return None

    slug = canonical_slug(stamp)
    if slug:
        preferred = WORKDIR / f"content/linkedin/{stamp}_linkedin_{slug}.md"
        if preferred.exists():
            matches = [preferred] + [p for p in matches if p != preferred]

    def _rank(p: Path) -> tuple[int, float]:
        m = re.search(r"-i(\d+)$", p.stem)
        idx = int(m.group(1)) if m else 0
        return (idx, p.stat().st_mtime)

    return max(matches, key=_rank)


def stale_channel_artifacts(stamp: str) -> list[Path]:
    """canonical이 아닌 동일 stamp 채널 산출물."""
    slug = canonical_slug(stamp)
    if not slug:
        return []
    stale: list[Path] = []
    for channel in ("blog", "instagram", "linkedin", "newsletter", "newsletter_html"):
        for path in glob_channel_matches(stamp, channel):
            if slug not in path.name:
                stale.append(path)
    return stale


def archive_stale_artifacts(stamp: str, *, dry_run: bool = False) -> list[str]:
    """중복 slug 산출물을 content/_stale/{stamp}/ 로 이동."""
    moved: list[str] = []
    dest_root = STALE_ROOT / stamp
    for path in stale_channel_artifacts(stamp):
        dest = dest_root / path.name
        if dry_run:
            moved.append(f"would move {path.name} → _stale/{stamp}/{path.name}")
            continue
        dest_root.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        shutil.move(str(path), str(dest))
        moved.append(f"moved {path.name} → _stale/{stamp}/{path.name}")
    return moved
