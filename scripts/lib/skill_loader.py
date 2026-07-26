"""스킬 progressive disclosure — Level 1/2/3 로더."""
from __future__ import annotations

from pathlib import Path

from . import ledger
from .token_budget import load_yaml_flat

STUDIO = ledger.STUDIO
INDEX = STUDIO / "config" / "skill-index.yaml"


def estimate_tokens(text: str) -> int:
    """한국어 혼용 텍스트의 보수적 추정: 문자수 / 2.2"""
    return int(len(text) / 2.2) + 1


def level1() -> str:
    """항상 로드되는 인덱스. 1줄 트리거만."""
    cfg = load_yaml_flat(INDEX)
    lines = ["# 사용 가능 스킬 (상세는 필요 시 SKILL.md 로드)"]
    for name, spec in (cfg.get("skills") or {}).items():
        if isinstance(spec, dict):
            lines.append(f"- {name}: {spec.get('trigger', '')}")
    return "\n".join(lines)


def level2(
    skill_name: str,
    *,
    include_learned: bool = True,
    learned_max: int | None = None,
) -> str:
    """매칭된 스킬의 SKILL.md 본문. F4의 STABLE/LEARNED 정책을 존중."""
    cfg = load_yaml_flat(INDEX)
    spec = (cfg.get("skills") or {}).get(skill_name)
    if not isinstance(spec, dict):
        raise KeyError(f"unknown skill: {skill_name}")
    md = (STUDIO / spec["path"] / "SKILL.md").read_text(encoding="utf-8")

    if include_learned and learned_max is None:
        return md

    from .playbook import split_sections, top_learned

    stable, learned = split_sections(md)
    if not include_learned:
        return stable
    from .playbook import parse_entries

    return stable + "\n\n## LEARNED\n" + top_learned(parse_entries(learned), learned_max)


def level2_for_path(skill_name: str, path_kind: str = "local") -> str:
    """path_kind: 'local' (Ollama) | 'cloud' (OpenRouter/claude-design)"""
    from .playbook import load, top_learned

    cfg = load_yaml_flat(STUDIO / "config" / "harness.yaml")
    pb = cfg.get("playbook") or {}
    if pb.get("mode") == "stable":
        stable, _ = load(skill_name)
        return stable
    policy = pb.get(f"{path_kind}_path") or {}
    stable, entries = load(skill_name)
    if not policy.get("include_learned", True):
        return stable
    max_n = policy.get("learned_max_entries")
    if max_n == 0:
        max_n = None  # 0 = 전체
    learned = top_learned(
        entries,
        max_n,
        include_deprecated=bool(policy.get("include_deprecated", False)),
    )
    marker = ""
    if policy.get("cache_breakpoint_after") == "STABLE":
        marker = "\n<!-- CACHE_BREAKPOINT -->\n"
    return f"{stable}{marker}\n## LEARNED\n{learned}\n"


def verify_level1_cap() -> tuple[bool, int, int]:
    cfg = load_yaml_flat(STUDIO / "config" / "harness.yaml")
    cap = ((cfg.get("skills") or {}).get("loading") or {}).get("level1_token_cap", 400)
    est = estimate_tokens(level1())
    return est <= cap, est, cap


if __name__ == "__main__":
    ok, est, cap = verify_level1_cap()
    print(level1())
    print(f"\n[level1] est={est} tokens cap={cap} → {'OK' if ok else 'OVER'}")
    raise SystemExit(0 if ok else 1)
