"""CTOR 실측 → 제목 스코어링 피드백 (결정적)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lib.newsletter_ctor import _ctor_targets, list_records

WORKDIR = Path.home() / "hermes-content-studio"
FEEDBACK_PATH = WORKDIR / ".harness" / "newsletter-ctor-feedback.json"

QUESTION_RE = re.compile(r"[?？]")
NUMBER_RE = re.compile(r"\d")


def _subject_traits(subject: str) -> dict[str, bool]:
    s = subject.strip()
    return {
        "question": bool(QUESTION_RE.search(s)),
        "number": bool(NUMBER_RE.search(s)),
        "bracket_prefix": s.startswith("["),
        "b2b_kw": bool(re.search(r"AX|AEO|B2B|AI", s, re.I)),
        "short_ideal": 28 <= len(s) <= 45,
    }


def compute_ctor_feedback(*, min_records: int = 2) -> dict[str, Any]:
    """과거 CTOR 기록에서 trait별 가중치 도출."""
    records = list_records(limit=20)
    lo, hi, _, _ = _ctor_targets()
    healthy = [r for r in records if r.get("ctor_health") == "healthy" and r.get("subject")]
    if len(healthy) < min_records:
        return {
            "version": 1,
            "applied": False,
            "reason": f"insufficient_records ({len(healthy)}<{min_records})",
            "weights": {},
            "sample_size": len(healthy),
        }

    trait_hits: dict[str, list[float]] = {}
    for row in healthy:
        traits = _subject_traits(str(row.get("subject") or ""))
        ctor = float(row.get("ctor_pct") or 0)
        for name, hit in traits.items():
            if hit:
                trait_hits.setdefault(name, []).append(ctor)

    weights: dict[str, int] = {}
    for name, vals in trait_hits.items():
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        if avg >= hi:
            weights[name] = 8
        elif avg >= lo:
            weights[name] = 4
        elif avg < lo - 2:
            weights[name] = -6

    payload = {
        "version": 1,
        "applied": bool(weights),
        "ctor_target_lo": lo,
        "ctor_target_hi": hi,
        "weights": weights,
        "sample_size": len(healthy),
        "trait_avgs": {k: round(sum(v) / len(v), 2) for k, v in trait_hits.items()},
    }
    try:
        FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        FEEDBACK_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return payload


def load_ctor_feedback() -> dict[str, Any]:
    if not FEEDBACK_PATH.exists():
        return compute_ctor_feedback()
    try:
        data = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return compute_ctor_feedback()


def apply_ctor_feedback_bonus(text: str, feedback: dict[str, Any] | None = None) -> tuple[int, list[str]]:
    """제목 trait에 CTOR 피드백 가중치 적용 — (bonus, reasons)."""
    fb = feedback or load_ctor_feedback()
    if not fb.get("applied"):
        return 0, []
    weights = fb.get("weights") or {}
    traits = _subject_traits(text)
    bonus = 0
    reasons: list[str] = []
    for name, weight in weights.items():
        if traits.get(name) and weight:
            bonus += int(weight)
            reasons.append(f"CTOR+{name}({weight:+d})")
    return bonus, reasons
