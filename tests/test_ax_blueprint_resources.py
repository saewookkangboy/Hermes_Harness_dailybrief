from pathlib import Path

from lib.ax.blueprint import build_blueprint, render_blueprint
from lib.ax.evidence import build_evidence_pack
from lib.ax.gates import blueprint_gate
from lib.ax.resources import build_resource_map, render_resource_map
from lib.ax.sources import load_fixture
from lib.ax.topic_spec import build_topic_spec

FIXTURE = Path(__file__).parent / "fixtures" / "topic" / "short-form-commerce.json"
STAMP = "2026-10-02"


def _inputs():
    spec = build_topic_spec("숏폼 커머스", STAMP)
    pack = build_evidence_pack(spec, load_fixture(FIXTURE), query_count=20)
    return spec, pack


def test_blueprint_covers_value_chain_with_required_fields():
    spec, pack = _inputs()
    bp = build_blueprint(spec, pack)
    stages = {o["stage"] for o in bp["opportunities"]}
    assert stages == {"research", "planning", "production", "distribution", "measurement", "optimization"}
    for o in bp["opportunities"]:
        assert 1 <= o["impact"] <= 5 and 1 <= o["feasibility"] <= 5
        assert o["kpi"] and o["hitl"] and o["risk"]
    assert blueprint_gate(bp).passed


def test_blueprint_is_domain_sensitive():
    spec, pack = _inputs()
    commerce = build_blueprint(spec, pack)
    spec_b = build_topic_spec("CDP 고객데이터", STAMP)
    data = build_blueprint(spec_b, pack)
    top_commerce = commerce["opportunities"][0]["stage"]
    top_data = data["opportunities"][0]["stage"]
    assert top_commerce in {"production", "optimization"}
    assert top_data in {"measurement", "optimization"}


def test_risk_evidence_lowers_feasibility_for_governed_stages():
    spec, pack = _inputs()
    bp = build_blueprint(spec, pack)
    by_stage = {o["stage"]: o for o in bp["opportunities"]}
    assert "규제" in by_stage["production"]["risk"] or "공정위" in by_stage["production"]["risk"] or "Risks" in by_stage["production"]["risk"]
    assert by_stage["production"]["feasibility"] <= by_stage["research"]["feasibility"] + 1


def test_blueprint_markdown_sections():
    spec, pack = _inputs()
    md = render_blueprint(build_blueprint(spec, pack))
    for s in ("## AX 성숙도", "## 자동화 기회 매트릭스", "## 단계별 설계", "## 30/60/90일 로드맵", "## 거버넌스"):
        assert s in md
    assert "https://" in md


def test_resource_map_prioritizes_domain_tools_and_lists_oss():
    spec, pack = _inputs()
    bp = build_blueprint(spec, pack)
    rm = build_resource_map(spec, pack, bp)
    assert rm["tools"][0]["origin"] == "도메인 특화"
    assert any(t["name"] == "Shopify Magic" for t in rm["tools"])
    assert rm["open_source"][0]["name"] == "shopclip/shoppable-shorts"
    assert rm["papers"] and rm["latest"]
    md = render_resource_map(rm)
    for s in ("## 도구·플랫폼", "## 오픈소스 (GitHub)", "## 연구·논문 (arXiv)", "## 최신 기술·릴리스", "## 학습 리소스"):
        assert s in md
