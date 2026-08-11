<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Hermes Content Studio — Brief SoT로 Blog·Threads·IG·LI·Newsletter를 20–26초에 생성하고 Gate A–D·Notion까지">
</p>

# Hermes Content Studio

Intel Mac에서 돌아가는 **자체호스팅 마케팅·교육 콘텐츠 스튜디오**예요.  
일일 리서치 브리프(`{date}_brief.md`)를 Brief SoT로 두고, 블로그·Threads·인스타그램·링크드인·B2B 뉴스레터를 **결정적 파이프라인(M1→M5)** 으로 생성·검증·Notion 아카이브합니다.

[Harness v1.3](https://github.com/walkinglabs/awesome-harness-engineering) · System Logic [v2.1](docs/architecture/SYSTEM-LOGIC.md) · [`AGENTS.md`](AGENTS.md) · [`HARNESS.md`](HARNESS.md) · [Docs](docs/README.md)

---

## Proof

| 최신 기준선 (2026-08-12 Full Quality) | 값 |
|--------------------------------------|-----|
| full_pipeline | **20–26s** (SLA 60–70) |
| harness-eval --quick | **40/0** |
| Newsletter Gate A–D | **PASS** · `publishable=true` |
| ask-eval | **−81~88%** tokens |
| agents / e2e | **40/0** · **19/0** |

<p align="center">
  <img src="./assets/docs/diagram-channels.svg" width="100%" alt="Brief SoT가 Blog·Threads·IG·LinkedIn·Newsletter 채널로 분기">
</p>

---

## 한눈에 보기

| 할 수 있는 일 | 방식 |
|---|---|
| 주간 리서치 Top 7 | `run-research-brief.sh` (~15–21s) |
| 블로그 · Threads · IG · LinkedIn · 뉴스레터 | `run-pipeline.sh` (~20–26s 실측, LLM 불필요) |
| Telegram / Slack / PlayMCP로 트리거 | Commander 라우팅 |
| 품질·비용 통제 | `validate-output.sh` · voice/naturalness · **Newsletter Gate A–D** · token_gate |
| 지식 누적 · `/ask` | Wiki Graph (`graph.db`) · graph_first |

<p align="center">
  <img src="./assets/readme/workflow.svg" width="100%" alt="M1 Research → M2 Packages → M2b Newsletter Gate A–D → Quality → M5 Notion">
</p>

---

## 왜 이렇게 만들었나요

- **Brief SoT 한 장**이 모든 채널의 입력이에요. 채널마다 LLM으로 다시 쓰지 않습니다.
- **결정적 스크립트 우선** — polish(`HERMES_ENHANCE=1`)는 선택입니다.
- **완료 = validate 통과 + `content/{channel}/` 저장** (+ Telegram이면 Notion Permalink).
- 뉴스레터는 **Gate A–D**로 신선도·CTA·publishable·CTOR 학습까지 막습니다.
- 커맨더는 Telegram · Slack · PlayMCP가 같은 파이프라인을 호출합니다.

<p align="center">
  <img src="./assets/docs/diagram-quality-gates.svg" width="100%" alt="Newsletter Gate A Freshness · B Email/CTA · C Validate publishable · D CTOR">
</p>

---

## 빠른 시작

```bash
# 1) 세션 부트스트랩
~/hermes-content-studio/scripts/init.sh
cat ~/hermes-content-studio/.harness/progress.md

# 2) (선택) 서비스 — Ollama + Gateway
~/hermes-content-studio/scripts/start-services.sh
~/hermes-content-studio/scripts/health-check.sh

# 3) 리서치만 / 전체 파이프라인
~/hermes-content-studio/scripts/run-research-brief.sh
HERMES_WIKI_GRAPH=1 ~/hermes-content-studio/scripts/run-pipeline.sh

# 4) 뉴스레터 단독 + publishable 게이트
SKIP_INIT=1 ~/hermes-content-studio/scripts/run-newsletter.sh --validate
```

상태바가 필요하면:

```bash
~/hermes-content-studio/scripts/hermes-run.sh \
  "이번 주 리서치 브리프 작성" --skills marketing-research
```

---

## 주간 리듬

| 요일 | 산출 | 스크립트 |
|------|------|----------|
| 월 09:00 | 리서치 브리프 | `run-research-brief.sh` |
| 수 09:00 | 블로그 · Threads · IG · LinkedIn · 뉴스레터 | `run-pipeline.sh` / `run-newsletter.sh` |
| 금 09:00 | 강의 HTML · PPTX | `run-lecture-slides.sh` |
| 요청 시 | Cursor 핸드오프 | `run-cursor-handoff.sh --latest` |

```bash
~/hermes-content-studio/scripts/setup-cron.sh
```

---

## 산출물 위치

```
content/
├── research/     # {date}_brief.md  ← Brief SoT
├── blog/         # .html (Velog형 SEO/GEO 리포트)
├── instagram/    # .md + 이미지 프롬프트
├── linkedin/     # .md
├── newsletter/   # .md · .html · subject-scores.json · title-image
├── lectures/     # .md · .html · .pptx
└── packages/     # blog-article · threads · Notion paste · publish.json
```

파일명: `YYYY-MM-DD_{channel}_{slug}.{ext}` · 디자인: [`Getdesign.md`](Getdesign.md)

| 패키지 | 역할 |
|--------|------|
| `{date}_blog-article.md` | Velog형 일일 AI 트렌드 리포트 (Notion `blog`) |
| `{date}_threads.md` | Threads 숏폼 (Notion `threads`) |
| `{date}_newsletter-paste.md` | ESP 없이 Notion → 외부 붙여넣기 |
| `{date}_newsletter-publish.json` | `publishable` + Gate 실패 목록 |

---

## Commander 채널

| 채널 | 역할 | 셋업 |
|------|------|------|
| **Telegram** | `/pipeline` · 진행 메시지 · Notion Permalink | `setup-telegram.sh` · `setup-telegram-routing.sh` · `watch-telegram.sh` |
| **Slack** | `#일반데이터` `/pipeline` · 일일 digest | `setup-slack.sh` · `setup-slack-routing.sh` |
| **PlayMCP** | Kakao 커맨더 (Slack과 동일 명령) | `setup-playmcp.sh` |

```bash
# 결정적 트리거 (LLM 없음)
~/hermes-content-studio/scripts/telegram-pipeline.sh pipeline
```

---

## 품질 · 비용 · 지식

<p align="center">
  <img src="./assets/docs/banner-quality.svg" width="100%" alt="Quality stack — validate, voice, Newsletter Gate A–D">
</p>

### 프로덕션 게이트

- `voice_blocking` + `naturalness_blocking` ON · budget cap 초과는 WARN
- 뉴스레터 **Gate A–D** (신선도/안전/제목 · Email/LI/CTA/이미지 · validate/publishable · CTOR 학습)
- stale 제목 폴백(`2026 AI·마케팅 실무 인사이트` 등) · hero near-dup 차단

```bash
# 채널 validate
~/hermes-content-studio/scripts/validate-output.sh research content/research/$(date +%Y-%m-%d)_brief.md

# Voice · Naturalness
~/hermes-content-studio/scripts/voice-style-eval.sh
~/hermes-content-studio/scripts/naturalness-eval.sh

# Newsletter Gate A–D
~/hermes-content-studio/scripts/newsletter-freshness-eval.sh   # A
~/hermes-content-studio/scripts/newsletter-gate-b-eval.sh      # B
~/hermes-content-studio/scripts/newsletter-gate-c-eval.sh      # C
~/hermes-content-studio/scripts/newsletter-gate-d-eval.sh      # D

# 비용 · Wiki · Ask
~/hermes-content-studio/scripts/cost-report.sh --since 7d
HERMES_WIKI_GRAPH=1 ~/hermes-content-studio/scripts/wiki-graph.sh
~/hermes-content-studio/scripts/ask-eval.sh --compare
```

### 전체 품질 스모크

```bash
~/hermes-content-studio/scripts/harness-eval.sh --quick      # 구조 40/0
~/hermes-content-studio/scripts/harness-eval.sh --record     # SLA 벤치
~/hermes-content-studio/scripts/e2e-smoke-test.sh            # E2E
~/hermes-content-studio/scripts/agents-eval.sh               # Agents A–D
~/hermes-content-studio/scripts/staging-supervised-eval.sh   # L2 staging
```

리포트 예: `content/logs/2026-08-12_full-quality-retest.md` (gitignore · 로컬 SoT는 `.harness/progress.md`)

---

## Harness

5-Subsystem ([awesome-harness-engineering](https://github.com/walkinglabs/awesome-harness-engineering)):

| 서브시스템 | SoT |
|-----------|-----|
| Instructions | `AGENTS.md` · `HARNESS.md` |
| State | `.harness/feature_list.json` · `progress.md` |
| Verification | `init.sh` · `harness-eval.sh` · Gate A–D evals |
| Scope | feature_list 단일 활성 기능 |
| Lifecycle | `session-handoff.md` |

```bash
~/hermes-content-studio/scripts/harness-eval.sh --quick
```

아키텍처 상세: [`docs/architecture/`](docs/architecture/)

---

## 디렉토리

```
hermes-content-studio/
├── AGENTS.md · HARNESS.md · Getdesign.md · JARVIS.md
├── assets/readme/ · assets/docs/   # README · Docs 비주얼 (Pure SVG)
├── config/                         # harness · newsletter · notion-archive
├── content/                        # 채널 산출물
├── docs/                           # Docs 허브 · architecture · plans
├── schemas/
├── scripts/                        # 파이프라인 · eval · commander
├── skills/
└── templates/
```

---

## Intel Mac 메모

- 결정적 경로: `run-research-brief.sh` + `run-content-package.sh` + `run-newsletter.sh`
- 실측 full_pipeline **~20–26s** (SLA 상한 60–70s)
- 로컬 polish: Ollama `gemma4:latest` (선택)
- 16GB 이하에서는 Ollama + Gateway 동시 실행에 주의
- 상시 cron이면 Mac 절전 해제 권장

---

## Cursor 연동

```bash
~/hermes-content-studio/scripts/install-cursor-cli.sh
~/hermes-content-studio/scripts/run-cursor-handoff.sh --latest
```

Telegram `/automate` → Codex HANDOFF → Cursor CLI (`HERMES_CURSOR_AUTO=1`).

---

## 선택 설정

| 항목 | 스크립트 / 비고 |
|------|-----------------|
| Codex | `setup-codex.sh` — claude-design · `HERMES_ENHANCE` |
| OpenRouter 등 | `~/.hermes/.env` (커밋 금지) |
| Notion REST | `NOTION_API_KEY` · `archive-to-notion.sh` |
| Notion/Slack MCP | Cursor MCP OAuth · `hermes mcp test notion` |

---

## 문서

- [`docs/README.md`](docs/README.md) — Docs 허브
- [`docs/architecture/SYSTEM-LOGIC.md`](docs/architecture/SYSTEM-LOGIC.md) — 현행 SoT (v2.1)
- [`docs/superpowers/specs/2026-08-11-ai-agent-blog-threads-daily-report-design.md`](docs/superpowers/specs/2026-08-11-ai-agent-blog-threads-daily-report-design.md) — Velog형 블로그 + Threads 설계
- [`docs/superpowers/plans/2026-08-11-ai-agent-blog-threads-daily-report.md`](docs/superpowers/plans/2026-08-11-ai-agent-blog-threads-daily-report.md) — 구현 계획
- [`HARNESS.md`](HARNESS.md) · [`AGENTS.md`](AGENTS.md) · [`JARVIS.md`](JARVIS.md) · [`Getdesign.md`](Getdesign.md)

---

<p align="center">
  <img src="./assets/docs/banner-visual-method.svg" width="100%" alt="Visual method — beautify-github-readme Pure SVG, Value → Proof → First use">
</p>

README · Docs 비주얼은 [beautify-github-readme](https://github.com/oil-oil/beautify-github-readme) 방법론(Pure SVG · Value → Proof → First use)을 따릅니다.  
스킬 설치: `npx skills add oil-oil/beautify-github-readme`
