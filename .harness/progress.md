# Harness Progress — v1.4 통합 컨텍스트 + Notion 구조

## 변경 요약 (2026-06-27, Content Loop P0-2 Supervised Pipeline)

### Supervised Pipeline Cron (L2)
- **`scripts/cron-supervised-pipeline.sh`:** M1→M2→(M2b)→Audit→M5 · triage 이후 10:00
- **기본:** `HERMES_CRON_SKIP_NEWSLETTER=1` (rollout) · M5 sync ON
- **`setup-commander-cron.sh`:** `cron-supervised-pipeline` 평일 10:00
- **산출:** `content/logs/{date}_supervised-pipeline.md` · `.harness/handoffs/{date}_supervised-pipeline.json`

### 검증
```bash
HERMES_CRON_SUPERVISED_DRY_RUN=1 ./scripts/cron-supervised-pipeline.sh
HERMES_CRON_SKIP_NOTION=1 ./scripts/cron-supervised-pipeline.sh   # E2E ~18s exit 0
SKIP_NEWSLETTER=1 SKIP_NOTION_ARCHIVE=1 ./scripts/run-supervised-pipeline.sh $(date +%Y-%m-%d)
./scripts/setup-commander-cron.sh
```

### E2E (2026-06-27)
- M1·GATE·M2 PASS · AUDIT WARN(linkedin/newsletter) · exit 0
- **`pipeline_supervisor.success`:** WARN는 차단하지 않음 (FAIL만 실패)
- **`_finish()`:** early return 시 handoff JSON 항상 기록 (버그 수정)

### 전체 테스트 (2026-06-27)
| 스위트 | 결과 |
|--------|------|
| init · harness-eval --quick | 14/14 ✅ |
| agents-eval A–D | 39/39 ✅ |
| wiki-lint · commander-integration | 9/9 · 28/28 ✅ |
| harness-eval full | 14/14 ✅ (content SLA ⚠️ 회귀) |
| daily-content-triage | ✅ |
| supervised full (M2b+M5) | ✅ ~35s · AUDIT WARN(linkedin) |
| loop-audit | 19/100 L0 (Hermes SoT — 참고용) |

### LinkedIn audit fix (2026-06-27)
- **`quality_auditor`:** feed `validate-output` + `packages/*_linkedin-context` 품질 평가 (마커 분리)
- **`glob_linkedin_feed`:** repurpose `-iN` variant 우선 · supervisor 동기화
- **검증:** `run-quality-audit.sh 2026-06-26` → PASS 7 · FAIL 0

### Longform Blog · Newsletter (2026-06-27)
- **`config/longform-content.yaml`:** 완결 문장·SEO/AEO/GEO 구조 SoT
- **`lib/longform_context.py`:** `build_blog_longform` · `complete_text` · newsletter 모듈 확장
- **`build_blog_html`:** H1·부제·H2×7 · insight deep dive · FAQ JSON-LD (~25KB)
- **`newsletter_quality` / `newsletter_html`:** 모듈 본문 4문장 · Hero 완결형
- **검증:** blog H2=8 · newsletter-eval 10/10 · audit PASS 7

## 변경 요약 (2026-06-27, Content Loop P0-1 Daily Triage)

### Daily Content Triage (L1)
- **`scripts/cron-daily-content-triage.sh`:** Morning · Audit · Health (+ 월: Watch · Agents Eval)
- **`docs/content-loops.md`:** 콘텐츠 루프 cadence · Human Gate · Verifier chain SoT
- **`setup-commander-cron.sh`:** `cron-daily-triage` 평일 09:30
- **Run log:** `.harness/content-loop-runs.jsonl`
- **산출:** `content/logs/{date}_daily-triage.md`

### 검증
```bash
HERMES_TRIAGE_SKIP_AGENTS_EVAL=1 ./scripts/cron-daily-content-triage.sh
./scripts/setup-commander-cron.sh   # cron 등록
cat docs/content-loops.md
```

## 변경 요약 (2026-06-27, M4 Performance Coach Phase D)

### M4 Performance Coach
- **`lib/m4_coach.py`:** CTOR 피드백 → newsletter·linkedin·blog·instagram trait 코칭
- **`config/m4-coach.yaml`:** 채널 trait · propagation 규칙
- **CLI:** `hermes-agent.sh coach --verbose` · `run-m4-coach.sh`
- **산출:** `content/logs/{date}_m4-coach.md` · `.harness/handoffs/{date}_m4-coach.json`

### 검증
```bash
./scripts/agents-eval.sh 2026-06-26          # A–D 통합
./scripts/hermes-agent.sh coach --verbose
./scripts/telegram-pipeline.sh qc coach      # Telegram /coach
./scripts/telegram-pipeline.sh qc agents-eval
```

## Agent 로드맵 완료 (Phase A–D)
| Phase | Agent | 상태 |
|-------|-------|------|
| A | Instagram M3 · Auditor · Repurpose | ✅ pipe-011 |
| B | HITL Scheduler · Pipeline Supervisor | ✅ pipe-012 |
| C | Wiki Curator · Research Squad · Watch | ✅ pipe-013 |
| D | M4 Performance Coach | ✅ pipe-014 |

## 변경 요약 (2026-06-26, 지식·리서치 Agent Phase C)

### Wiki Curator
- **`lib/wiki_curator.py`:** status · seed · lint · ingest 큐 (결정적)
- **`run-wiki-curator.sh`:** `hermes-agent.sh wiki seed|lint|ingest|all`
- **산출:** `content/logs/{date}_wiki-curator-lint.md` · `content/wiki/_ingest_queue.json`

### Research Squad
- **`lib/research_squad.py`:** Scout → Analyst → Curator → Archivist
- **`/deep` 기본:** Research Squad ( `--quick` 시 memory_router만)
- **산출:** `content/research/raw/{date}_squad_*.md`

### Competitive Watch
- **`lib/competitive_watch.py`:** Brief Graph · 엔티티별 신규/상승 streak
- **`config/competitive-watch.yaml`** · **`cron-competitive-watch.sh`** (월 09:00)
- **산출:** `content/logs/{date}_competitive-watch.md`

### 검증
```bash
./scripts/content-knowledge-eval.sh 2026-06-26  # 12/12 PASS
./scripts/hermes-agent.sh wiki lint
./scripts/hermes-agent.sh squad 'AX 트렌드' --date 2026-06-26
./scripts/hermes-agent.sh watch --verbose
```

## 변경 요약 (2026-06-26, 운영 Agent Phase B)

### HITL Publish Scheduler
- **`lib/publish_scheduler.py`:** 예약 생성 · due 시 HITL 카드 · 취소
- **`cron-publish-schedule.sh`:** 15분 cron (`setup-commander-cron.sh`)
- **CLI:** `hermes-agent.sh schedule linkedin --at 09:00` · `schedules` · `schedule --cancel --id ID`

### Pipeline Supervisor
- **`lib/pipeline_supervisor.py`:** M1 → gate → M2 → M2b → audit → M5 단계별 감독
- **`run-supervised-pipeline.sh`:** 실패 시 blocked_at 반환 · handoff JSON
- **산출:** `content/logs/{date}_supervised-pipeline.md`

### 검증
```bash
./scripts/content-ops-eval.sh 2026-06-26
./scripts/hermes-agent.sh schedule linkedin --at +30m --dry-run --date 2026-06-26
SKIP_NEWSLETTER=1 SKIP_NOTION_ARCHIVE=1 ./scripts/run-supervised-pipeline.sh 2026-06-26
```

## 변경 요약 (2026-06-26, 콘텐츠 품질 Agent Phase A)

### Instagram M3 Agent
- **`lib/instagram_pipeline.py`:** analyze → visual-spec → draft (결정적)
- **`run-instagram-pipeline.sh`:** `hermes-agent.sh instagram --validate`
- **산출:** `packages/*_instagram-analysis.md` · `*_instagram-visual-spec.md` · `instagram/*.md`

### Quality Auditor Agent
- **`lib/quality_auditor.py`:** brief_gate + validate-output + newsletter_complete + notion_quality
- **`run-quality-audit.sh`:** `hermes-agent.sh audit`
- **산출:** `content/logs/{date}_audit-report.md`

### Repurpose Agent
- **`lib/repurpose_pipeline.py`:** Brief 인사이트 #N → blog|instagram|linkedin|newsletter 재조립
- **`run-repurpose.sh`:** `hermes-agent.sh repurpose linkedin --index 3`

### 검증
```bash
./scripts/content-quality-eval.sh 2026-06-26  # 12/12 PASS
./scripts/hermes-agent.sh instagram --date 2026-06-26
./scripts/hermes-agent.sh audit --date 2026-06-26
./scripts/hermes-agent.sh repurpose linkedin --index 1 --date 2026-06-26
```

## 변경 요약 (2026-06-16, 우선순위 P1–P8 기능 패키지)

### P1 — CTOR → 제목 스코어링 피드백
- **`lib/newsletter_ctor_feedback.py`:** trait 가중치 · `score_subject_line` 보너스
- **`newsletter_ctor.record_campaign`:** 피드백·M4 동기화 트리거
- **산출:** `subject-scores.json` · `ctor_feedback` 필드

### P2 — HITL newsletter 발행 통합
- **`agent-commands.yaml`:** publish channels + newsletter
- **`hermes-agent.sh publish newsletter`:** paste pack HITL 카드
- **`publish_gate`:** newsletter validate + Notion `--notify-final`

### P3 — Wiki → M2 concept 주입
- **`lib/wiki_concepts.py`:** `inject_wiki_blurbs` → blog·instagram·linkedin
- **`assemble-content-package.py`:** 결정적 wiki 맥락 블록

### P4 — Proactive + 주간 Graph digest
- **`proactive_triggers`:** newsletter_paste · ctor_stale · watch_telegram
- **`brief_graph.format_weekly_digest`:** 반복·신규·공백 topic
- **`cron-weekly-graph-digest.sh`:** 월 09:00 (`setup-commander-cron.sh`)

### P5 — Blog M3 서브파이프라인
- **`lib/blog_pipeline.py`:** seo → structure → validate
- **`run-blog-pipeline.sh`:** `hermes-agent.sh blog`

### P6 — M4 실측 1채널
- **`lib/m4_channel_metrics.py`:** CTOR → channel-metrics · `m4-import-metrics.sh`
- **`content-orchestration.yaml`:** M4 `live_when_metrics`

### P7 — PlayMCP Commander
- **`config/playmcp-routing.yaml`:** quick_commands 14개
- **`setup-playmcp-routing.sh`:** `setup-playmcp.sh` [8/8] 연동
- **`playmcp-integration-eval.sh`**

### P8 — ESP controlled live
- **`newsletter-send.sh`:** dry-run 기본 · `--live` HITL 필수
- **`newsletter.yaml` esp:** `HERMES_ESP_APPROVED` + `RESEND_API_KEY`
- **`hermes-agent.sh approve esp`**

### 검증
```bash
./scripts/features-priority-eval.sh
./scripts/playmcp-integration-eval.sh
./scripts/hermes-agent.sh publish newsletter --dry-run --date YYYY-MM-DD
```

## 변경 요약 (2026-06-10, Newsletter Quality 강화 + Notion 동기화)

### Newsletter 완성도
- **`lib/newsletter_complete.py`:** 잘림·미완성 감사 (`audit_newsletter_md`)
- **`newsletter_quality.py`:** `truncate` → `compress_sentences`/`finish_at_sentence` · `_newsletter_title`
- **`newsletter_html.py`:** HTML 모듈 동일 완결 문장 정책
- **`validate-output.sh` · `newsletter-eval.sh`:** completeness 게이트 추가
- **`content_quality.py`:** garbage title 패턴 (OpenAI News 중복 등)

### Notion M5
- **`archive-to-notion.sh 2026-06-10 --force --notify-final`** — 8페이지 canonical score 100
- Daily: https://app.notion.com/p/37bfb3b5e389811e8ebad3a3bb11794a

### 검증
- `newsletter-eval.sh 2026-06-10` — **10/10 PASS** (completeness_no_truncation 포함)

## 변경 요약 (2026-06-10, LLM Wiki 부분 통합)

### 결론
- **일별 콘텐츠 공장(M1→M5) 유지** · **누적 wiki 계층**만 선택 도입 (전면 Wiki 교체 없음)

### 선택 (도입)
- **`memory_router`:** wiki index-first (`lib/wiki_router.py`)
- **결정적 Seed:** Brief Graph → `content/wiki/concepts/` (`HERMES_WIKI_SEED=1` · `wiki-seed.sh`)
- **LLM Ingest/Lint:** 비동기 옵션 (`HERMES_WIKI_INGEST=1` · `HERMES_WIKI_LINT=1`)

### 유지
- M1→M2→M2b→M5 결정적 SLA · `{date}_brief.md` SoT · validate · Notion Permalink

### 신설
- **`docs/LLM-WIKI-INTEGRATION.md`** · **`config/wiki.yaml`** · **`skills/shared/wiki-maintainer/`**
- **`content/wiki/`** (index · log · concepts · output) · **`content/research/raw/`**
- **`wiki-lint-eval.sh`** · feature **pipe-009**

### 검증
```bash
./scripts/wiki-lint-eval.sh
HERMES_WIKI_SEED=1 ./scripts/wiki-seed.sh
```

## 변경 요약 (2026-06-08, Cursor Agent 리소스 Notion)

- **로컬 MD:** `content/logs/2026-06-08_cursor-agent-resources.md` — Cursor transcript 기반 토큰·시간·스킬 맵
- **Notion:** https://app.notion.com/p/379fb3b5e38981a4ba83f2a9d3af9979
- **export:** `export-architecture-notion.py` — `cursor` 페이지 추가 · 기존 resources/diagrams replace
- **state:** `content/.notion-architecture-state.json`

## 변경 요약 (2026-06-08, Notion archived ancestor 복구)

- **원인:** 기존 `2026-06-08` Daily/카테고리 페이지가 Notion 보관(archive) 상태 → update/create 400
- **수정:** `archive-to-notion.py` — `is_archived_notion_error` · `clear_stamp_notion_state` · `upsert_category_page` · `--reset-notion-state`
- **복구:** `--reset-notion-state --force` → Daily `https://app.notion.com/p/379fb3b5e389815cab0ae900fd564b0b` · 8페이지 동기화

## 변경 요약 (2026-06-08, Brief·Unified 맥락 완결형)

### Research Brief → Unified Context 맥락 단절 수정
- **`compress_sentences` / `finish_at_sentence`** (`lib/common.py`) — 중간 `…` 잘림 대신 완결 문장 압축
- **`context_blurb` · `polish_display_title` · `has_meaningful_korean`** (`content_quality.py`) — 한국어 제목·요약 연속성
- **`TITLE_BY_TOPIC` · insight_derivation 보강** (`brief_quality.py`) — 영문 조각 제목·반복 템플릿 제거
- **재생성:** `2026-06-08_brief.md` · `2026-06-08_unified-context.md` · validate PASS

## 변경 요약 (2026-06-08, Studio 아키텍처 Notion·MD)

### 운영 리소스 · 의존성 다이어그램
- **로컬 MD:** `content/logs/2026-06-08_studio-resources-spec.md` · `studio-dependency-diagrams.md` · `studio-architecture-guide.md`
- **Notion 별도 페이지 (Daily Archive 루트 하위):**
  - [운영 리소스·기술 스펙](https://app.notion.com/p/379fb3b5e389810f9630cd8cbfed942b)
  - [의존성 다이어그램](https://app.notion.com/p/379fb3b5e38981c2a947ec8af87330b4)
- **재동기화:** `scripts/export-architecture-notion.sh` · state `content/.notion-architecture-state.json`

## 변경 요약 (2026-06-08, Commander Phases 1–4)

### Phase 1 — 자동 모닝 · 헬스 알림
- **`cron-morning-brief.sh`** · **`cron-health-alert.sh`** · **`lib/runtime_health.py`**
- **`setup-commander-cron.sh`** — hermes cron `--no-agent` (평일 09:00 · 10:00/18:00) → Telegram deliver
- **`lib/commander_notify.sh`** — Telegram + Slack 공용 알림

### Phase 2 — /ask + Brief Graph
- **`memory_router.py`:** 14일 brief 히스토리 · graph streak 검색 · Graph 섹션 출력
- **`hermes-agent.sh ask`** — route alias

### Phase 3 — HITL 발행
- **`publish_gate.py`:** `format_telegram_approval` · `format_pending_status`
- **`/pending`** quick_command · publish/approve 시 commander_notify

### Phase 4 — Slack Commander 동등화
- **`slack-routing.yaml`** — Telegram quick_commands 25개 동일 · intent prompt
- **`setup-slack-routing.sh`** 갱신

### 검증
- **`commander-phases-eval.sh`** 13/13 PASS
- cron 등록: `setup-commander-cron.sh` (스크립트는 `~/.hermes/scripts/` 실제 복사본)

## 변경 요약 (2026-06-08, Telegram /morning 슬래시 등록)

### Unrecognized slash command 해결
- **원인:** `/morning` · `/newsletter` 등 intent-pack이 `quick_commands`에 미등록 → gateway unknown-command
- **수정:** `telegram-routing.yaml` + `telegram-pipeline.sh qc` (morning/catch-up/publish/linkedin/traces/handoff/graph/commands/approve)
- **적용:** `setup-telegram-routing.sh` → `~/.hermes/config.yaml` · gateway restart
- **eval:** commander-integration-eval 28/28 PASS

## 변경 요약 (2026-06-08, Telegram 2026-06-05 중복 재발 수정)

### 근본 원인
- **watch-telegram 7중 실행** (Fri/Sun 수동·start-services 중복)
- watch가 `[Notion Archive] 시작: 2026-06-05` 로그마다 **sync lock을 과거 날짜로 덮어씀**
- 병렬 archive(2026-06-05 + 2026-06-08) → Telegram에 **2026-06-05 Permalink** 전송

### 수정
- **`kill-stale-watch-telegram.sh`** · **`start-services.sh`:** 기동 전 중복 watch 정리 (macOS `ps|rg` 호환)
- **`watch-telegram`:** post-sync **기본 OFF** (`HERMES_WATCH_POST_SYNC=1`만 대화형) · 로그 기반 `telegram_sync_begin` **제거**
- **`archive-to-notion.sh`:** `REQUESTED_DATE` 파싱(DATE env 오염 방지) · Telegram/`--notify-final` 시 **commander 날짜 보정** · flock/PID lock
- **`telegram_sync_guard`:** lock **다운그레이드 금지** (2026-06-08 lock 유지)
- **`commander-integration-eval.sh`:** 25/25 PASS

### 운영
```bash
~/hermes-content-studio/scripts/kill-stale-watch-telegram.sh   # 중복 watch 정리
~/hermes-content-studio/scripts/start-services.sh              # 단일 watch 재기동
# Telegram: /sync 1회 → stamp=오늘(2026-06-08) Permalink 1건만
```

## 변경 요약 (2026-06-08, Commander 통합 점검 · Telegram sync 수정)

### Telegram 슬래시 Notion 중복 수정
- **`studio_commander_date`:** 오늘 → 최신 brief 1건 (2026-06-05 고정 출력 방지)
- **`telegram_sync_guard`:** 파이프라인 sync 중 watch post-sync skip
- **`watch-telegram`:** 슬래시(`/pipeline` 등) 응답 시 agent post-sync skip
- **`pages_for_stamp`:** 타 날짜 fallback 제거 · completion 1 stamp만
- **`notify_dedupe`:** 동일 chat+stamp 알림 120s 억제
- **`commander-integration-eval.sh`**

## 변경 요약 (2026-06-08, P6 Notion 붙여넣기 팩)

### P6 — 배포 워크플로 (ESP 없음)
- **`lib/newsletter_paste.py`:** §1 제목 · §2 프리헤더 · §3 MD · §4 HTML 코드 블록
- **`content/packages/{date}_newsletter-paste.md`** · Notion `newsletter_paste` 채널 (order 8)
- **`config/newsletter.yaml`:** `delivery.mode: notion_paste` · `esp_send: false`
- **`newsletter-p6-eval.sh`** · e2e newsletter-paste 게이트 · Notion 8페이지

### 워크플로 (유지)
1. `run-newsletter.sh --validate` → paste 팩 생성
2. `archive-to-notion.sh --force` → Notion Newsletter Paste
3. Notion 코드 블록 **복사** → 스티비·센드그리드 등 문서 편집기 붙여넣기

## 변경 요약 (2026-06-08, P4–P5 CTOR·LinkedIn)

### P4 — CTOR 실측 + LinkedIn 팩트체크
- **`lib/newsletter_ctor.py`:** delivered/opens/clicks → CTOR · `.harness/newsletter-ctor-metrics.json`
- **`newsletter-ctor-record.sh` / `newsletter-ctor-dashboard.sh`:** HTML+MD 대시보드 (`content/logs/`)
- **`build_linkedin_context_md`:** `## 출처` URL → Notion **canonical (score 100)**
- **`newsletter-p4-eval.sh`:** 7/7 PASS

### Notion (2026-06-08 갱신)
- LinkedIn: https://www.notion.so/379fb3b5e3898117b646d966482999db (canonical)

## 변경 요약 (2026-06-08, P3 마감 + Notion 동기화)

### Notion 동기화 (2026-06-08)
- **7페이지** canonical · newsletter + newsletter_html 갱신
- Newsletter: https://www.notion.so/379fb3b5e389814f9a9fc065ce583fe1
- Newsletter HTML: https://www.notion.so/379fb3b5e389812b8b34df8e6c62c640

### P3 — 문서·M4·eval 마감
- **`m4_analytics.newsletter_kpis`** · `run-newsletter.sh` trace
- **`harness-eval.sh` full:** newsletter 타이밍·회귀
- **`newsletter-p3-eval.sh`** · README/HARNESS · feature_list 갱신

## 변경 요약 (2026-06-08, P2 뉴스레터 고도화)

### P2 구현
- **`newsletter.yaml` 로더:** subject_templates · scoring · outputs(html/scores) → 코드 연동
- **`patch_unified_context_newsletter`:** unified에 권장 제목·경로 · `unified-newsletter` 게이트
- **`slack-daily-log`:** Newsletter Context · MD/HTML 산출물
- **`publish_gate`:** newsletter HITL 채널 · `run-newsletter` 발행 경로
- **`skills/channels/newsletter/SKILL.md`**
- **`newsletter-p2-eval.sh`:** 9/9 PASS

### 검증
- `newsletter-p2-eval.sh 2026-06-08` · `e2e-smoke-test` 12/12 · `archive-to-notion --force`

## 변경 요약 (2026-06-08, P0 파이프라인 연동)

### P0 — 주간 오케스트레이션
- **`run-pipeline.sh`:** M2b `run-newsletter.sh --validate` (SKIP_NEWSLETTER=1로 제외)
- **`e2e-smoke-test.sh`:** newsletter 4게이트 + 파이프라인 SLA 70s
- **`content-orchestration.yaml`:** M2b · newsletter_pipeline · daily M1+M2+M2b+M5

### P1 — Telegram·문서·Notion 상태
- **`telegram-pipeline.sh`:** run_newsletter · qc newsletter · /pipeline에 M2b 포함
- **`telegram-routing.yaml`:** `/newsletter` quick command
- **`AGENTS.md`:** newsletter 채널·실행·품질 게이트
- **`notion_hygiene.resolve_state_page`:** `@draft` state fallback (false missing 제거)

### 검증
- `e2e-smoke-test.sh 2026-06-08` — 12/12 PASS
- `newsletter-eval.sh` — 9/9 PASS

## 변경 요약 (2026-06-08, B2B 뉴스레터 확장)

### Step 1 — A/B 제목 자동 스코어링
- **`lib/newsletter_subject.py`:** Stripo 휴리스틱 (길이·질문형·스팸·B2B 키워드)
- 산출: `content/newsletter/{date}_newsletter_subject-scores.json`
- MD 본문: 스코어 테이블 + ⭐ 권장 제목

### Step 2 — HTML 이메일 템플릿
- **`templates/email/newsletter.html`:** 모바일 단일 컬럼 · table layout · preheader
- **`lib/newsletter_html.py`:** TLDR/Hero/모듈/CTA 모듈 조립
- 산출: `content/newsletter/{date}_newsletter_{slug}.html`

### Step 3 — Notion 아카이브 채널
- **`config/notion-archive.yaml`:** `newsletter` (context) · `newsletter_html` (order 6–7)
- **`notion_quality.py` / `notify_format.py` / `archive-to-notion.py`** 연동

### 설계 (오픈율·완독율/CTOR)
- **근거:** Stripo B2B 2026 · ClickMinded · Morning Brew modular · Dyspatch
- **구조:** TLDR 3불릿 → Hero → 모듈×3 → Grab Bag → Single CTA → 다음 호 예고
- **설정:** `config/newsletter.yaml` · `config/content-guidelines.yaml#newsletter`

### 구현
- **`lib/newsletter_quality.py`:** `assemble_newsletter()` → md + html + scores
- **`run-newsletter.sh` / `assemble-newsletter.py`:** Brief SoT → `content/newsletter/`
- **`validate-output.sh`:** newsletter · context · html · subject-scores 게이트
- **`hermes-agent.sh newsletter`:** `/newsletter` intent

### Harness 등록
- **`feature_list.json` pipe-008:** B2B 뉴스레터 파이프라인 (area: newsletter, status: passing)
- **`harness.yaml`:** SLA newsletter 10s · post_stage 4게이트 · eval baseline 5s

### 검증
- **`newsletter-eval.sh`:** 9/9 PASS · `content/logs/2026-06-08_newsletter-eval-report.md`
- Notion 동기화 완료 (2026-06-08): 7페이지 · newsletter + newsletter_html canonical
  - Daily: https://app.notion.com/p/379fb3b5e38981d2b8ecc42bea10db1d
  - Newsletter: https://app.notion.com/p/379fb3b5e389814f9a9fc065ce583fe1
  - Newsletter HTML: https://app.notion.com/p/379fb3b5e389812b8b34df8e6c62c640

## 변경 요약 (2026-06-08, Phase 3 Agent 고도화)

### Command Registry (agent-native parity)
- **`lib/command_registry.py`:** intent packs + script commands 단일 SoT
- **`config/agent-commands.yaml` v3.0:** `commands:` pipeline · notion-sync · research · content · slack-digest
- **`hermes-agent.py commands` / `run <id>`:** CLI·Telegram·Cursor 동일 진입점

### Brief Graph Lite
- **`lib/brief_graph.py`:** topic_key streak · `_brief_graph.json` · unified context **이전 브리프와의 차이** 열
- **`hermes-agent.py graph --write-unified`:** packages unified-context Graph 표 반영

### HITL Publish Gate
- **`lib/publish_gate.py`:** `.harness/publish-queue/{stamp}.json` · 승인 카드
- **`publish` (기본):** HITL 대기 · **`--approve` / `approve`:** 발행 실행

### 검증
- **`phase3-eval.sh`:** 7/7 PASS · Phase 2 regression OK
- **E2E 2026-06-08:** `e2e-smoke-test` 7/7 · `--telegram` 11/11 · Agent+HITL 8/8
- 리포트: `content/logs/2026-06-08_e2e-full-report.md`
- **fix:** `hermes-agent auto` — graph/traces 등 서브커맨드 기본 인자 (`_auto_defaults`)

## 변경 요약 (2026-06-08, Phase 2 Agent 고도화)

### M4 Traces 실측화
- **`lib/m4_analytics.py`:** traces 집계 · SLA breach · Notion tier · `m4-snapshot.json`
- **`hermes-agent.py traces`:** M4 리포트 · agent intent trace 기록

### LinkedIn M3 Sub-pipeline
- **`lib/linkedin_pipeline.py`:** analyze → strategy → draft (결정적)
- **`run-linkedin-pipeline.sh`:** `packages/*_linkedin-analysis.md` · `*_linkedin-strategy.md` · context M3 섹션
- **`hermes-agent.py linkedin`:** Telegram `/linkedin` 라우팅

### Session Handoff 고도화
- **`lib/session_handoff.py`:** `format_resume_block()` · `write_session_handoff()` → `.harness/session-handoff.md`
- **`hermes-agent.py handoff`:** 이어하기 명령 + M4 embed

### 검증
- **`phase2-eval.sh`:** 8/8 PASS · Phase 1 regression OK
- 리포트: `content/logs/2026-06-07_phase2-eval-report.md`
- **다음:** Phase 3 — command registry · Brief Graph · HITL publish gate

## 변경 요약 (2026-06-08, Phase 1 Agent 고도화)

### 우선순위 1 — Memory Router + Intent Pack
- **`config/agent-commands.yaml`:** morning · catch-up · publish · deep · ask intent pack
- **`lib/memory_router.py`:** brief → packages → personal → notion_state 우선 질의 · `skip_web_search`
- **`hermes-agent.py` / `hermes-agent.sh`:** route · morning · catch-up · publish · deep · proactive · bridge-sync · session · auto
- **`telegram-pipeline.sh`:** `/morning` · `/catch-up` · publish · deep · ask · intent-pack 라우팅

### 우선순위 2 — Brief ↔ Personal Bridge
- **`lib/personal_bridge.py`:** `_inbox_candidates.json` · `sync_inbox_from_personal()` · `queue_topic_for_brief()`

### 우선순위 3 — Session SoT + Proactive
- **`lib/session_sot.py`:** `.harness/sessions/{id}.json` · `record_action()` · `resume_hint()`
- **`lib/proactive_triggers.py`:** brief_freshness · notion_stale (24h) 체크
- **`archive-to-notion.py`:** 페이지 state `synced_at` (proactive용)

### 검증
- **`phase1-eval.sh`:** 8/8 PASS · 리포트 `content/logs/2026-06-07_phase1-eval-report.md`
- memory_router 5.4ms · harness-eval --quick OK
- **다음:** Phase 2 — M4 traces · LinkedIn sub-pipeline · Session handoff 고도화

## 변경 요약 (2026-06-08, Notion Fact-check 게이트)

### Notion 아카이브
- **`notion_quality.py`:** Notion 반영 전 `fact_check` 게이트 추가 — 출처 URL·수치 주장·최상급/절대 표현 검증
- **Draft 분기:** Fact-check 이슈가 있으면 canonical 대신 Draft Archive 반영
- **`notion_templates.py`:** Notion 페이지 상단 메타에 팩트체크 통과/보류·이슈 표기
- **검증:** py_compile 통과 · `harness-eval --quick` 9/9 PASS · 2026-06-08 Notion force sync 5페이지 완료


## 변경 요약 (2026-06-07, Notion 템플릿 · 알림 포맷)

### Notion 아카이브
- **`lib/notion_templates.py`:** blog 평문 → `##` 헤딩 정규화 · LinkedIn `## CTA` · callout 메타 블록
- **품질:** blog/linkedin/instagram canonical score 100 (기존 draft 분기 해소)
- **`build_blog_article_md`:** 소스부터 `## 한 줄 요약` · `## FAQ` 등 구조화

### Telegram · Slack 알림
- **`lib/notify_format.py`:** 5단계 progress bar 통일 · `format_completion()` 단일 최종 메시지
- **`--notify-final`:** `telegram-post-sync.sh` → 중간 1~4/5 중복 제거, 5/5 Permalink 1회
- **Slack `#일반데이터`:** `--summary-only` compact digest (888 chars) · 전문은 `content/logs/*_daily-slack-digest.md`
- **검증:** Slack summary 전송 ✅ · Notion force sync 5페이지 score 100 ✅

### Notion Instagram/LinkedIn Gemini 프롬프트
- **`instagram_carousel_spec` / `append_instagram_gemini_prompts`:** channel md · Notion context 공용
- **`build_instagram_context_md`:** Slide 1~3 전문 Gemini 프롬프트 포함 (요약 stub 제거)
- **`build_linkedin_context_md`:** 포스트 초안 + `## Gemini 이미지 생성 프롬프트` 분리 섹션
- **validate:** instagram-context Slide 3개 · linkedin-context gemini-3-pro-image-preview 게이트

### Unified Context · Telegram 알림 v2
- **Research Brief 발췌:** Top 7 표 (`| # | 인사이트 | 핵심 요약 | 마케터 관점 | 출처 |`)
- **Telegram:** `📅 {stamp}` + `📝 업데이트 요약` + 갱신 Permalink만 (`--notify-final`)
- **검증:** 2026-06-07 pipeline 25s · Notion 5페이지 score 100 ✅

## 변경 요약 (2026-06-07, Brief SoT · 일일 최신 → M2)

### Brief 우선 파이프라인
- **SoT:** `_search_context_{date}.json` → `{date}_brief.md` → blog · instagram · linkedin
- **일일 수집:** 쿼리 `{year}` 템플릿 · ddgs `timelimit=week` · min 7건
- **M2 게이트:** `lib/brief_gate.py` · `run-content-package.sh` 당일 brief 자동 선행
- **검증:** M2 전 Top 7 · instagram · linkedin 채널 파일 validate

## 변경 요약 (2026-06-07, Brief Top 7 · 일일 렌즈)

### Research Brief v2.1
- **Top 7:** `INSIGHT_LIMIT=7` · priority query 다양성 pick · validate 7개 게이트
- **일일 수집:** `gather-web-research.py` period = today (단일일)
- **일일 cron:** `daily-research-brief` 매일 08:00 (`studio.yaml` · `setup-cron.sh`)
- **마케터 톤:** 1인칭 현장 서술 (저는·현장에서) · 중복 방지 `used_views`
- **품질 필터:** Wikipedia·스팸 URL 제외 · 한국 쿼리 relevance 게이트
- **다운스트림:** `content_quality.py` Top 7 동기화 · blog/unified-context 7건

## 변경 요약 (2026-06-06, Brief v2 — 21년차 AI·AX 페르소나)

### Research Brief v2
- **페르소나:** 21년차 디지털 마케터 · AI 리터러시·거버넌스·AX·AI Native 컨설턴트
- **커버리지:** LLM 4사 · AX · 거버넌스 · 에이전트 · 하네스 · Repo · 일일 글로벌·한국 렌즈
- **Insight 파이프:** 리서치 → 내용 요약 → Insight 도출 → 활용 방법 → 가이드·팁
- **설정:** `config/research-brief.yaml` · `gather-web-research.py` 쿼리 확장
- **신규 섹션:** 페르소나 · 리서치 커버리지 · LLM 펄스 · AX·AI Native · 실무 가이드 하이라이트

## 변경 요약 (2026-06-06, Brief 품질 v2.1)

### Research Brief (`brief_quality.py`)
- **신규:** `scripts/lib/brief_quality.py` — topic_key별 한국어 요약·마케터 관점·시장영향·한국적용·기회
- **금지:** generic `"재해석해 적용"` 일괄 fallback · 영문 스니펫 **요약** 필드 붙여넣기
- **필드:** 한국어 제목, 신뢰도(high/medium/low), 인사이트별 차별화 SCQA
- **검증:** `validate-output.sh research` — 마케터 관점 중복·한국어 요약 글자수 게이트

## 변경 요약 (2026-06-06, 콘텐츠 톤·포맷 v2)

### Blog / LinkedIn 산출물
- **Blog:** LinkedIn형 평문 · ~합니다 · 출처 기반 확장 본문 · 실무 적용 topic별 재구성
- **LinkedIn:** 해요체 포스트 + Gemini Nano Banana Pro 2 · 1:1 · 2×2 웹툰 프롬프트

## 변경 요약 (2026-06-06, im-not-ai 문체)

### Voice / Humanize
- **upstream:** [im-not-ai](https://github.com/epoko77-ai/im-not-ai) quick-rules 기반
- **결정적:** `scripts/lib/humanize_korean.py` — M2 assemble 시 blog·linkedin 자동 적용
- **설정:** `config/voice-style.yaml` · skill `shared/humanize-korean`
- **register:** blog=semi_formal (~다), linkedin=1인칭 전문가
- **선택 LLM:** `HERMES_HUMANIZE=1` → upstream humanize-korean skill

## 변경 요약 (2026-06-06, 콘텐츠 오케스트레이션 v1.0)

### Skill 재구성 (1차)
- **마스터:** `skills/content-orchestration/` — M1~M5 ([marketing-ai-orchestration-harness](https://github.com/saewookkangboy/marketing-ai-orchestration-harness))
- **채널:** `skills/channels/{research,blog,instagram,linkedin}/` — P0~P5 Phase
- **LinkedIn M3:** analyze→strategy→draft→validate ([linkedin-feed-strategy-maker](https://github.com/saewookkangboy/linkedin-feed-strategy-maker))
- **프롬프트:** `skills/prompts/strategy-frameworks.md` ([strategy-prompts](https://github.com/saewookkangboy/strategy-prompts))
- **공통:** `skills/shared/{handoff,validate}/`
- **스키마:** `schemas/handoff.schema.json`, `schemas/content-input.schema.json`
- **설정:** `config/content-orchestration.yaml`
- **라우터:** `content-pipeline` v1.3.0 (슬림화), `marketing-research` v1.2.0 (M1 alias)

### harness-100 패턴
- Orchestrator / Channel / Shared 3-layer
- Scale modes: full | reduced | single_channel | enhance

## 변경 요약 (2026-06-06, Cursor CLI)

### Cursor Agent CLI 자동화
- **설치:** `install-cursor-cli.sh` — cursor-agent + IDE symlink
- **버전:** `cursor_cli_version()` — `cursor_cli_resolve_agent` + `--version`, 미설치 시 빈 문자열
- **실행:** `run-cursor-handoff.sh --latest|--handoff PATH [--background]`
- **Telegram /automate:** Codex HANDOFF 생성 → `run-cursor-handoff --background` (HERMES_CURSOR_AUTO=1)
- **헬스체크:** cursor-agent, run-cursor-handoff ✅

## 변경 요약 (2026-06-06)

### Notion Hygiene v1.5
- **중복 정리:** 카테고리당 canonical 1페이지 유지, 나머지 → `Draft & Incomplete Archive`
- **미완성 분리:** 품질 점수 미달(TODO/본문부족/필수섹션 누락) → 보관 페이지에만 동기화
- **최신 교체:** `replace_content`로 canonical 페이지 본문 전체 갱신
- **점검 명령:** `check-notion-status.sh [DATE] [--fix] [--json]`
- **Telegram:** `/notion-status` `/notion-fix`

## 변경 요약 (2026-06-06, 이전)

### 성능·안정화 (에이전트 eval)
- **harness-eval --record:** research 8s, content 1s, full 9s (baseline 대비 -80%, 회귀 없음)
- **e2e-smoke-test --telegram:** 11/11 PASS (파이프라인 10s, Notion 22s)
- **pipe-006 안정화:** `qc pipeline` Notion sync → sync-bg (14s, Hermes command_timeout 30s 준수)
- **활성 기능:** pipe-006 → **passing**

### 콘텐츠
- **Research Brief:** 심층 분석·SEO/AEO/GEO 키워드맵·통합 컨텍스트 섹션 추가
- **Blog:** `content/packages/{date}_blog-article.md` — ~합니다 평문·AEO/GEO·출처 기반 확장
- **Instagram/LinkedIn:** Notion용 `*_context.md` (플랫폼 최적화 컨텍스트, 캐러셀/포스트 핵심만)
- **Unified Context:** Daily Archive 인덱스용 통합 문서

### Notion
- 날짜별 Daily → 카테고리당 **1개 하위 페이지** (분할 과다 해소)
- 순서: Unified → Research → Blog → Instagram → LinkedIn
- Lecture는 `/lecture` 시에만 Outline·HTML 페이지 생성

### Telegram
- `/pipeline` — research + content + sync (**강의 제외**)
- `/lecture-studio <요구사항>` — 자연어 → Outline + HTML → Notion

### Slack (신규)
- `/pipeline` — Telegram과 동일 quick_commands (`setup-slack-routing.sh`)
- 홈 채널 `#일반데이터` (`C0B8CN2EA05`) — free_response, 진행·Permalink Slack 알림
- `slack-notify.sh` + `archive-to-notion.py --slack-channel`
- **`slack-daily-log.sh`** — 일일 pipeline log + 콘텐츠 전문 → Slack (`content/logs/{date}_daily-slack-digest.md`)

## 검증

```bash
./scripts/check-notion-status.sh 2026-06-06
./scripts/check-notion-status.sh 2026-06-05 --fix   # 중복 Draft 이동
./scripts/archive-to-notion.sh 2026-06-06 --hygiene-only
./scripts/harness-eval.sh --record
./scripts/e2e-smoke-test.sh --telegram
./scripts/telegram-pipeline.sh qc pipeline   # ≤15s + Notion sync-bg
./scripts/setup-slack-routing.sh             # Slack /pipeline 라우팅
./scripts/validate-output.sh research content/research/2026-06-06_brief.md
```
