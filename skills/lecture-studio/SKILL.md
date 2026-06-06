---
name: lecture-studio
description: "Telegram 강의 자료: 자연어 요구사항 → Outline + HTML → Notion. /pipeline 제외."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [lecture, slides, telegram, notion]
    related_skills: [content-studio-slides, telegram-commander]
---

# Lecture Studio — 강의 자료 (/lecture)

주간 `/pipeline`과 **별도**. 사용자가 자연어로 강의 요구사항을 입력하면 Outline + HTML을 생성하고 Notion에 아카이브합니다.

## 필수 실행

```bash
~/hermes-content-studio/scripts/telegram-lecture.sh qc "<사용자 요청 전문>"
```

또는 (Terminal):

```bash
~/hermes-content-studio/scripts/telegram-lecture.sh "AEO 실전 90분, 대상: B2B 마케터, FAQ·실습 포함"
```

## 입력 예시

- "Hermes Content Studio 실습 2시간, Intel Mac 대상, hands-on 위주"
- "AEO FAQ schema 워크숍 90분, 마케터·SEO 담당자"
- "claude-design 1920x1080 HTML 덱, AX 전환 사례 5개" (+ `LECTURE_DESIGN_MODE=claude-design`)

## 출력

- `content/lectures/YYYY-MM-DD_lecture_*_outline.md`
- `content/lectures/YYYY-MM-DD_lecture_*.html`
- Notion: Lecture Outline · Lecture HTML (Daily Archive 하위)

## Anti-patterns

- `/pipeline`으로 강의 생성 요청
- brief 자동 `--from-brief` (요청 시에만)
