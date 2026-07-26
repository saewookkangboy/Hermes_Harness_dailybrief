"""SKILL.md STABLE / LEARNED 파서 및 안전 쓰기기.

불변식:
  1. STABLE 섹션은 이 모듈을 통해 절대 수정되지 않는다.
  2. LEARNED 엔트리는 삭제되지 않는다 (tombstone만).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import ledger
from .token_budget import load_yaml_flat

STUDIO = ledger.STUDIO
TOMBSTONE = "⚠DEPRECATED"

ENTRY_RE = re.compile(
    r"^###\s+(?P<id>L-\d{4})\s*"
    r"\[helpful:(?P<helpful>\d+)\s+harmful:(?P<harmful>\d+)\]\s*"
    r"(?:since\s+(?P<since>\d{4}-\d{2}-\d{2}))?"
    r"(?P<tomb>\s*⚠DEPRECATED)?\s*$",
    re.MULTILINE,
)


class StableWriteError(RuntimeError):
    """자동화가 STABLE 섹션을 수정하려 했다."""


@dataclass
class Entry:
    id: str
    helpful: int
    harmful: int
    since: str
    body: str
    deprecated: bool = False
    expected: dict = field(default_factory=dict)

    def render(self) -> str:
        tomb = f"  {TOMBSTONE}" if self.deprecated else ""
        return (
            f"### {self.id} [helpful:{self.helpful} harmful:{self.harmful}] "
            f"since {self.since}{tomb}\n{self.body.rstrip()}\n"
        )


def skills_root() -> Path:
    override = os.environ.get("HERMES_SKILLS_ROOT", "").strip()
    if override:
        return Path(override)
    return STUDIO / "skills"


def skill_path(skill_key: str) -> Path:
    idx = load_yaml_flat(STUDIO / "config" / "skill-index.yaml")
    spec = (idx.get("skills") or {}).get(skill_key)
    if not isinstance(spec, dict):
        raise KeyError(f"unknown skill key: {skill_key}")
    rel = Path(spec["path"])
    root = skills_root()
    if rel.parts and rel.parts[0] == "skills":
        return root.joinpath(*rel.parts[1:]) / "SKILL.md"
    return STUDIO / rel / "SKILL.md"


def split_sections(md: str) -> tuple[str, str]:
    """(stable_part, learned_part). LEARNED 헤더가 없으면 learned=''."""
    m = re.search(r"^##\s+LEARNED\s*$", md, re.MULTILINE)
    if not m:
        return md.rstrip() + "\n", ""
    return md[: m.start()].rstrip() + "\n", md[m.end() :].lstrip("\n")


def parse_entries(learned: str) -> list[Entry]:
    entries: list[Entry] = []
    matches = list(ENTRY_RE.finditer(learned))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(learned)
        entries.append(
            Entry(
                id=m.group("id"),
                helpful=int(m.group("helpful")),
                harmful=int(m.group("harmful")),
                since=m.group("since") or "1970-01-01",
                body=learned[m.end() : end].strip(),
                deprecated=bool(m.group("tomb")),
            )
        )
    return entries


def next_id(entries: list[Entry]) -> str:
    n = max((int(e.id.split("-")[1]) for e in entries), default=0) + 1
    return f"L-{n:04d}"


def render(stable: str, entries: list[Entry]) -> str:
    body = "\n".join(e.render() for e in entries)
    return (
        f"{stable}\n## LEARNED\n"
        f"<!-- Curator 전용. 사람이 직접 편집하지 말 것. -->\n\n{body}"
    )


def write(
    skill_key: str,
    stable: str,
    entries: list[Entry],
    *,
    original_stable: str,
) -> None:
    """STABLE 변경 시도를 차단한 뒤 파일을 쓴다."""
    if stable.strip() != original_stable.strip():
        raise StableWriteError(
            f"{skill_key}: STABLE 섹션 변경 시도가 차단되었습니다. "
            "브랜드 규칙은 사람만 편집합니다."
        )
    skill_path(skill_key).write_text(render(stable, entries), encoding="utf-8")


def load(skill_key: str) -> tuple[str, list[Entry]]:
    md = skill_path(skill_key).read_text(encoding="utf-8")
    stable, learned = split_sections(md)
    return stable, parse_entries(learned)


def top_learned(
    entries: list[Entry],
    max_entries: int | None,
    *,
    include_deprecated: bool = False,
) -> str:
    """로드 시점 제한. 파일에서 지우는 것이 아니라 컨텍스트에서 뺀다."""
    pool = [e for e in entries if include_deprecated or not e.deprecated]
    pool.sort(key=lambda e: (e.helpful - e.harmful, e.since), reverse=True)
    if max_entries:
        pool = pool[:max_entries]
    return "\n".join(e.render() for e in pool)


def health(entries: list[Entry]) -> dict:
    return {
        "total": len(entries),
        "active": sum(1 for e in entries if not e.deprecated),
        "deprecated": sum(1 for e in entries if e.deprecated),
        "net_positive": sum(
            1 for e in entries if not e.deprecated and e.helpful > e.harmful
        ),
        "unverified": sum(
            1 for e in entries if e.helpful == 0 and e.harmful == 0 and not e.deprecated
        ),
    }
