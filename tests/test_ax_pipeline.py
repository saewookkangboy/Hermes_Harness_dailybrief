import json
from pathlib import Path

from lib.ax.channels import hashtags
from lib.ax.lens_queries import LensQuery
from lib.ax.memory import load_memory, update_lens_feedback
from lib.ax.pipeline import run_topic_pack
from lib.ax.text import euro
from lib.ax.topic_spec import build_topic_spec

FIXTURE = Path(__file__).parent / "fixtures" / "topic" / "short-form-commerce.json"
STAMP = "2026-10-02"


def test_full_pipeline_offline_passes_all_gates(isolated_topics, monkeypatch):
    monkeypatch.setenv("HERMES_TOPIC_TRACE", "0")
    result = run_topic_pack("숏폼 커머스", STAMP, fixture=FIXTURE)
    assert result.passed, result.report.summary()
    names = {r.name for r in result.report.results}
    assert names == {"relevance", "coverage", "diversity", "blueprint", "future", "channel", "validate"}
    for key in ("research", "ax-blueprint", "resource-map", "future-ahead", "blog", "linkedin",
                "newsletter", "threads", "instagram", "topic-pack", "gates"):
        assert result.paths[key].exists(), key
        assert result.paths[key].parent.parent == isolated_topics / "topics"
    idx = json.loads((isolated_topics / "topics" / "_index.json").read_text())
    assert idx["short-form-video-commerce"]["runs"] == 1
    pack_md = result.paths["topic-pack"].read_text()
    assert "### [Topic Research]" not in pack_md and "## [Topic Research]" in pack_md


def test_rerun_marks_delta_and_keeps_memory(isolated_topics, monkeypatch):
    monkeypatch.setenv("HERMES_TOPIC_TRACE", "0")
    run_topic_pack("숏폼 커머스", "2026-10-01", fixture=FIXTURE)
    second = run_topic_pack("숏폼 커머스", STAMP, fixture=FIXTURE)
    evidence = json.loads(second.paths["evidence"].read_text())
    assert evidence["new_count"] == 0
    mem = load_memory("short-form-video-commerce")
    assert [r["stamp"] for r in mem["runs"]] == ["2026-10-01", STAMP]


def test_pipeline_stops_after_m1_when_research_gate_fails(isolated_topics, tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_TOPIC_TRACE", "0")
    thin = tmp_path / "thin.json"
    data = json.loads(FIXTURE.read_text())
    data["results"] = data["results"][:3]
    thin.write_text(json.dumps(data))
    result = run_topic_pack("숏폼 커머스", STAMP, fixture=thin)
    assert not result.passed and result.stopped_at == "M1"
    assert "ax-blueprint" not in result.paths
    assert result.paths["research"].exists()


def test_partial_stages_reuse_saved_evidence(isolated_topics, monkeypatch):
    monkeypatch.setenv("HERMES_TOPIC_TRACE", "0")
    run_topic_pack("숏폼 커머스", STAMP, stages=("M1",), fixture=FIXTURE)
    result = run_topic_pack("숏폼 커머스", STAMP, stages=("M2", "M3", "M4"))
    assert result.passed
    assert result.paths["future-ahead"].exists()
    assert "linkedin" not in result.paths


class _FakeEvidence:
    def __init__(self, lens):
        self.lens = lens


class _FakePack:
    def __init__(self, lenses):
        self.items = [_FakeEvidence(l) for l in lenses]


def test_lens_feedback_running_average(isolated_topics):
    queries = [LensQuery("korea", "news", "a"), LensQuery("korea", "web", "b")]
    update_lens_feedback(_FakePack([]), queries)
    fb = update_lens_feedback(_FakePack(["korea", "korea", "korea", "korea"]), queries)
    assert fb["lenses"]["korea"] == {"runs": 2, "avg_yield": 1.0, "last_yield": 2.0}


def test_channel_drafts_meet_quality_rules(isolated_topics, monkeypatch):
    monkeypatch.setenv("HERMES_TOPIC_TRACE", "0")
    result = run_topic_pack("숏폼 커머스", STAMP, fixture=FIXTURE)
    li = result.paths["linkedin"].read_text()
    body = li.split("---")[0]
    assert len(body) <= 1300 and body.count("→") >= 3 and "저는" in body and "?" in body[-120:]
    nl = result.paths["newsletter"].read_text()
    for s in ("## 30초 TLDR", "## 오늘의 1가지", "## 3분 읽기", "## 이번 주 실습 1가지", "## 제목 후보"):
        assert s in nl
    assert "[블로그 링크]" in result.paths["threads"].read_text()
    ig = result.paths["instagram"].read_text()
    assert ig.count("### Slide") == 3 and len(hashtags(build_topic_spec("숏폼 커머스", STAMP))) >= 5
    blog = result.paths["blog"].read_text()
    for s in ("## 주요 트렌드", "## 핵심 기술", "## 시사점", "## 한 줄 요약"):
        assert s in blog
    for bad in ("생성로", "제안로", "생성를", "은(는)"):
        assert bad not in li + nl + blog + ig


def test_josa_euro():
    assert euro("대량 생성") == "대량 생성으로"
    assert euro("탐지") == "탐지로"
    assert euro("파일") == "파일로"
    assert euro("'시간(일)'") == "'시간(일)'로"
