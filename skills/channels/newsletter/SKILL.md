---
name: channel-newsletter
description: "M2b B2B 뉴스레터: Brief SoT → md + HTML + A/B 제목 스코어 · CTOR 최적화."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [M2b, newsletter, b2b, email, ctor]
    stage: M2b
    related_skills: [content-orchestration, notion-archive, shared/validate]
---

# Channel: Newsletter (M2b)

B2B 이메일 뉴스레터 — **오픈율 방향성 + 완독율(CTOR) 10–15%** 우선.

## 결정적 파이프라인 (~10s)

```bash
~/hermes-content-studio/scripts/run-newsletter.sh [YYYY-MM-DD] --validate
~/hermes-content-studio/scripts/hermes-agent.sh newsletter --date YYYY-MM-DD --validate
```

산출:
- `content/newsletter/{date}_newsletter_{slug}.md`
- `content/newsletter/{date}_newsletter_{slug}.html`
- `content/newsletter/{date}_newsletter_subject-scores.json`
- `content/packages/{date}_newsletter-context.md`
- `content/packages/{date}_newsletter-paste.md` (§1–§4 코드 블록 · Notion 복사용)

## 주간 파이프라인 (M1→M2→M2b→M5)

```bash
~/hermes-content-studio/scripts/run-pipeline.sh
# SKIP_NEWSLETTER=1 로 M2b 제외
```

## Phase 맵

| Phase | 역할 |
|-------|------|
| P0 INPUT | research brief SoT |
| P1 CONTEXT | newsletter-context.md |
| P2 ASSEMBLE | md + HTML (`templates/email/newsletter.html`) |
| P3 VALIDATE | 4게이트 (newsletter · html · context · scores) |
| P4 ARCHIVE | Notion `newsletter` + `newsletter_html` |
| P4b CTOR | 실측 record + dashboard |
| P5 PASTE | Notion 붙여넣기 팩 → 외부 플랫폼 (ESP 없음) |

## 구조 (Morning Brew + Stripo)

1. 발송 메타 · A/B 제목 스코어
2. 30초 TLDR (3불릿)
3. Hero 1가지
4. Insight 모듈 ×3
5. Grab Bag · Single CTA · 다음 호

## 설정

- `config/newsletter.yaml` — 벤치마크 · subject_templates · scoring
- `config/content-guidelines.yaml#newsletter`

## 검증

```bash
~/hermes-content-studio/scripts/newsletter-eval.sh [YYYY-MM-DD]
~/hermes-content-studio/scripts/newsletter-p2-eval.sh [YYYY-MM-DD]
~/hermes-content-studio/scripts/newsletter-p4-eval.sh [YYYY-MM-DD]
~/hermes-content-studio/scripts/newsletter-p6-eval.sh [YYYY-MM-DD]
~/hermes-content-studio/scripts/newsletter-ctor-record.sh YYYY-MM-DD --delivered N --opens N --clicks N
~/hermes-content-studio/scripts/newsletter-ctor-dashboard.sh [YYYY-MM-DD]
```

## 배포 (Notion → 외부 플랫폼)

ESP/API 자동 발송 없음. `archive-to-notion.sh` 후 **Newsletter Paste** 페이지에서:

1. **§1 제목** 코드 블록 → 캠페인 Subject
2. **§2 프리헤더** → 미리보기 문구
3. **§3 본문 Markdown** → 문서 편집기
4. **§4 HTML** → HTML/소스 모드 (선택)

## HITL (선택)

```bash
hermes-agent.sh publish newsletter --date YYYY-MM-DD
hermes-agent.sh approve newsletter --date YYYY-MM-DD
hermes-agent.sh publish newsletter --approve --date YYYY-MM-DD
```
