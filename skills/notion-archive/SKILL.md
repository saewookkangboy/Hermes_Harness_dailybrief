---
name: notion-archive
description: "Hermes Content Studio 산출물을 Notion 일자별·카테고리별 아카이브."
version: 1.1.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [notion, archive, content, pipeline]
    related_skills: [content-pipeline, marketing-research]
---

# Notion Archive — 일자별 콘텐츠 아카이브

## 목적

`content/` 산출물을 Notion **Hermes Content Studio Archive**에 일자별·카테고리별로 동기화합니다.
Telegram 알림·Terminal 모니터(`watch-telegram.sh`)는 변경하지 않습니다.

## 카테고리

| 카테고리 | 로컬 경로 |
|----------|-----------|
| Research Brief | `content/research/*_brief.md` |
| Blog | `content/blog/*.html` |
| Instagram | `content/instagram/*.md` |
| LinkedIn | `content/linkedin/*.md` |
| Lecture | `content/lectures/*` |

## 규칙

- **Daily Archive**는 해당 날짜에 **신규 아카이브할 콘텐츠가 1건 이상**일 때만 생성
- 이미 동기화된 파일·빈 본문은 페이지 생성 안 함
- 루트 페이지: 워크스페이스 최상위 `Hermes Content Studio Archive`

## 실행

```bash
~/hermes-content-studio/scripts/archive-to-notion.sh [YYYY-MM-DD]
```

## 워크플로우 (에이전트) — Telegram 요청 시 필수

콘텐츠 파일 저장 후 **반드시** Notion 동기화:
```bash
TELEGRAM_CHAT_ID=<chat_id> ~/hermes-content-studio/scripts/archive-to-notion.sh $(date +%Y-%m-%d) --force
```

Telegram Permalink 형식으로 사용자에게 전달.
`watch-telegram.sh` 실행 중이면 자동 동기화·Permalink 전송됨.

Markdown 보존: `scripts/lib/markdown_notion.py` — 헤딩·코드블록·리스트 유지
