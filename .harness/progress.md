# Harness Progress — v1.4 통합 컨텍스트 + Notion 구조

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
