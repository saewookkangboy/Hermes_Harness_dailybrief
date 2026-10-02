from datetime import date
from pathlib import Path

from lib.ax.brief import render_brief
from lib.ax.config import load_config
from lib.ax.evidence import build_evidence_pack, freshness_score, normalize_url, select_top, tag_lenses
from lib.ax.gates import GateReport, research_gates
from lib.ax.sources import load_fixture
from lib.ax.text import clip, ieyo, sanitize
from lib.ax.topic_spec import build_topic_spec

FIXTURE = Path(__file__).parent / "fixtures" / "topic" / "short-form-commerce.json"
STAMP = "2026-10-02"


def _pack(seen=None):
    spec = build_topic_spec("숏폼 커머스", STAMP)
    rows = load_fixture(FIXTURE)
    return spec, build_evidence_pack(spec, rows, query_count=20, seen_urls=seen)


def test_off_topic_and_duplicates_are_filtered():
    _, pack = _pack()
    titles = [ev.title for ev in pack.items]
    assert not any("Enterprise AI agent governance" in t for t in titles)
    assert not any("Cloud storage" in t for t in titles)
    assert sum("What is short-form video commerce" in t for t in titles) == 1
    assert pack.raw_count == 20
    assert pack.relevant_count == 18


def test_tracking_params_stripped():
    assert normalize_url("https://a.example/x/?utm_source=y&id=3#frag") == "https://a.example/x?id=3"


def test_lens_tagging_adds_api_lens():
    _, pack = _pack()
    gh = pack.by_source("github")
    assert gh and all("tech_tools" in ev.lenses for ev in gh)
    ax = pack.by_source("arxiv")
    assert ax and "future_signals" in ax[0].lenses


def test_freshness_and_confidence_ordering():
    today = date(2026, 10, 2)
    assert freshness_score("2026-09-20", today) == 1.0
    assert freshness_score("", today) == 0.5
    assert freshness_score("2024-01-01", today) == 0.0
    _, pack = _pack()
    confs = [ev.confidence for ev in pack.items]
    assert confs == sorted(confs, reverse=True)


def test_research_gates_pass_on_fixture():
    _, pack = _pack()
    report = research_gates(pack, GateReport())
    assert report.passed, report.summary()
    assert {r.name for r in report.results} == {"relevance", "coverage", "diversity"}


def test_relevance_gate_fails_when_thin():
    spec = build_topic_spec("숏폼 커머스", STAMP)
    rows = load_fixture(FIXTURE)[:3]
    pack = build_evidence_pack(spec, rows, query_count=3)
    report = research_gates(pack, GateReport())
    assert not report.passed
    assert "relevance" in {r.name for r in report.failures()}


def test_delta_marks_seen_urls():
    _, first = _pack()
    seen = {ev.url for ev in first.items[:5]}
    _, second = _pack(seen)
    assert second.new_count() == second.relevant_count - 5


def test_select_top_diversifies_lenses():
    _, pack = _pack()
    top = select_top(pack, 7)
    assert len(top) == 7
    assert len({ev.lens for ev in top}) == 7


def test_brief_renders_sections_and_unique_views():
    spec, pack = _pack()
    md = render_brief(spec, pack, research_gates(pack, GateReport()))
    for section in ("## Topic Spec", "## Executive Summary", "## 렌즈 커버리지", "## Top 7 인사이트", "## Evidence 목록", "## 수집 메타"):
        assert section in md
    views = [ln for ln in md.splitlines() if ln.startswith("- **마케터 관점:**")]
    assert len(views) == 7 and len(set(views)) == 7
    assert "..." not in md and "…" not in md
    assert "enterprise AI" not in md


def test_text_helpers():
    assert sanitize("혁신적인 도구... 등장") == "새로운 도구 등장"
    assert clip("첫 문장이에요. 두 번째 문장은 아주 길어서 잘려야 해요.", 12).endswith(".")
    assert ieyo("정의·개념") == "정의·개념이에요"
    assert ieyo("시장·뉴스") == "시장·뉴스예요"


def test_tag_lenses_reassigns_when_query_lens_terms_absent():
    cfg = load_config()
    text = "Short Video Platform Market Size, Share, Report, Forecast 2035"
    assert tag_lenses("risk_regulation", "web", text, cfg)[0] == "market_news"
    assert tag_lenses("risk_regulation", "web", "TikTok Shop privacy lawsuit", cfg)[0] == "risk_regulation"
    assert tag_lenses("future_signals", "web", "nextdaily 기사 제목", cfg)[0] == "future_signals"
    assert tag_lenses("future_signals", "github", "repo tool", cfg)[0] == "tech_tools"
