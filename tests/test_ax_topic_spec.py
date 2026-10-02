from lib.ax.lens_queries import expand_keyword_queries, generate_queries, queries_per_lens
from lib.ax.topic_spec import build_topic_spec, relevance_score, tokenize

STAMP = "2026-10-02"


def test_compound_korean_keyword_is_split_and_translated():
    spec = build_topic_spec("숏폼커머스", STAMP)
    assert spec.tokens == ["숏폼", "커머스"]
    assert spec.en_query == "short-form video commerce"
    assert spec.slug == "short-form-video-commerce"


def test_domain_prefers_specific_over_generic_ai():
    spec = build_topic_spec("AI 숏폼 커머스", STAMP)
    assert spec.domain == "commerce"
    assert "ai_tech" in spec.secondary_domains


def test_ai_only_keyword_maps_to_ai_tech():
    spec = build_topic_spec("RAG 평가", STAMP)
    assert spec.domain == "ai_tech"
    assert spec.en_query == "rag evaluation"


def test_unknown_domain_falls_back_to_general():
    spec = build_topic_spec("팝업스토어 기획", STAMP)
    assert spec.domain == "general_marketing"
    assert spec.slug


def test_intent_detection():
    assert build_topic_spec("CDP 도입 방법", STAMP).intent == "how_to"
    assert build_topic_spec("CRM 툴 비교", STAMP).intent == "comparison"
    assert build_topic_spec("브랜드 전략", STAMP).intent == "strategy"
    assert build_topic_spec("숏폼", STAMP).intent == "trend"


def test_short_ascii_token_uses_word_boundary():
    spec = build_topic_spec("RAG 평가", STAMP)
    assert relevance_score(spec, "Cloud storage pricing evaluation") == 0.5
    assert relevance_score(spec, "How to run RAG evaluation with Ragas") == 1.0


def test_stopwords_removed():
    assert "리서치" not in tokenize("숏폼 리서치")


def test_queries_cover_all_lenses_without_enterprise_ai_bias():
    spec = build_topic_spec("숏폼 커머스", STAMP)
    queries = generate_queries(spec, feedback={})
    lenses = {q.lens for q in queries}
    assert lenses == {
        "definition", "market_news", "tech_tools", "use_cases",
        "risk_regulation", "korea", "future_signals",
    }
    assert {q.source for q in queries} >= {"web", "news", "github", "arxiv", "hn"}
    assert not any("enterprise ai" in q.query.lower() for q in queries)
    assert all("{" not in q.query for q in queries)


def test_low_yield_lens_gets_extra_query():
    fb = {"lenses": {"korea": {"runs": 3, "avg_yield": 0.4}}}
    assert queries_per_lens("korea", fb) == 3
    assert queries_per_lens("definition", fb) == 2


def test_keyword_expansion_is_domain_neutral():
    qs = expand_keyword_queries("숏폼 커머스", STAMP)
    assert qs[0] == "숏폼 커머스"
    assert not any("enterprise AI" in q for q in qs)
    assert any("short-form video commerce" in q for q in qs)


def test_intent_words_split_from_topic_and_acronym_expanded():
    spec = build_topic_spec("CDP 도입 방법", STAMP)
    assert spec.tokens == ["cdp"]
    assert spec.intent == "how_to"
    assert spec.slug == "cdp"
    assert "customer data platform" in spec.en_query
    assert spec.domain == "data_crm"


def test_bare_acronym_requires_context():
    spec = build_topic_spec("CDP 도입 방법", STAMP)
    assert relevance_score(spec, "Extreme Weather to Cost Firms: CDP Report") == 0.0
    assert relevance_score(spec, "CDP for marketers: unify customer profiles") == 1.0
    assert relevance_score(spec, "What is a Customer Data Platform") == 1.0


def test_slug_is_ascii_even_for_untranslated_korean():
    spec = build_topic_spec("뜨개질 클래스", STAMP)
    assert spec.slug.isascii() and spec.slug.startswith("topic-")
