# Hermes Content Studio — Agent Context

Intel Mac 자체호스팅 마케팅·교육 콘텐츠 스튜디오.
Harness v1.2.0 — [awesome-harness-engineering](https://github.com/walkinglabs/awesome-harness-engineering)

## 세션 시작 (필수)

```bash
~/hermes-content-studio/scripts/init.sh
cat ~/hermes-content-studio/.harness/progress.md
```

상세: `HARNESS.md` · 설정: `config/harness.yaml`

## 워크스페이스 규칙

- 모든 산출물: `~/hermes-content-studio/content/{channel}/`
- 디자인 시스템: `Getdesign.md` 필수 참조
- 파일명: `YYYY-MM-DD_{channel}_{slug}.{ext}`
- 언어: 한국어 (기술 용어 영문 병기)
- 톤: 캐주얼 구어 해요체 (~해요, ~돼요) — im-not-ai AI 티만 제거

## 실행 (커맨더)

```bash
# 하네스 부트스트랩 (세션 시작)
~/hermes-content-studio/scripts/init.sh

# 성능 eval (구조·벤치마크)
~/hermes-content-studio/scripts/harness-eval.sh --quick

# E2E 사용성·성능 스모크 (Telegram 포함)
~/hermes-content-studio/scripts/e2e-smoke-test.sh --telegram

# 리서치 브리프 (결정적, ~15s)
~/hermes-content-studio/scripts/run-research-brief.sh

# 전체 파이프라인 (결정적, M1+M2+M2b ~70s)
~/hermes-content-studio/scripts/run-pipeline.sh
# SKIP_NEWSLETTER=1 ~/hermes-content-studio/scripts/run-pipeline.sh  # 뉴스레터 제외

# B2B 뉴스레터 (Brief SoT → md + HTML + A/B 제목, ~10s)
~/hermes-content-studio/scripts/run-newsletter.sh [YYYY-MM-DD] --validate
~/hermes-content-studio/scripts/hermes-agent.sh newsletter --date YYYY-MM-DD --validate
~/hermes-content-studio/scripts/newsletter-eval.sh [YYYY-MM-DD]
~/hermes-content-studio/scripts/newsletter-ctor-record.sh YYYY-MM-DD --delivered N --opens N --clicks N
~/hermes-content-studio/scripts/newsletter-ctor-dashboard.sh [YYYY-MM-DD]
# 배포: Notion 붙여넣기 팩 → 외부 플랫폼 (ESP 발송 없음)
# content/packages/{date}_newsletter-paste.md · Notion Newsletter Paste 페이지
~/hermes-content-studio/scripts/commander-integration-eval.sh   # Telegram/Slack/Harness 점검

# 스튜디오 업데이트 (Hermes + 의존성 + 헬스체크)
~/hermes-content-studio/scripts/update-studio.sh

# 상태 표시바 + Hermes (단일 작업)
~/hermes-content-studio/scripts/hermes-run.sh \
  "이번 주 리서치 브리프 작성" --skills marketing-research

# Telegram 요청 진행 상황 (start-services.sh가 백그라운드 시작)
~/hermes-content-studio/scripts/watch-telegram.sh

# Telegram 결정적 파이프라인 (LLM 없음)
~/hermes-content-studio/scripts/telegram-pipeline.sh pipeline

# Slack 결정적 파이프라인 + 일일 digest (#일반데이터)
~/hermes-content-studio/scripts/setup-slack.sh
~/hermes-content-studio/scripts/setup-slack-routing.sh
~/hermes-content-studio/scripts/slack-daily-log.sh              # 오늘 전문 digest → Slack
~/hermes-content-studio/scripts/slack-daily-log.sh --build-only # 로컬만 저장

# Telegram 개인화 (Codex · 백그라운드)
~/hermes-content-studio/scripts/telegram-custom.sh mail "받편함 요약"
~/hermes-content-studio/scripts/setup-telegram-routing.sh

# Cursor Agent CLI (HANDOFF 자동 실행)
~/hermes-content-studio/scripts/install-cursor-cli.sh
~/hermes-content-studio/scripts/run-cursor-handoff.sh --latest
# /automate → Codex HANDOFF → run-cursor-handoff --background (HERMES_CURSOR_AUTO=1)

# Notion 일자별 아카이브
~/hermes-content-studio/scripts/archive-to-notion.sh [YYYY-MM-DD]

# Studio 아키텍처 → Notion (운영 리소스·의존성·Cursor 맵)
~/hermes-content-studio/scripts/export-architecture-notion.sh

# Voice · Naturalness (결정적 품질 게이트)
~/hermes-content-studio/scripts/voice-style-eval.sh [YYYY-MM-DD]
~/hermes-content-studio/scripts/naturalness-eval.sh [YYYY-MM-DD]
~/hermes-content-studio/scripts/loop-budget-eval.sh
~/hermes-content-studio/scripts/loop-budget-status.sh
~/hermes-content-studio/scripts/humanize-llm-eval.sh [YYYY-MM-DD]
HERMES_HUMANIZE_LLM_LIVE=1 ~/hermes-content-studio/scripts/humanize-llm-eval.sh [YYYY-MM-DD]
HERMES_M5_E2E_LIVE=1 ~/hermes-content-studio/scripts/m5-notion-eval.sh [YYYY-MM-DD]
HERMES_SUPERVISED_STAGING=1 ~/hermes-content-studio/scripts/staging-supervised-eval.sh [YYYY-MM-DD]
HERMES_PLAYMCP_E2E_LIVE=1 ~/hermes-content-studio/scripts/playmcp-routing-e2e.sh
# 주간 staging cron: setup-commander-cron.sh → cron-staging-supervised 토 11:00
# 프로덕션 blocking: voice + naturalness ON (budget cap 초과는 WARN, budget_blocking=false)
HERMES_HUMANIZE=1 ~/hermes-content-studio/scripts/run-humanize-polish.sh [YYYY-MM-DD]
HERMES_HUMANIZE=1 HERMES_HUMANIZE_LLM=1 HERMES_HUMANIZE_LLM_CHANNELS=linkedin \
  ~/hermes-content-studio/scripts/run-humanize-polish.sh [YYYY-MM-DD]
HERMES_CRON_HUMANIZE=1 ~/hermes-content-studio/scripts/cron-supervised-pipeline.sh
# Notion archive: playmcp 스킵 (기본) · HERMES_MCP_DISCOVER_ALL=1 전체 MCP
```

Telegram에서 요청 보낼 때 **별도 Terminal**에서 `watch-telegram.sh` 실행:
- 단계별 Telegram 진행 메시지 (1/5~5/5)
- 에이전트 완료 후 Notion 100% 동기화 + Permalink 자동 전송

| 채널 | 방식 | 상태 |
|------|------|------|
| Telegram | Bot Token (Gateway) | connected — `/pipeline` `setup-telegram-routing.sh` |
| Slack | Bot Token (Gateway) | `/pipeline` — `setup-slack.sh` + `setup-slack-routing.sh` |
| PlayMCP (Kakao) | MCP-Gateway | **connected** — `setup-playmcp.sh` · LIVE E2E 7/7 |

두 채널 모두 동일한 커맨더 역할: 리서치·콘텐츠·강의 파이프라인 트리거.

## Harness 상태

| 파일 | 역할 |
|------|------|
| `.harness/feature_list.json` | 파이프라인 기능·검증 범위 |
| `.harness/progress.md` | 세션 진행 SoT |
| `.harness/session-handoff.md` | 다음 세션 핸드오프 |
| `.harness/traces/` | 단계별 타이밍 트레이스 |

## LLM Wiki (부분 통합)

> 전략 SoT: `docs/LLM-WIKI-INTEGRATION.md` — **일별 파이프라인 유지**, 누적 wiki 계층만 선택 도입

| 구분 | 내용 |
|------|------|
| **선택** | `/ask` index-first · Brief Graph→concepts Seed · Personal→raw Ingest · 주간 Lint |
| **유지** | M1→M5 결정적 (~70s) · `{date}_brief.md` SoT · validate · Notion Permalink |
| **신설** | `content/wiki/` · `config/wiki.yaml` · `wiki-maintainer` skill · `wiki-seed.sh` |

```bash
# 구조 게이트
~/hermes-content-studio/scripts/wiki-lint-eval.sh

# 결정적 Seed (brief_graph → concepts, LLM 없음)
HERMES_WIKI_SEED=1 ~/hermes-content-studio/scripts/wiki-seed.sh

# LLM Ingest / Lint (비동기, 기본 off)
HERMES_WIKI_INGEST=1 ~/hermes-content-studio/scripts/run-wiki-ingest.sh
HERMES_WIKI_LINT=1 ~/hermes-content-studio/scripts/run-wiki-lint.sh
```

## 스킬 우선순위

0. `harness-ops` — init·eval·성능 게이트
1. `content-orchestration` — M1~M5 마케팅 오케스트레이션 (마스터)
2. `content-pipeline` — 주간 라우터 (content-orchestration 위임)
3. `telegram-commander` — Telegram 요청 + Notion Permalink 필수
4. `channels/research` (M1) · `channels/linkedin` (M2+M3) — 채널별 단계 skill
5. `marketing-research` — M1 alias (하위 호환)
6. `content-studio-slides` — 강의 슬라이드
7. `notion-archive` — Notion 동기화 (M5)
8. `playmcp-commander` — PlayMCP 커맨더 채널
9. `vibe-coding-cursor` — Cursor 핸드오프
10. `shared/wiki-maintainer` — LLM Wiki Ingest · Query · Lint (옵션)

오케스트레이션 설정: `config/content-orchestration.yaml` · handoff: `schemas/handoff.schema.json`

## 채널

| 채널 | 폴더 | 형식 |
|------|------|------|
| research | content/research | .md |
| blog | content/blog | .html (SEO/AEO) |
| instagram | content/instagram | .md |
| linkedin | content/linkedin | .md |
| newsletter | content/newsletter | .md, .html (+ subject-scores.json) |
| lectures | content/lectures | .md, .html, .pptx |

## 품질 게이트

- SEO/AEO/GEO: title, meta, H1, H2×3, FAQ JSON-LD, GEO 인용 블록
- LinkedIn: hook 2줄, 1300자, 댓글 CTA, 이미지 프롬pt 없음
- Instagram: 슬라이드별 Midjourney/DALL-E 프롬pt + alt text
- Newsletter: TLDR 3불릿 · Hero · 모듈×3 · 단일 CTA · 제목 ≤50자 · CTOR 10–15%
- 강의: getdesign.md 프리셋, HTML + PPTX
- 출처 URL 필수
- `scripts/validate-output.sh` 통과
- **Voice · Naturalness (P4–P14):** `voice_blocking` + `naturalness_blocking` 프로덕션 ON · `budget_blocking: false` (cap 초과 WARN)
- **Budget:** `daily_token_cap: 600000` · `path_daily_token_caps.HERMES_HUMANIZE_LLM: 400000` — `loop-budget-status.sh`

## 실행 추가

```bash
# 강의 슬라이드 (HTML + PPTX + claude-design 연동)
~/hermes-content-studio/scripts/run-lecture-slides.sh "제목" \
  --content-file outline.txt --design-mode claude-design --notion-sync
```

## 코딩

코드 구현은 직접 하지 않음. `vibe-coding-cursor` 스킬로 Cursor 핸드오프 패키지 생성.
