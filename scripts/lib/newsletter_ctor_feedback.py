"""CTOR 실측 → 제목 스코어링 피드백 (결정적).

평가용 시드(`--seed` / `p4-eval-seed`)는 학습에서 제외하고, 실측이 부족하면
정적 기본 가중치로 남는다 (R27 · AE8).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lib.newsletter_ctor import (
    _ctor_targets,
    is_seed_record,
    learning_config,
    list_records,
)

WORKDIR = Path(__file__).resolve().parents[2]
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


def _weight_scale(cfg: dict | None = None) -> tuple[int, int, int]:
    w = (learning_config(cfg).get("weights") or {})
    return int(w.get("strong", 8)), int(w.get("good", 4)), int(w.get("weak", -6))


def _bucket(avg: float, lo: float, hi: float, cfg: dict | None = None) -> int:
    strong, good, weak = _weight_scale(cfg)
    if avg >= hi:
        return strong
    if avg >= lo:
        return good
    if avg < lo - 2:
        return weak
    return 0


def _write(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        FEEDBACK_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
    return payload


def compute_ctor_feedback(*, min_records: int | None = None) -> dict[str, Any]:
    """실측 CTOR 기록에서 trait·패턴별 가중치 도출 (시드 제외)."""
    all_records = list_records(limit=20)
    seeds = [r for r in all_records if is_seed_record(r)]
    records = [r for r in all_records if not is_seed_record(r)]
    lo, hi, _, _ = _ctor_targets()
    threshold = (
        int(min_records)
        if min_records is not None
        else int(learning_config().get("min_real_records", 3))
    )
    # 저조한 패턴에도 음수 가중치를 주려면 healthy 기록만이 아니라 실측 전체를 본다
    usable = [r for r in records if r.get("subject")]

    if len(usable) < threshold:
        reason = (
            "seed_only" if seeds and not records else f"insufficient_records ({len(usable)}<{threshold})"
        )
        return _write(
            {
                "version": 2,
                "applied": False,
                "reason": reason,
                "weights": {},
                "pattern_weights": {},
                "sample_size": len(usable),
                "excluded_seed_count": len(seeds),
                "min_real_records": threshold,
            }
        )

    trait_hits: dict[str, list[float]] = {}
    pattern_hits: dict[str, list[float]] = {}
    for row in usable:
        ctor = float(row.get("ctor_pct") or 0)
        for name, hit in _subject_traits(str(row.get("subject") or "")).items():
            if hit:
                trait_hits.setdefault(name, []).append(ctor)
        pid = str(row.get("pattern_id") or "").strip()
        if pid:
            pattern_hits.setdefault(pid, []).append(ctor)

    weights = {
        name: _bucket(sum(v) / len(v), lo, hi)
        for name, v in trait_hits.items()
        if v and _bucket(sum(v) / len(v), lo, hi)
    }
    # 패턴은 표본이 너무 적으면 반영하지 않음 (R26 — 한 번에 한 변수)
    min_per_pattern = int((learning_config().get("pattern") or {}).get("min_records_per_pattern", 2))
    pattern_weights = {
        pid: _bucket(sum(v) / len(v), lo, hi)
        for pid, v in pattern_hits.items()
        if len(v) >= min_per_pattern and _bucket(sum(v) / len(v), lo, hi)
    }

    return _write(
        {
            "version": 2,
            "applied": bool(weights or pattern_weights),
            "ctor_target_lo": lo,
            "ctor_target_hi": hi,
            "weights": weights,
            "pattern_weights": pattern_weights,
            "sample_size": len(usable),
            "healthy_count": sum(1 for r in usable if r.get("ctor_health") == "healthy"),
            "excluded_seed_count": len(seeds),
            "min_real_records": threshold,
            "trait_avgs": {k: round(sum(v) / len(v), 2) for k, v in trait_hits.items()},
            "pattern_avgs": {k: round(sum(v) / len(v), 2) for k, v in pattern_hits.items()},
        }
    )


def load_ctor_feedback() -> dict[str, Any]:
    if not FEEDBACK_PATH.exists():
        return compute_ctor_feedback()
    try:
        data = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
        # v1 캐시는 시드를 학습했을 수 있으므로 재계산
        if isinstance(data, dict) and int(data.get("version") or 1) >= 2:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return compute_ctor_feedback()


def apply_ctor_feedback_bonus(
    text: str, feedback: dict[str, Any] | None = None
) -> tuple[int, list[str]]:
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


def pattern_bonus(pattern_id: str, feedback: dict[str, Any] | None = None) -> int:
    """제목 패턴별 실측 가중치 (R26)."""
    fb = feedback or load_ctor_feedback()
    if not fb.get("applied"):
        return 0
    return int((fb.get("pattern_weights") or {}).get(str(pattern_id), 0))


def preferred_pattern_ids(feedback: dict[str, Any] | None = None) -> list[str]:
    """가중치 높은 순 패턴 목록 — 실측 없으면 빈 목록."""
    fb = feedback or load_ctor_feedback()
    if not fb.get("applied"):
        return []
    pw = fb.get("pattern_weights") or {}
    return [pid for pid, w in sorted(pw.items(), key=lambda kv: -int(kv[1])) if int(w) > 0]
