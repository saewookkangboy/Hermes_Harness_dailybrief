---
name: personal-assistant
description: "Telegram 개인화: 맞춤 리서치, 이메일 정리, Codex 자동화. /pipeline 과 별도."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [telegram, personal, email, codex, automation, research]
    related_skills: [marketing-research, vibe-coding-cursor, telegram-commander, himalaya]
---

# Personal Assistant — 개인화·커스텀 작업

`/pipeline` 결정적 주간 워크플로와 **별도**로, 사용자 맞춤 요청을 처리합니다.

## 작업 유형

| 유형 | 트리거 | 처리 |
|------|--------|------|
| 이메일 | mail, 이메일, 받편함 | `mail-digest.py` + Codex 요약 |
| 맞춤 리서치 | 주제 지정 조사 | Codex + web_search |
| 자동화 | Codex, 스크립트, 구현 | Codex + vibe-coding-cursor |
| 자유 질문 | 기타 | Codex personal-assistant |

## 필수 실행 (Telegram·에이전트 공통)

**LLM으로 직접 작성하지 마세요.** 아래 **단일 명령**만 실행:

```bash
~/hermes-content-studio/scripts/telegram-custom.sh auto "<사용자 요청 전문>"
```

- 백그라운드 작업 접수 → 완료 시 Telegram 알림
- 산출물: `content/personal/YYYY-MM-DD_{type}_{slug}.md`

## Telegram Slash

| 명령 | 설명 |
|------|------|
| `/mail` | 받편함 다이제스트 (즉시 접수) |
| `/personal <요청>` | 맞춤 작업 (이 스킬) |
| `/automate <설명>` | Codex 자동화 구현 |

## 이메일

1. `scripts/mail-digest.py` — Mail.app (macOS) 또는 Himalaya
2. 설정: `config/personal-tasks.yaml`
3. 심화: `/personal 이메일 액션 아이템과 회신 초안 정리`

## Codex

개인화 작업은 **Codex (gpt-5.5)** 사용:
- `HERMES_USE_CODEX=1` (telegram-custom.sh 자동 설정)
- 미연결: `~/hermes-content-studio/scripts/setup-codex.sh`

## vs /pipeline

| | /pipeline | /personal |
|---|-----------|-----------|
| 목적 | 주간 고정 브리프+소셜 | 맞춤·1회성 |
| LLM | ❌ 결정적 | ✅ Codex |
| 시간 | ~15s | 1~10min |
| 출력 | content/research,blog,... | content/personal/ |

## Anti-patterns

- `/pipeline`으로 개인화 요청 처리
- gemma4로 장문 생성 (Codex 사용)
- 이메일 본문을 Telegram에 전체 붙여넣기 (파일+요약만)
