"""Reflector — 결정적 신호 수집 + LLM 1회로 delta 생성."""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from . import ledger
from .token_budget import load_yaml_flat

STUDIO = ledger.STUDIO
HARNESS = STUDIO / ".harness"
DELTAS = HARNESS / "deltas"


def collect(days: int = 7) -> dict:
    since = (date.today() - timedelta(days=days)).isoformat()
    return {
        "window": {"from": since, "to": date.today().isoformat()},
        "gate_failures": _validate_failures(since),
        "sla_breaches": _sla_breaches(since),
        "cost": ledger.aggregate(f"{days}d"),
        "ctor": _ctor(since),
        "subject_ab": _subject_scores(since),
        "playbook_health": _playbook_health(),
        "pending_verification": _pending(days),
    }


def _validate_failures(since: str) -> list[dict]:
    log = HARNESS / "validate-log.jsonl"
    if not log.exists():
        return []
    out = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("ts", "")[:10] >= since and not r.get("passed", True):
            out.append(
                {
                    "stage": r.get("stage"),
                    "rule": r.get("rule"),
                    "ts": r.get("ts"),
                    "detail": (r.get("detail") or "")[:200],
                }
            )
    return out[:40]


def _sla_breaches(since: str) -> list[dict]:
    cfg = load_yaml_flat(STUDIO / "config" / "harness.yaml")
    sla = cfg.get("sla", {}) or {}
    out = []
    traces = HARNESS / "traces"
    if not traces.exists():
        return []
    since_compact = since.replace("-", "")
    for f in sorted(traces.glob("trace-*.jsonl")):
        stem = f.stem.replace("trace-", "")
        if stem < since_compact:
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            stage = r.get("stage")
            spec = sla.get(stage, {}) if isinstance(sla.get(stage), dict) else {}
            limit = spec.get("sec")
            elapsed = r.get("elapsed_sec") or r.get("elapsed_seconds") or 0
            if limit and elapsed > limit:
                out.append(
                    {
                        "stage": stage,
                        "elapsed": elapsed,
                        "sla": limit,
                        "trace": f.stem,
                    }
                )
    return out[:30]


def _ctor(since: str) -> dict:
    src = next(
        (
            p
            for p in (
                HARNESS / "ctor-ledger.jsonl",
                STUDIO / "content" / "newsletter" / "ctor-ledger.jsonl",
            )
            if p.exists()
        ),
        None,
    )
    if not src:
        return {"low": [], "high": [], "n": 0}
    low, high, n = [], [], 0
    for line in src.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("date", "") < since or not r.get("opens"):
            continue
        n += 1
        ctor = r["clicks"] / r["opens"]
        rec = {
            "date": r["date"],
            "ctor": round(ctor, 4),
            "subject": (r.get("subject") or "")[:80],
        }
        if ctor < 0.10:
            low.append(rec)
        elif ctor > 0.15:
            high.append(rec)
    return {"low": low[:10], "high": high[:10], "n": n}


def _subject_scores(since: str) -> list[dict]:
    out = []
    d = STUDIO / "content" / "newsletter"
    if not d.exists():
        return []
    for f in sorted(d.glob("*subject-scores.json")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
        if m and m.group(1) >= since:
            try:
                out.append(
                    {
                        "date": m.group(1),
                        "scores": json.loads(f.read_text(encoding="utf-8")),
                    }
                )
            except json.JSONDecodeError:
                pass
    return out[:10]


def _playbook_health() -> dict:
    from . import playbook as P

    idx = load_yaml_flat(STUDIO / "config" / "skill-index.yaml")
    out = {}
    for key in idx.get("skills") or {}:
        try:
            _, entries = P.load(key)
        except (KeyError, FileNotFoundError):
            continue
        out[key] = P.health(entries)
    return out


def _pending(days: int) -> list[dict]:
    from . import playbook as P

    cfg = load_yaml_flat(STUDIO / "config" / "harness.yaml")
    wait = (
        ((cfg.get("playbook") or {}).get("learned") or {}).get("verify_after_days", 14)
    )
    cutoff = (date.today() - timedelta(days=wait)).isoformat()
    idx = load_yaml_flat(STUDIO / "config" / "skill-index.yaml")
    out = []
    for key in idx.get("skills") or {}:
        try:
            _, entries = P.load(key)
        except (KeyError, FileNotFoundError):
            continue
        for e in entries:
            if (
                not e.deprecated
                and e.helpful == 0
                and e.harmful == 0
                and e.since <= cutoff
            ):
                out.append(
                    {
                        "skill": key,
                        "id": e.id,
                        "since": e.since,
                        "body": e.body[:200],
                    }
                )
    return out


REFLECTOR_PROMPT = """당신은 마케팅 콘텐츠 스튜디오의 Reflector입니다.
아래 실행 신호를 읽고, 스킬 플레이북에 반영할 delta를 제안하세요.

절대 규칙:
1. STABLE 섹션(브랜드 톤·품질 게이트)에 대한 제안은 하지 마세요. LEARNED만 대상입니다.
2. 각 delta는 evidence에 검증 가능한 참조(trace-*, ctor:날짜, validate:단계)를 포함해야 합니다.
3. ADD 에는 expected(metric, delta)를 반드시 붙이세요. 예측 없는 제안은 무효입니다.
4. 신호가 약하면 delta를 만들지 마세요. 빈 배열이 정답일 수 있습니다.
5. 최대 {max_deltas}개. 추측이 아니라 반복 관찰된 패턴만.
6. 출력은 JSON만. 설명·마크다운 코드블록 없이.

스킬 키 목록: {skill_keys}

출력 스키마: schemas/delta.schema.json 준수.

--- 신호 ---
{signals}
"""


def build_prompt(signals: dict) -> str:
    cfg = load_yaml_flat(STUDIO / "config" / "harness.yaml")
    rc = (cfg.get("playbook") or {}).get("reflect") or {}
    idx = load_yaml_flat(STUDIO / "config" / "skill-index.yaml")
    return REFLECTOR_PROMPT.format(
        max_deltas=rc.get("max_deltas_per_run", 6),
        skill_keys=", ".join((idx.get("skills") or {}).keys()),
        signals=json.dumps(signals, ensure_ascii=False, indent=1)[
            : (rc.get("max_tokens_in", 6000) * 2)
        ],
    )


def save(delta_doc: dict) -> Path:
    DELTAS.mkdir(parents=True, exist_ok=True)
    p = DELTAS / f"delta-{date.today().strftime('%Y%m%d')}.json"
    if "generated_at" not in delta_doc or not delta_doc["generated_at"]:
        delta_doc["generated_at"] = date.today().isoformat()
    p.write_text(json.dumps(delta_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
