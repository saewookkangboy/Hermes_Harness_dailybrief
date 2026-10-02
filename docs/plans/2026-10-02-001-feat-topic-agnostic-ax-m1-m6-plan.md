# Topic-Agnostic AX Pipeline (M1–M6) Implementation Plan

**Goal:** 임의 키워드 요청 하나로 리서치 → AX 자동화 설계 → 기술 자원 맵 → Future Ahead → 채널 콘텐츠 → 아카이브·학습까지 결정적으로 생성한다.

**Architecture:** 기존 일일 경로(`{date}_brief.md` SoT, M1→M5)는 그대로 두고, `topic` 모드를 병렬 경로로 추가한다. 모든 단계는 `topic_spec.json` 계약을 공유하고, 산출물은 `content/topics/{slug}/`에 격리해 일일 채널 glob(`{date}_linkedin_*.md` 등)과 충돌하지 않는다. LLM 없이 동작하며, 설정 SoT는 `config/topic-research.yaml`.

**Tech Stack:** Python 3.11 · PyYAML · ddgs · urllib(GitHub/arXiv/HN 공개 API) · pytest · bash eval

## Global Constraints

- 일일 파이프라인 SLA(20–26s)·Gate A–D·validate 회귀 금지
- 산출물 파일명: `YYYY-MM-DD_{channel}_{slug}.{ext}` (topic channel = `content/topics/{slug}/`)
- 한국어 · 캐주얼 해요체(블로그는 기존 규칙대로 합니다체) · 출처 URL 필수
- `~/.hermes/.env`·credentials 읽기 금지 — GitHub 토큰은 `GITHUB_TOKEN` 환경변수가 있을 때만 사용
- 오프라인 결정성: `HERMES_TOPIC_FIXTURE=<json>`이면 네트워크 없이 동일 결과

---

## Stage 정의 (topic 모드)

| Stage | 이름 | 모듈 | 산출물 |
|-------|------|------|--------|
| M1 | Discover | `lib/ax/topic_spec.py` · `lens_queries.py` · `sources.py` · `evidence.py` · `brief.py` | `topic_spec.json` · `evidence.json` · `{date}_research_{slug}.md` |
| M2 | AX Blueprint | `lib/ax/blueprint.py` | `{date}_ax-blueprint_{slug}.md/.json` |
| M3 | Resource & Tech Map | `lib/ax/resources.py` | `{date}_resource-map_{slug}.md/.json` |
| M4 | Future Ahead | `lib/ax/future.py` | `{date}_future-ahead_{slug}.md/.json` |
| M5 | Content Execution | `lib/ax/channels.py` | `{date}_{blog,linkedin,newsletter,threads,instagram}_{slug}.md` |
| M6 | Archive & Learn | `lib/ax/memory.py` · Notion `topic_pack` 카테고리 | `{date}_topic-pack_{slug}.md` · `memory.json` · `content/topics/_index.json` · `.harness/topic-lens-feedback.json` |

Gate: `lib/ax/gates.py` — relevance · coverage · diversity · blueprint · future · channel(naturalness) → `gates.json`

## Tasks

### Task 1 (P0): 계약·쿼리·Relevance
- Create `config/topic-research.yaml` (lenses, query templates, sources, domains, intents, value chain, maturity, horizons, gates, tool catalog)
- Create `scripts/lib/ax/{__init__,config,topic_spec,lens_queries}.py`
- Modify `scripts/run-keyword-research.py` — `"{p} enterprise AI"` 고정 접미사 제거, `lens_queries.expand_keyword_queries` 사용
- Test: `tests/test_ax_topic_spec.py` (도메인/의도/slug/동의어, 쿼리에 enterprise AI 강제 없음)

### Task 2 (P1): 멀티소스 + Evidence Pack + Topic Brief
- Create `scripts/lib/ax/{sources,evidence,gates,brief}.py`
- 소스: web/news(ddgs) · github(search API) · arxiv(export API) · hn(Algolia) — 병렬, 실패 격리
- Evidence: 렌즈 태깅, relevance 점수, URL 정규화 dedupe, 신뢰도(소스 가중 + 신선도 + 교차확인)
- Test: `tests/test_ax_evidence.py` (fixture 기반 relevance 필터, coverage/diversity 게이트)

### Task 3 (P2): M2 Blueprint + M3 Resource Map
- Create `scripts/lib/ax/{blueprint,resources}.py`
- Blueprint: 가치사슬 6단계 매핑, 영향도×실행가능성, 성숙도 L0–L4, HITL·KPI·리스크 필수
- Resource Map: 도메인/단계별 카탈로그 + evidence(github/arxiv/docs) + 신선도
- Test: `tests/test_ax_blueprint_resources.py`

### Task 4 (P3): M4 Future Ahead
- Create `scripts/lib/ax/future.py` — Now/Next/Future, 약한 신호(graph.db + 메모리 이력 + evidence 최신성), 2×2 시나리오, 월요일 액션 3개, 예측별 신호 ≥2 + 신뢰도
- Test: `tests/test_ax_future.py`

### Task 5 (P4): M5 채널 + 오케스트레이터
- Create `scripts/lib/ax/channels.py`, `scripts/lib/ax/pipeline.py`, `scripts/run-topic-pack.py`, `scripts/run-topic-pack.sh`
- `--stages M1,M2,...` · `--fixture` · `--no-notion` · traces(`timed_stage`)
- Test: `tests/test_ax_pipeline.py` (fixture E2E, 모든 gate PASS, 파일 생성)

### Task 6 (P5): M6 + Commander
- Create `scripts/lib/ax/memory.py` — delta(신규 URL), 렌즈 적중률 피드백 → 다음 쿼리 가중치
- Modify `config/notion-archive.yaml` (`topic_pack` 카테고리), `scripts/validate-output.sh` (topic-* 타입), `scripts/telegram-pipeline.sh` (`topic` 명령), routing yaml
- Create `scripts/topic-pack-eval.sh`

### Task 7: 문서·회귀
- `docs/architecture/SYSTEM-LOGIC.md` v3.0 섹션, `AGENTS.md` 커맨드, `config/content-orchestration.yaml` topic_stages, `.harness/feature_list.json`, `.harness/progress.md`
- 회귀: pytest · topic-pack-eval · research-keyword-eval · harness-eval --quick · 라이브 E2E 1회
