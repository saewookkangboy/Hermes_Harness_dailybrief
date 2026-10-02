"""M1b 7-Lens 쿼리 생성 — 고정 쿼리 목록·고정 접미사 없이 topic_spec에서 생성."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from lib.ax.config import lens_feedback_path, load_config
from lib.ax.topic_spec import TopicSpec, build_topic_spec

LENS_ONLY_SOURCES = {"github", "arxiv", "hn"}


@dataclass(frozen=True)
class LensQuery:
    lens: str
    source: str
    query: str


def _fill(template: str, spec: TopicSpec, today: date) -> str:
    return (
        template.replace("{en}", spec.en_query)
        .replace("{ko}", spec.ko_query)
        .replace("{year}", str(today.year))
        .replace("{next_year}", str(today.year + 1))
        .strip()
    )


def load_lens_feedback() -> dict[str, Any]:
    path = lens_feedback_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def queries_per_lens(lens: str, feedback: dict[str, Any], base: int = 2) -> int:
    """적중률이 낮은 렌즈는 쿼리를 1개 더 써서 커버리지를 보강한다."""
    stats = (feedback.get("lenses") or {}).get(lens) or {}
    runs = int(stats.get("runs") or 0)
    avg_yield = float(stats.get("avg_yield") or 0.0)
    if runs >= 2 and avg_yield < 1.0:
        return base + 1
    return base


def generate_queries(
    spec: TopicSpec,
    *,
    today: date | None = None,
    cfg: dict[str, Any] | None = None,
    feedback: dict[str, Any] | None = None,
) -> list[LensQuery]:
    cfg = cfg or load_config()
    today = today or date.fromisoformat(spec.stamp)
    feedback = load_lens_feedback() if feedback is None else feedback
    enabled = {k for k, v in (cfg.get("sources") or {}).items() if isinstance(v, dict) and v.get("enabled")}
    out: list[LensQuery] = []
    seen: set[tuple[str, str]] = set()

    def add(lens: str, source: str, query: str) -> None:
        key = (source, query.lower())
        if source in enabled and query and key not in seen:
            seen.add(key)
            out.append(LensQuery(lens, source, query))

    for lens, lcfg in (cfg.get("lenses") or {}).items():
        templates = [_fill(t, spec, today) for t in lcfg.get("queries") or []]
        n = queries_per_lens(lens, feedback)
        sources = lcfg.get("sources") or ["web"]
        text_sources = [s for s in sources if s not in LENS_ONLY_SOURCES]
        api_sources = [s for s in sources if s in LENS_ONLY_SOURCES]
        if text_sources:
            primary, *secondary = text_sources
            for q in templates[:n]:
                add(lens, primary, q)
            for src in secondary:
                if templates:
                    add(lens, src, templates[0])
        for src in api_sources:
            add(lens, src, spec.en_query)
    return out


def expand_keyword_queries(keyword: str, stamp: str | None = None) -> list[str]:
    """일일 브리프 키워드 merge/replace용 확장 — 도메인 중립 (enterprise AI 접미사 없음)."""
    stamp = stamp or date.today().isoformat()
    spec = build_topic_spec(keyword, stamp)
    year = date.fromisoformat(stamp).year
    candidates = [
        keyword,
        f"{spec.en_query} {year}",
        f"{spec.en_query} marketing use case",
        f"{spec.ko_query} 사례",
        f"{spec.en_query} tools",
    ]
    seen: set[str] = set()
    out: list[str] = []
    for q in candidates:
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out
