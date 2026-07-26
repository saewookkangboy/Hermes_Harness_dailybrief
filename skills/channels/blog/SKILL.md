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

## Phase 맵

| Phase | Step | 출력 | validate |
|-------|------|------|----------|
| P0 | brief + `_search_context_*.md` | — | — |
| P1 | blog-article md | `packages/{date}_blog-article.md` | blog-article |
| P2 | HTML assemble | `blog/{date}_blog_*.html` | blog |
| P3 | validate | — | SEO/AEO/GEO |
| P5 | enhance (선택) | polish | — |

## 실행

```bash
~/hermes-content-studio/scripts/run-content-package.sh
# blog만 검증
~/hermes-content-studio/scripts/validate-output.sh blog-article content/packages/YYYY-MM-DD_blog-article.md
~/hermes-content-studio/scripts/validate-output.sh blog content/blog/YYYY-MM-DD_blog_*.html
```

## 품질 (`config/content-guidelines.yaml#blog`)

- title 50–60자, meta 140–160자
- H1 1개, H2 3개+
- FAQ JSON-LD, Article schema
- GEO 인용 블록, author attribution
- ~합니다 평문 · 출처 기반 확장 (`blog-article`, 최대 15000자)

## 템플릿

`templates/html/blog-post.html`

## strategy-prompts (M2)

- AIDA: Direct Answer 첫 문단
- 콘텐츠 퍼널: 인지→고려→전환 H2 구조
- So What: 각 H2 끝 실무 takeaway

## Anti-patterns

- FAQ schema 없이 "완료"
- 출처 URL 없음
- LLM으로 HTML 전체 재생성 (assemble 우선)

## LEARNED
<!-- Curator 전용. 사람이 직접 편집하지 말 것. -->

