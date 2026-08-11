<!--
이 파일은 두 섹션으로 나뉩니다.
  ## STABLE   — 브랜드 규칙·품질 게이트. 사람만 편집.
  ## LEARNED  — 경험적 학습. scripts/curate-playbook.sh 만 편집.
                append-only + tombstone. 삭제 금지.
-->

---
name: channel-blog
description: "M2 블로그: SEO/AEO/GEO HTML + blog-article 패키지."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [M2, blog, seo, aeo, geo]
    stage: M2
    related_skills: [content-orchestration, shared/validate]
---

# Channel: Blog (M2)

## Velog 일일 리포트 (AI Agent 렌즈)

Brief Top 인사이트 → **AI Agent·에이전틱 AI** 관점의 Velog 일일 트렌드 포스트.

| 섹션 | 내용 |
|------|------|
| 제목 | `[오늘의 AI 트렌드] {테마}({MM/DD})` |
| 서문 | 날짜 + 일일 요약 2문장 |
| §1 | 주요 트렌드 및 개발 이슈 (Top 2) |
| §2 | 요즘 주목받는 핵심 기술 (불릿) |
| §3 | 마케터·비즈니스 리더 향후 대책 |
| 마무리 | 한 줄 요약 + 출처 URL |

- **본문 상한:** 출처·SEO 꼬리 제외 **≤3,000자** (`BODY_MAX_CHARS`)
- **Threads 동반:** `content/packages/{date}_threads.md` — 훅 · `→` 불릿 3–5 · `[블로그 링크]` · 댓글 CTA
- **렌즈:** 글로벌 AI Agent 신호 → 국내 마케터·AX 실무 (`research-brief.yaml` AI Agent 토픽)

## Phase 맵

| Phase | Step | 출력 | validate |
|-------|------|------|----------|
| P0 | brief + `_search_context_*.md` | — | — |
| P1 | blog-article md | `packages/{date}_blog-article.md` | blog-article |
| P1b | Threads package | `packages/{date}_threads.md` | threads-package |
| P2 | HTML assemble | `blog/{date}_blog_*.html` | blog |
| P3 | validate | — | Velog 구조 · 본문 cap |
| P5 | enhance (선택) | polish | — |

## 실행

```bash
~/hermes-content-studio/scripts/run-content-package.sh
# blog · Threads 검증
~/hermes-content-studio/scripts/validate-output.sh blog-article content/packages/YYYY-MM-DD_blog-article.md
~/hermes-content-studio/scripts/validate-output.sh threads-package content/packages/YYYY-MM-DD_threads.md
~/hermes-content-studio/scripts/validate-output.sh blog content/blog/YYYY-MM-DD_blog_*.html
# eval: unit + live (packages 필요)
~/hermes-content-studio/scripts/blog-daily-report-eval.sh --unit
~/hermes-content-studio/scripts/blog-daily-report-eval.sh --live YYYY-MM-DD
```

## 품질 (`config/content-quality.yaml#blog`)

- Velog 섹션 4블록 + 한 줄 요약 + 출처 URL 필수
- 본문(출처 제외) **≤3,000자** — 초과 시 FAIL
- HTML: title · meta · H1 · Article JSON-LD · H2×3+
- ~합니다 평문 · AI Agent 렌즈 · 출처 기반

## 템플릿

`templates/html/blog-post.html`

## strategy-prompts (M2)

- AIDA: Direct Answer 첫 문단
- 콘텐츠 퍼널: 인지→고려→전환 H2 구조
- So What: 각 H2 끝 실무 takeaway

## Anti-patterns

- 본문이 출처·SEO 꼬리 제외 3,000자를 초과
- 출처 URL 없음
- `[오늘의 AI 트렌드]` 제목 누락
- LLM으로 HTML 전체 재생성 (assemble 우선)

## LEARNED
<!-- Curator 전용. 사람이 직접 편집하지 말 것. -->

