import sqlite3
from pathlib import Path

from lib.ax.blueprint import build_blueprint
from lib.ax.evidence import build_evidence_pack
from lib.ax.future import build_future, candidate_terms, graph_signals, render_future, weak_signals
from lib.ax.gates import future_gate
from lib.ax.sources import load_fixture
from lib.ax.text import eunneun
from lib.ax.topic_spec import build_topic_spec

FIXTURE = Path(__file__).parent / "fixtures" / "topic" / "short-form-commerce.json"
STAMP = "2026-10-02"


def _inputs():
    spec = build_topic_spec("숏폼 커머스", STAMP)
    pack = build_evidence_pack(spec, load_fixture(FIXTURE), query_count=20)
    return spec, pack, build_blueprint(spec, pack)


def test_future_has_horizons_with_evidence_and_actions():
    spec, pack, bp = _inputs()
    fa = build_future(spec, pack, bp, graph_db=Path("/nonexistent.db"))
    horizons = [p["horizon"] for p in fa["predictions"]]
    assert horizons == ["now", "next", "future"]
    for p in fa["predictions"]:
        assert len(p["signals"]) >= 2 and p["confidence"] > 0
    assert len(fa["actions"]) == 3
    assert len(fa["scenarios"]) == 4
    assert future_gate(fa).passed


def test_scenario_axes_follow_domain():
    spec, pack, bp = _inputs()
    fa = build_future(spec, pack, bp, graph_db=Path("/nonexistent.db"))
    assert fa["axes"]["x"] == "AI 쇼핑 에이전트 보급"
    generic = build_topic_spec("팝업스토어 기획", STAMP)
    fb = build_future(generic, pack, build_blueprint(generic, pack), graph_db=Path("/nonexistent.db"))
    assert fb["axes"]["x"] == "기술 도입 속도"


def test_weak_signals_exclude_prior_terms():
    spec, pack, _ = _inputs()
    first = weak_signals(spec, pack)
    if first:
        again = weak_signals(spec, pack, prior_terms={first[0]["term"]})
        assert first[0]["term"] not in {w["term"] for w in again}


def test_lens_trend_uses_history():
    spec, pack, bp = _inputs()
    history = [{"lens_counts": {"market_news": 1}, "terms": []}]
    fa = build_future(spec, pack, bp, history=history, graph_db=Path("/nonexistent.db"))
    assert any(t.startswith("시장·뉴스 +") for t in fa["lens_trend"])


def test_future_gate_fails_without_signals():
    spec, pack, bp = _inputs()
    pack.items = pack.items[:1]
    fa = build_future(spec, pack, bp, graph_db=Path("/nonexistent.db"))
    assert not future_gate(fa).passed
    assert fa["watchlist"]


def test_graph_signals_reads_concepts(tmp_path):
    db = tmp_path / "graph.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE node (id TEXT, kind TEXT, label TEXT, first_seen TEXT, last_seen TEXT, mention_cnt INT)")
    con.execute("INSERT INTO node VALUES ('c1','concept','숏폼 커머스 확산','2026-08-01','2026-09-30',7)")
    con.commit()
    con.close()
    spec = build_topic_spec("숏폼 커머스", STAMP)
    rows = graph_signals(spec, db)
    assert rows and rows[0]["mentions"] == 7


def test_render_future_sections():
    spec, pack, bp = _inputs()
    md = render_future(build_future(spec, pack, bp, graph_db=Path("/nonexistent.db")))
    for s in ("## Three Horizons", "## 약한 신호", "## 2×2 시나리오", "## 다음 주 월요일에 할 일"):
        assert s in md
    assert "은(는)" not in md
    assert eunneun("플랫폼 종속도") == "플랫폼 종속도는"


def test_candidate_terms_skip_title_case_words_and_topic_plurals():
    spec = build_topic_spec("CDP 도입 방법", STAMP)
    terms = candidate_terms(
        "Best CDPs Compared: Large Language Models Meet DeepEval",
        "Teams now pair Zeotap with open-source pipelines. Discover more.",
        spec,
    )
    assert {"deepeval", "zeotap", "open-source"} <= terms
    assert not terms & {"best", "cdps", "large", "compared", "discover"}
