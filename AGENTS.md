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

# 전체 파이프라인 (결정적, ~45s)
~/hermes-content-studio/scripts/run-pipeline.sh

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
```

Telegram에서 요청 보낼 때 **별도 Terminal**에서 `watch-telegram.sh` 실행:
- 단계별 Telegram 진행 메시지 (1/5~5/5)
- 에이전트 완료 후 Notion 100% 동기화 + Permalink 자동 전송

| 채널 | 방식 | 상태 |
|------|------|------|
| Telegram | Bot Token (Gateway) | connected — `/pipeline` `setup-telegram-routing.sh` |
| Slack | Bot Token (Gateway) | `/pipeline` — `setup-slack.sh` + `setup-slack-routing.sh` |
| PlayMCP (Kakao) | MCP-Gateway | OTT 필요 → `scripts/setup-playmcp.sh` |

두 채널 모두 동일한 커맨더 역할: 리서치·콘텐츠·강의 파이프라인 트리거.

## Harness 상태

| 파일 | 역할 |
|------|------|
| `.harness/feature_list.json` | 파이프라인 기능·검증 범위 |
| `.harness/progress.md` | 세션 진행 SoT |
| `.harness/session-handoff.md` | 다음 세션 핸드오프 |
| `.harness/traces/` | 단계별 타이밍 트레이스 |

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

오케스트레이션 설정: `config/content-orchestration.yaml` · handoff: `schemas/handoff.schema.json`

## 채널

| 채널 | 폴더 | 형식 |
|------|------|------|
| research | content/research | .md |
| blog | content/blog | .html (SEO/AEO) |
| instagram | content/instagram | .md |
| linkedin | content/linkedin | .md |
| lectures | content/lectures | .md, .html, .pptx |

## 품질 게이트

- SEO/AEO/GEO: title, meta, H1, H2×3, FAQ JSON-LD, GEO 인용 블록
- LinkedIn: hook 2줄, 1300자, 댓글 CTA, 이미지 프롬pt 없음
- Instagram: 슬라이드별 Midjourney/DALL-E 프롬pt + alt text
- 강의: getdesign.md 프리셋, HTML + PPTX
- 출처 URL 필수
- `scripts/validate-output.sh` 통과

## 실행 추가

```bash
# 강의 슬라이드 (HTML + PPTX + claude-design 연동)
~/hermes-content-studio/scripts/run-lecture-slides.sh "제목" \
  --content-file outline.txt --design-mode claude-design --notion-sync
```

## 코딩

코드 구현은 직접 하지 않음. `vibe-coding-cursor` 스킬로 Cursor 핸드오프 패키지 생성.
