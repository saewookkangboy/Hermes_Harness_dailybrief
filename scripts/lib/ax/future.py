"""M4 Future Ahead — Now/Next/Future 예측 · 약한 신호 · 2×2 시나리오 · 월요일 액션."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from lib.ax.config import WORKDIR, load_config
from lib.ax.evidence import Evidence, EvidencePack
from lib.ax.text import eunneun, ieyo
from lib.ax.topic_spec import TopicSpec

GRAPH_DB = WORKDIR / "content" / "wiki" / "graph.db"
_KO_TERM = re.compile(r"[가-힣]{3,}")
_LOWER_WORD = re.compile(r"(?<![A-Za-z0-9])[a-z][a-z0-9]+(?![A-Za-z0-9])")
_EN_DISTINCT = re.compile(
    r"\b(?:[A-Za-z]+-[A-Za-z]+|[A-Z][a-z0-9]*[A-Z][A-Za-z0-9]*|[A-Za-z]*\d[A-Za-z0-9]*[A-Za-z][A-Za-z0-9]*|[A-Z]{3,})\b"
)
_EN_MIDCAP = re.compile(r"(?<=[a-z0-9,;:] )[A-Z][a-z]{2,}\b")
_KO_ENDING = re.compile(r"(요|다|니다|해|해서|하고|하는|했고|되는|되고|있는|없는|으로|에서|에게|까지|부터|처럼|이고|이며|라는|이라|했어|됐어|돼서|을|를|이|가|은|는|의|에|로|와|과|도)$")
_EN_STOP = {
    "the", "how", "what", "why", "our", "this", "new", "top", "case", "study", "risks", "future", "guide", "hacker",
    "news", "points", "comments", "with", "for", "and", "from", "will", "can", "you", "your", "we", "a", "an", "of",
    "brands", "brand", "tools", "platforms", "report", "market", "outlook", "explained", "update", "launch",
    "trends", "trend", "best", "statistics", "size", "share", "forecast", "compared", "examples", "solutions",
    "solution", "data", "platform", "customer", "customers", "marketing", "industry", "insights", "analysis",
    "strategy", "strategies", "benefits", "overview", "complete", "ultimate", "latest", "key", "figures", "growth",
    "show", "ask", "blog", "inc", "llc", "ltd", "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december", "use", "cases", "challenges", "vendors", "features",
}
HORIZON_DECAY = {"now": 1.0, "next": 0.92, "future": 0.85}


def candidate_terms(title: str, snippet: str, spec: TopicSpec) -> set[str]:
    """고유명사형 용어만: 하이픈·CamelCase·숫자혼합·대문자 약어, 또는 본문 문장 중간의 대문자 단어 (Title Case 제목 단어 제외)."""
    topic_words = {w for group in spec.core_groups for v in group for w in re.split(r"[\s\-]", v.lower()) if w}
    out: set[str] = set()
    for m in [*_EN_DISTINCT.findall(f"{title} {snippet}"), *_EN_MIDCAP.findall(snippet)]:
        low = m.lower()
        if len(low) < 3:
            continue
        parts = {p[:-1] if p.endswith("s") and len(p) > 3 else p for p in low.split("-")}
        if low in _EN_STOP or parts <= _EN_STOP | topic_words or (parts | {low}) & topic_words:
            continue
        out.add(low)
    for m in _KO_TERM.findall(f"{title} {snippet}"):
        if not _KO_ENDING.search(m) and not any(w in m for w in topic_words if len(w) >= 2):
            out.add(m)
    return out


def _confidence_label(v: float) -> str:
    return "높음" if v >= 0.7 else "보통" if v >= 0.5 else "낮음"


def _horizon_signals(pack: EvidencePack, lenses: list[str], horizon: str) -> list[Evidence]:
    picked = [ev for ev in pack.items if ev.lens in lenses]
    if horizon == "future":
        picked += [ev for ev in pack.items if ev.source_type in ("arxiv", "hn") and ev not in picked]
    return sorted(picked, key=lambda e: e.confidence, reverse=True)


def weak_signals(
    spec: TopicSpec,
    pack: EvidencePack,
    prior_terms: set[str] | None = None,
    cfg: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """여러 도메인에서 반복되지만 아직 주류(비중 상한)가 아닌 신규 용어."""
    cfg = cfg or load_config()
    wcfg = cfg.get("weak_signal") or {}
    generic = {t.lower() for l in (cfg.get("lenses") or {}).values() for term in l.get("tag_terms") or [] for t in term.split()}
    generic |= {t.lower() for t in wcfg.get("stop_terms") or []}
    prior_terms = prior_terms or set()
    corpus = " ".join(f"{ev.title} {ev.snippet}" for ev in pack.items)
    lowercase_words = set(_LOWER_WORD.findall(corpus))
    term_domains: dict[str, set[str]] = defaultdict(set)
    term_fresh: dict[str, list[float]] = defaultdict(list)
    for ev in pack.items:
        for term in candidate_terms(ev.title, ev.snippet, spec):
            if term in generic or term in prior_terms:
                continue
            if term.isascii() and "-" not in term and term in lowercase_words:
                continue
            term_domains[term].add(ev.domain)
            term_fresh[term].append(ev.freshness)
    total = max(1, len(pack.domains()))
    out = []
    for term, domains in term_domains.items():
        share = len(domains) / total
        if len(domains) >= int(wcfg.get("min_domains", 2)) and share <= float(wcfg.get("max_share", 0.35)):
            fresh = sum(term_fresh[term]) / len(term_fresh[term])
            out.append({"term": term, "domains": len(domains), "share": round(share, 2), "freshness": round(fresh, 2)})
    out.sort(key=lambda r: (r["freshness"], r["domains"]), reverse=True)
    return out[: int(wcfg.get("max_items", 5))]


def graph_signals(spec: TopicSpec, db_path: Path = GRAPH_DB, limit: int = 5) -> list[dict[str, Any]]:
    """누적 wiki graph에서 주제 관련 개념의 언급 추이 (없으면 빈 목록)."""
    if not db_path.exists():
        return []
    variants = [v for group in spec.core_groups for v in group if len(v) >= 2]
    if not variants:
        return []
    where = " OR ".join("lower(label) LIKE ?" for _ in variants)
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = con.execute(
            f"SELECT label, mention_cnt, first_seen, last_seen FROM node WHERE kind='concept' AND ({where}) "
            "ORDER BY mention_cnt DESC LIMIT ?",
            [f"%{v.lower()}%" for v in variants] + [limit],
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return []
    return [{"label": r[0], "mentions": r[1], "first_seen": r[2], "last_seen": r[3]} for r in rows]


def lens_trend(pack: EvidencePack, history: list[dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    if not history:
        return []
    prev = history[-1].get("lens_counts") or {}
    labels = {k: v.get("label", k) for k, v in (cfg.get("lenses") or {}).items()}
    out = []
    for lens, now in pack.lens_counts().items():
        delta = now - int(prev.get(lens, 0))
        if delta:
            out.append(f"{labels.get(lens, lens)} {'+' if delta > 0 else ''}{delta}")
    return out


def _statement(horizon: str, spec: TopicSpec, signals: list[Evidence], pack: EvidencePack, weak: list[dict], cfg: dict) -> str:
    labels = {k: v.get("label", k) for k, v in (cfg.get("lenses") or {}).items()}
    lead = signals[0].title
    quoted = f"'{lead}'"
    if horizon == "now":
        top_lens = Counter(ev.lens for ev in signals).most_common(1)[0][0]
        return (
            f"앞으로 6개월 안에는 '{spec.ko_query}'의 {labels.get(top_lens, top_lens)} 신호가 실무 의사결정으로 이어질 가능성이 커요. "
            f"대표 근거는 {ieyo(quoted)}."
        )
    if horizon == "next":
        counts = pack.lens_counts()
        axis = "도구·플랫폼 통합" if counts.get("tech_tools", 0) >= counts.get("risk_regulation", 0) else "규제·신뢰 대응"
        return f"6~18개월 사이에는 {axis} 역량이 '{spec.ko_query}' 성과 격차를 만들 거예요. '{lead}' 같은 신호가 그 방향을 보여 줘요."
    terms = ", ".join(w["term"] for w in weak[:3])
    hint = f"{terms} 같은 신규 용어" if terms else "연구·커뮤니티 신호"
    return f"18~36개월 뒤 '{spec.ko_query}'의 판도는 {hint}에서 먼저 드러날 수 있어요. 초기 단서는 {ieyo(quoted)}."


def _scenarios(spec: TopicSpec, cfg: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    axes_cfg = cfg.get("scenario_axes") or {}
    axes = axes_cfg.get(spec.domain) or next(
        (axes_cfg[d] for d in spec.secondary_domains if d in axes_cfg), axes_cfg.get("default")
    )
    x, y = axes["x"], axes["y"]
    rows = [
        (x["high"], y["high"], "먼저 실험한 팀이 데이터와 노하우를 쌓아 격차를 벌려요.", "Quick Win 자동화를 30일 안에 파일럿으로 돌려요."),
        (x["high"], y["low"], "빠르게 도입하더라도 승인·기록 체계가 없으면 리스크가 커져요.", "HITL 승인 단계와 감사 로그를 먼저 갖춰요."),
        (x["low"], y["high"], "큰 투자보다 저비용 실험을 꾸준히 이어 가는 편이 유리해요.", "효율 개선 과제부터 작은 자동화를 쌓아요."),
        (x["low"], y["low"], "관망하면서 규제 대응 역량을 먼저 갖추는 게 안전해요.", "리스크 체크리스트와 데이터 거버넌스를 정비해요."),
    ]
    scenarios = [
        {
            "name": f"{xv} · {yv}",
            "desc": f"{eunneun(x['label'])} {xv}, {eunneun(y['label'])} {yv} 쪽으로 가는 경우예요. {desc}",
            "prepare": prep,
        }
        for xv, yv, desc, prep in rows
    ]
    return {"x": x["label"], "y": y["label"]}, scenarios


def build_future(
    spec: TopicSpec,
    pack: EvidencePack,
    blueprint: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
    cfg: dict[str, Any] | None = None,
    graph_db: Path = GRAPH_DB,
) -> dict[str, Any]:
    cfg = cfg or load_config()
    history = history or []
    prior_terms = {t for run in history for t in run.get("terms") or []}
    weak = weak_signals(spec, pack, prior_terms, cfg)
    need = int(((cfg.get("gates") or {}).get("future") or {}).get("min_signals_per_prediction", 2))

    predictions, watchlist = [], []
    for horizon, hcfg in (cfg.get("horizons") or {}).items():
        signals = _horizon_signals(pack, hcfg.get("lenses") or [], horizon)[:3]
        if len(signals) < need:
            watchlist.append(f"{hcfg.get('label', horizon)}: 근거 {len(signals)}건이라 다음 실행에서 다시 확인해요")
            continue
        conf = round(sum(ev.confidence for ev in signals) / len(signals) * HORIZON_DECAY.get(horizon, 1.0), 2)
        predictions.append(
            {
                "horizon": horizon,
                "label": hcfg.get("label", horizon),
                "statement": _statement(horizon, spec, signals, pack, weak, cfg),
                "signals": [{"title": ev.title, "url": ev.url, "lens": ev.lens} for ev in signals],
                "confidence": conf,
                "confidence_label": _confidence_label(conf),
            }
        )

    axes, scenarios = _scenarios(spec, cfg)
    ranked = sorted(blueprint.get("opportunities") or [], key=lambda o: o["priority"], reverse=True)
    actions = [
        f"{o['label']}: '{spec.ko_query}' 파일럿 범위를 정하고 '{o['kpi']}' 기준선을 이번 주에 기록해요."
        for o in ranked[:3]
    ]
    return {
        "topic": spec.keyword,
        "stamp": spec.stamp,
        "predictions": predictions,
        "watchlist": watchlist + [f"약한 신호 '{w['term']}' ({w['domains']}개 도메인)" for w in weak],
        "weak_signals": weak,
        "graph_signals": graph_signals(spec, graph_db),
        "lens_trend": lens_trend(pack, history, cfg),
        "axes": axes,
        "scenarios": scenarios,
        "actions": actions,
    }


def render_future(fa: dict[str, Any]) -> str:
    out = [f"# [Future Ahead] {fa['topic']}", "", f"> {fa['stamp']} · 예측 {len(fa['predictions'])} · 약한 신호 {len(fa['weak_signals'])}", ""]
    out += ["## Three Horizons", ""]
    for p in fa["predictions"]:
        out += [f"### {p['label']} · 신뢰도 {p['confidence_label']} ({p['confidence']:.2f})", "", p["statement"], ""]
        out += [f"- 신호: {s['title']} — {s['url']}" for s in p["signals"]]
        out.append("")
    out += ["## 약한 신호", ""]
    if fa["weak_signals"]:
        out += ["| 용어 | 도메인 수 | 비중 | 신선도 |", "|------|-----------|------|--------|"]
        out += [f"| {w['term']} | {w['domains']} | {w['share']:.0%} | {w['freshness']:.2f} |" for w in fa["weak_signals"]]
    else:
        out.append("- 이번 수집에서는 기준을 넘은 약한 신호가 없었어요.")
    if fa["graph_signals"]:
        out += ["", "### 누적 그래프 신호", ""]
        out += [f"- {g['label']} — 언급 {g['mentions']}회 · {g['first_seen'][:10]} ~ {g['last_seen'][:10]}" for g in fa["graph_signals"]]
    if fa["lens_trend"]:
        out += ["", f"- 이전 실행 대비 렌즈 변화: {', '.join(fa['lens_trend'])}"]
    out += ["", f"## 2×2 시나리오 ({fa['axes']['x']} × {fa['axes']['y']})", ""]
    for s in fa["scenarios"]:
        out += [f"### {s['name']}", "", s["desc"], f"- **준비할 것:** {s['prepare']}", ""]
    out += ["## 다음 주 월요일에 할 일", ""]
    out += [f"{i}. {a}" for i, a in enumerate(fa["actions"], 1)]
    if fa["watchlist"]:
        out += ["", "## 관찰 목록", ""]
        out += [f"- {w}" for w in fa["watchlist"]]
    return "\n".join(out) + "\n"


def write_future(fa: dict[str, Any], md_path: Path, json_path: Path) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_future(fa), encoding="utf-8")
    json_path.write_text(json.dumps(fa, ensure_ascii=False, indent=2), encoding="utf-8")
