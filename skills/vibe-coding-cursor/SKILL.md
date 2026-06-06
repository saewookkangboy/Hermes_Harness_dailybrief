---
name: vibe-coding-cursor
description: "Cursor 바이브 코딩 핸드오프: 프롬프트·컨텍스트 패키지 생성 및 실행 가이드."
version: 1.1.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [cursor, vibe-coding, coding-agent, handoff, development]
    related_skills: [content-pipeline, codex, claude-code]
---

# Vibe Coding with Cursor — 핸드오프 스킬

Hermes에서 기획·리서치·콘텐츠 작업 후, 코드 구현이 필요할 때
Cursor Agent로 넘기기 위한 **핸드오프 패키지**를 생성합니다.

## 워크스페이스

```
~/hermes-content-studio/content/drafts/cursor-handoff/
├── YYYY-MM-DD_{project}_HANDOFF.md    # 메인 핸드오프 문서
├── YYYY-MM-DD_{project}_CONTEXT.md    # 배경·결정·제약
└── YYYY-MM-DD_{project}_TASKS.md      # 구현 태스크 목록
```

기존 프로젝트 경로:
- `~/Desktop/개발_코딩_프로젝트/marketers-brain/`
- `~/Desktop/개발_코딩_프로젝트/vibe-coding-navigator/`

## 핸드오프 문서 형식

```markdown
# Cursor Handoff: {프로젝트명}
**날짜:** YYYY-MM-DD
**Hermes 세션:** {session_id}
**대상 레포:** {절대경로}

## 목표
(1–2문장, 무엇을 만들/수정하는지)

## 배경
(리서치 브리프·콘텐츠에서 온 맥락)

## 구현 범위
- [ ] 태스크 1
- [ ] 태스크 2

## 기술 스택
- Next.js / React / ...
- 기존 컨벤션: {PROJECT_STRUCTURE.md 참조}

## Getdesign.md 적용
(UI 작업 시 ~/hermes-content-studio/Getdesign.md 색상·타이포 참조)

## 수용 기준
1. ...
2. ...

## 금지 사항
- 범위 밖 리팩토링 금지
- ...

## Cursor 실행 방법

### 방법 A: Cursor IDE (권장)
1. Cursor에서 `{레포 경로}` 열기
2. Agent 모드에서 이 HANDOFF.md 내용 붙여넣기
3. "위 핸드오프대로 구현해줘" 실행

### 방법 B: Cursor CLI (자동화)
```bash
# 설치 (1회)
~/hermes-content-studio/scripts/install-cursor-cli.sh

# HANDOFF 자동 실행 (headless)
~/hermes-content-studio/scripts/run-cursor-handoff.sh --latest
~/hermes-content-studio/scripts/run-cursor-handoff.sh --handoff content/drafts/cursor-handoff/YYYY-MM-DD_{project}_HANDOFF.md

# Telegram /automate: Codex → HANDOFF 생성 → run-cursor-handoff --background (HERMES_CURSOR_AUTO=1)
```

### 방법 C: Cursor SDK (자동화)
```typescript
import { Agent } from "@cursor/sdk";
const result = await Agent.prompt(handoffPrompt, {
  apiKey: process.env.CURSOR_API_KEY!,
  local: { cwd: "{레포 경로}" },
});
```

## 품질 게이트
- [ ] HANDOFF.md에 절대 경로 명시
- [ ] 기존 레포 컨벤션(AGENTS.md, CLAUDE.md) 참조
- [ ] 범위 최소화 (5줄 diff 원칙)
- [ ] 테스트/빌드 명령 포함
```

## 실행 흐름

1. 사용자 요청 또는 콘텐츠 파이프라인에서 "코드 구현 필요" 판단
2. 리서치·기획 결과를 CONTEXT.md에 정리
3. 구현 태스크를 TASKS.md에 분해
4. HANDOFF.md 생성 → `cursor-handoff/` 저장
5. `run-cursor-handoff.sh --latest` 자동 실행 (HERMES_CURSOR_AUTO=1) 또는 사용자에게 Cursor IDE 안내

## Intel Mac 팁

- Cursor Agent는 클라우드/로컬 모델 선택 가능 — 복잡한 구현은 클라우드 권장
- Hermes(Ollama)로 기획 → Cursor로 구현 분업이 효율적
- `marketers-brain` 등 Next.js 프로젝트: `npm run dev` 로컬 검증
