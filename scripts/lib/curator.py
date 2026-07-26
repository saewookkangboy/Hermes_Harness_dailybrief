"""Curator — delta를 LEARNED에 적용. ADD / BUMP / DEPRECATE 3연산만."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from . import ledger, playbook as P
from .token_budget import load_yaml_flat

STUDIO = ledger.STUDIO
LOG = STUDIO / ".harness" / "playbook-log.jsonl"


class ForbiddenOp(RuntimeError):
    pass


def _log(rec: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def apply_delta(delta: dict, *, dry: bool = False) -> str:
    op = delta["op"]
    if op not in ("ADD", "BUMP", "DEPRECATE"):
        raise ForbiddenOp(f"허용되지 않은 연산: {op}")

    skill = delta["skill"]
    stable, entries = P.load(skill)
    original_stable = stable
    by_id = {e.id: e for e in entries}
    cfg = load_yaml_flat(STUDIO / "config" / "harness.yaml")
    max_harmful = (
        ((cfg.get("playbook") or {}).get("learned") or {}).get(
            "deprecate_after_harmful", 3
        )
    )

    if op == "ADD":
        new_id = P.next_id(entries)
        body_lines = [delta["text"].strip()]
        exp = delta.get("expected") or {}
        if exp:
            body_lines.append(
                f"예측: {exp.get('metric')} {exp.get('delta')} "
                f"(검증 기한 {date.today().isoformat()} + 14일)"
            )
        body_lines.append("근거: " + ", ".join(delta["evidence"]))
        entries.append(
            P.Entry(
                id=new_id,
                helpful=0,
                harmful=0,
                since=date.today().isoformat(),
                body="\n".join(body_lines),
            )
        )
        msg = f"ADD {skill} {new_id}"

    elif op == "BUMP":
        e = by_id.get(delta["id"])
        if not e:
            return f"SKIP {skill} {delta['id']} (없음)"
        if delta["signal"] == "helpful":
            e.helpful += 1
            msg = f"BUMP {skill} {e.id} helpful→{e.helpful}/{e.harmful}"
        else:
            e.harmful += 1
            if e.harmful >= max_harmful and not e.deprecated:
                e.deprecated = True
                msg = (
                    f"BUMP+AUTO-DEPRECATE {skill} {e.id} "
                    f"(harmful={e.harmful} >= {max_harmful})"
                )
                if not dry:
                    P.write(skill, stable, entries, original_stable=original_stable)
                    _log(
                        {
                            "op": "AUTO_DEPRECATE",
                            "skill": skill,
                            "id": e.id,
                            "harmful": e.harmful,
                            "evidence": delta["evidence"],
                        }
                    )
                return msg
            msg = f"BUMP {skill} {e.id} harmful→{e.helpful}/{e.harmful}"

    else:  # DEPRECATE
        e = by_id.get(delta["id"])
        if not e:
            return f"SKIP {skill} {delta['id']} (없음)"
        e.deprecated = True
        msg = f"DEPRECATE {skill} {e.id}"

    if not dry:
        P.write(skill, stable, entries, original_stable=original_stable)
        _log(
            {
                "op": op,
                "skill": skill,
                "id": delta.get("id"),
                "evidence": delta.get("evidence"),
                "expected": delta.get("expected"),
            }
        )
    return msg


def apply_doc(path: Path, *, dry: bool = False) -> list[str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [apply_delta(d, dry=dry) for d in doc["deltas"]]


def verify_expectations(days: int = 14) -> list[dict]:
    """expected 미달 엔트리에 harmful BUMP 후보를 만든다."""
    from . import reflect

    signals = reflect.collect(days)
    out: list[dict] = []
    for pend in signals["pending_verification"]:
        out.append(
            {
                "skill": pend["skill"],
                "op": "BUMP",
                "id": pend["id"],
                "signal": "harmful",
                "evidence": [
                    f"verify:{date.today().isoformat()}",
                    f"since:{pend['since']}",
                ],
                "rationale": "verify_after_days 경과했으나 expected 개선 미확인",
            }
        )
    return out
