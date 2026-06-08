"""뉴스레터 제목 A/B 자동 스코어링 — Stripo B2B 2026 휴리스틱."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
CONFIG_PATH = WORKDIR / "config" / "newsletter.yaml"

DEFAULT_SPAM_PATTERNS = [
    r"\bfree\b",
    r"\b무료\b",
    r"act\s*now",
    r"지금\s*바로",
    r"!!!+",
    r"\b한정\b",
    r"\b이벤트\b",
]
ALL_CAPS_RE = re.compile(r"\b[A-Z]{4,}\b")
NUMBER_RE = re.compile(r"\d")


def _load_cfg() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    import yaml

    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def subject_limits(cfg: dict | None = None) -> tuple[int, int, int]:
    """max_chars, ideal_lo, ideal_hi."""
    c = cfg or _load_cfg()
    bench = c.get("benchmarks") or {}
    scoring = c.get("scoring") or {}
    max_c = int(bench.get("subject_max_chars", 50))
    ideal = scoring.get("ideal_subject_chars") or [28, 45]
    return max_c, int(ideal[0]), int(ideal[1])


@dataclass
class SubjectScore:
    text: str
    score: int
    rank: int = 0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "score": self.score,
            "rank": self.rank,
            "chars": len(self.text),
            "reasons": self.reasons,
        }


def score_subject_line(text: str, cfg: dict | None = None) -> SubjectScore:
    """결정적 휴리스틱 — 오픈율 방향성 (MPP 이후 CTOR과 병행)."""
    c = cfg or _load_cfg()
    max_c, ideal_lo, ideal_hi = subject_limits(c)
    spam_patterns = (c.get("scoring") or {}).get("spam_patterns") or DEFAULT_SPAM_PATTERNS
    line = text.strip().strip("`")
    reasons: list[str] = []
    score = 50
    n = len(line)

    if ideal_lo <= n <= ideal_hi:
        score += 18
        reasons.append(f"길이 최적({ideal_lo}–{ideal_hi}자)")
    elif n <= max_c:
        score += 10
        reasons.append(f"길이 양호(≤{max_c}자)")
    else:
        score -= 25
        reasons.append(f"{max_c}자 초과 — 모바일 잘림 위험")

    if "?" in line or "？" in line:
        score += 14
        reasons.append("질문형 — Stripo +11pp opens")
    if NUMBER_RE.search(line):
        score += 6
        reasons.append("숫자·구체성")
    if re.search(r"AX|AEO|B2B|AI", line, re.I):
        score += 5
        reasons.append("B2B 키워드 명시")

    for pat in spam_patterns:
        if re.search(pat, line, re.I):
            score -= 18
            reasons.append(f"스팸 신호: {pat}")
            break
    if ALL_CAPS_RE.search(line):
        score -= 15
        reasons.append("대문자 연속 — 스팸 필터 위험")

    if line.startswith("["):
        score += 3
        reasons.append("날짜/태그 프리픽스 — 인지성")

    score = max(0, min(100, score))
    return SubjectScore(text=line, score=score, reasons=reasons)


def rank_subjects(candidates: list[str], cfg: dict | None = None) -> list[SubjectScore]:
    c = cfg or _load_cfg()
    scored = [score_subject_line(line, c) for line in candidates if line.strip()]
    scored.sort(key=lambda s: (-s.score, len(s.text)))
    for i, s in enumerate(scored, 1):
        s.rank = i
    return scored


def min_winner_score(cfg: dict | None = None) -> int:
    c = cfg or _load_cfg()
    return int((c.get("scoring") or {}).get("min_winner_score", 40))


def save_subject_scores(stamp: str, ranked: list[SubjectScore], cfg: dict | None = None) -> Path:
    out_dir = WORKDIR / "content" / "newsletter"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{stamp}_newsletter_subject-scores.json"
    payload = {
        "stamp": stamp,
        "winner": ranked[0].to_dict() if ranked else None,
        "candidates": [s.to_dict() for s in ranked],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def format_subject_ab_block(ranked: list[SubjectScore]) -> list[str]:
    lines = ["**제목 후보 (A/B, ≤50자) — 자동 스코어:**", ""]
    lines.append("| Rank | Score | 제목 | 근거 |")
    lines.append("|-----:|------:|------|------|")
    for s in ranked:
        star = " ⭐" if s.rank == 1 else ""
        reason = ", ".join(s.reasons[:2])
        lines.append(f"| {s.rank}{star} | {s.score} | {s.text} | {reason} |")
    if ranked:
        lines.extend(
            [
                "",
                f"**권장 제목:** `{ranked[0].text}` (score {ranked[0].score})",
            ]
        )
    return lines
