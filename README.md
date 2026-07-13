# Hermes Content Studio

> **Hermes Harness Daily Brief** — Intel Mac 자체호스팅 AI 마케팅·교육 콘텐츠 스튜디오  
> [awesome-harness-engineering](https://github.com/walkinglabs/awesome-harness-engineering) · Harness v2.0 · [시스템 로직](docs/architecture/SYSTEM-LOGIC.md)

일일 리서치 브리프(Top 7)를 **Brief SoT**(`{date}_brief.md`)로 두고, 블로그·인스타그램·링크드인·B2B 뉴스레터를 **결정적 파이프라인(M1→M5)** 으로 생성·검증·Notion 아카이브합니다. Telegram·Slack·PlayMCP Commander, Content Loops(cron triage·supervised pipeline), Voice/Naturalness 품질 게이트, 8개 sibling studio upstream 연동, JARVIS 프로젝트 메모리를 포함합니다.

| 영역 | 설명 |
|------|------|
| **파이프라인** | M1 Research → GATE → M2 Content → M2b Newsletter → Quality → M5 Notion |
| **Commander** | Telegram · Slack · PlayMCP · `hermes-agent.sh` · cron |
| **품질** | `validate-output.sh` · voice/naturalness blocking · loop budget |
| **확장** | Multi-Studio ×8 · Wiki · Research Squad · Cursor 핸드오프 |
| **문서** | [`docs/architecture/`](docs/architecture/) · `HARNESS.md` · `AGENTS.md` |

Intel Mac (MacBook Pro) 자체호스팅 Hermes Agent 기반 **마케팅·교육 콘텐츠 스튜디오**.

## 목표

| 영역 | 산출물 | 주기 |
|------|--------|------|
| 마케팅 리서치 | 주간 브리프 | 월 09:00 |
| 블로그 (SEO/AEO) | HTML 초안 | 수 09:00 |
| 인스타그램 | 캐러셀·캡션 | 수 09:00 |
| 링크드인 | 뉴스피드 포스트 | 수 09:00 |
| B2B 뉴스레터 | md + HTML 이메일 · A/B 제목 | 수 09:00 (M2b) |
| 강의 자료 | 기획·HTML·슬라이드 | 금 09:00 |
| 바이브 코딩 | Cursor 핸드오프 | 요청 시 |

## 빠른 시작

```bash
# 0. 스튜디오 업데이트 (Hermes Agent + 스킬 v1.1.0)
~/hermes-content-studio/scripts/update-studio.sh

# 1. 서비스 시작 (Ollama + Hermes Gateway)
~/hermes-content-studio/scripts/start-services.sh

# 2. 헬스체크
~/hermes-content-studio/scripts/health-check.sh

# 3. 주간 cron 등록
~/hermes-content-studio/scripts/setup-cron.sh

# 4. 수동 리서치 실행
hermes -z "이번 주 리서치 브리프 작성해줘" --skills marketing-research
```

## 디렉토리 구조

```
hermes-content-studio/
├── Getdesign.md              # 비주얼 디자인 시스템
├── AGENTS.md                 # Hermes 에이전트 컨텍스트
├── config/studio.yaml        # 스튜디오 설정
├── skills/                   # 커스텀 Hermes 스킬
│   ├── content-pipeline/
│   ├── marketing-research/
│   ├── content-studio-slides/
│   └── vibe-coding-cursor/
├── templates/                # HTML·소셜·슬라이드 템플릿
├── content/                  # 산출물
│   ├── research/
│   ├── blog/
│   ├── instagram/
│   ├── linkedin/
│   ├── newsletter/
│   ├── lectures/
│   └── drafts/cursor-handoff/
└── scripts/                  # 셋업·운영 스크립트
```

## Harness Engineering (v2.0)

[awesome-harness-engineering](https://github.com/walkinglabs/awesome-harness-engineering) 기반 5-Subsystem 하네스:

| 서브시스템 | 파일 |
|-----------|------|
| Instructions | `AGENTS.md`, `HARNESS.md` |
| State | `.harness/feature_list.json`, `.harness/progress.md` |
| Verification | `scripts/init.sh`, `scripts/harness-eval.sh` |
| Scope | feature_list 단일 활성 기능 |
| Lifecycle | `session-handoff.md`, init → 작업 → 핸드오프 |

아키텍처: [`docs/architecture/SYSTEM-LOGIC.md`](docs/architecture/SYSTEM-LOGIC.md) · 버전 아카이브: [`docs/architecture/archive/`](docs/architecture/archive/)

```bash
# 세션 시작
~/hermes-content-studio/scripts/init.sh

# 성능 eval
~/hermes-content-studio/scripts/harness-eval.sh --quick
```

## Intel Mac 최적화 (v1.2.0)

- **결정적 파이프라인:** `run-research-brief.sh` + `run-content-package.sh` + `run-newsletter.sh` (~70s, LLM 불필요)
- **병렬 웹 검색:** ddgs 4 workers (`gather-web-research.py`)
- **로컬 모델:** Ollama `gemma4:latest` (8B Q4) — Hermes polish(선택)용
- **클라우드 API:** 장문·슬라이드·복잡 분석 시 OpenRouter 등 권장
- **메모리:** 16GB 이하 Mac에서는 Ollama + Gateway 동시 실행 주의
- **상시 실행:** Mac 절전 해제 권장 (시스템 설정 → 에너지)

## Cursor 연동

Cursor Agent CLI (`cursor-agent`) + 핸드오ff 자동 실행:

```bash
# CLI 설치 (1회)
~/hermes-content-studio/scripts/install-cursor-cli.sh

# HANDOFF 자동 실행
~/hermes-content-studio/scripts/run-cursor-handoff.sh --latest
~/hermes-content-studio/scripts/run-cursor-handoff.sh --dry-run --latest

# Telegram /automate → Codex HANDOFF → Cursor CLI (백그라운드, HERMES_CURSOR_AUTO=1)
```

수동 IDE 핸드오프 (CLI 없을 때):

1. Hermes가 `content/drafts/cursor-handoff/` 에 HANDOFF.md 생성
2. Cursor IDE에서 대상 레포 열기
3. Agent 모드에 HANDOFF.md 내용 붙여넣기

## Hermes 실행 (상태 표시바)

`-z` 원샷은 진행 표시가 없습니다. **상태바 래퍼** 사용:

```bash
~/hermes-content-studio/scripts/hermes-run.sh \
  "marketing-research 스킬대로 이번 주 리서치 브리프 작성. 파일: content/research/2026-06-05_brief.md" \
  --skills marketing-research
```

표시: `[████████░░░░] 02:30 | LLM 추론 | Ollama 85%`

## 메시징 (Discord → Telegram)

Discord는 **연결 해제**됨. 대체: **Telegram** (WhatsApp 대비 BotFather 토큰만 필요).

```bash
TELEGRAM_BOT_TOKEN=... TELEGRAM_ALLOWED_USERS=... \
  ~/hermes-content-studio/scripts/setup-telegram.sh
```

## MCP 연동 (Notion · Slack)

### Cursor IDE (완료)
- **Notion MCP**: `https://mcp.notion.com/mcp` — OAuth 완료, 16 tools
- **Slack MCP**: `https://mcp.slack.com/mcp` — OAuth 완료, 20 tools
- Cursor Agent 채팅에서 Notion 검색·페이지 생성, Slack 채널·메시지 조회 가능

### Hermes Agent
- **Notion MCP**: `hermes mcp test notion` ✓ — 새 세션부터 16 tools 사용
- **Slack MCP**: Hermes OAuth 등록 404로 비활성 — Cursor MCP 또는 Bot Token 사용

```bash
# Hermes MCP 상태 확인
hermes mcp list
hermes mcp test notion

# Hermes에 Notion MCP 재등록 (필요 시)
hermes mcp add notion --url https://mcp.notion.com/mcp --auth oauth
```

## 다음 설정 (수동)

1. **Codex (ChatGPT 구독)** (연결됨): `./scripts/setup-codex.sh` — claude-design·HERMES_ENHANCE 품질 경로에 자동 사용
2. **클라우드 API** (선택): `~/.hermes/.env`에 `OPENROUTER_API_KEY` 추가 후 config에 fallback 설정
3. **Notion REST API** (선택): `NOTION_API_KEY` + hermes `notion` 스킬 (MCP와 병행 가능)
4. **Slack Bot** (커맨더): `./scripts/setup-slack.sh` + `./scripts/setup-slack-routing.sh` — `/pipeline` in `#일반데이터`
5. **PlayMCP (Kakao)** (커맨더): `ONE_TIME_TOKEN=ott_... ./scripts/setup-playmcp.sh` — Slack과 동일한 명령 채널
6. **Cursor CLI** (연결됨): `./scripts/install-cursor-cli.sh` + `./scripts/run-cursor-handoff.sh --latest`

## 주간 워크플로

```
월 09:00  리서치 브리프 ──────────────────────────┐
                                                 │
수 09:00  블로그 + 인스타 + 링크드인 초안 ◄───────┘
                                                 │
금 09:00  강의 기획 + 슬라이드 ◄──────────────────┘
                                                 │
요청 시   Cursor 핸드오프 (코드 구현) ────────────┘
```
