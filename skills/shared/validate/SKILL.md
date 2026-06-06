---
name: shared-validate
description: "채널별 validate-output.sh 품질 게이트·체크리스트."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [validate, quality, harness]
    related_skills: [content-orchestration, harness-ops]
---

# Shared: Validate

완료 선언 전 **필수**. `scripts/validate-output.sh`

## 타입별 명령

```bash
validate-output.sh research      content/research/YYYY-MM-DD_brief.md
validate-output.sh blog-article  content/packages/YYYY-MM-DD_blog-article.md
validate-output.sh blog          content/blog/YYYY-MM-DD_blog_*.html
validate-output.sh instagram-context content/packages/YYYY-MM-DD_instagram-context.md
validate-output.sh instagram     content/instagram/YYYY-MM-DD_instagram_*.md
validate-output.sh linkedin-context  content/packages/YYYY-MM-DD_linkedin-context.md
validate-output.sh linkedin      content/linkedin/YYYY-MM-DD_linkedin_*.md
validate-output.sh unified-context content/packages/YYYY-MM-DD_unified-context.md
validate-output.sh lecture       content/lectures/YYYY-MM-DD_*.md
```

## 가이드라인 SoT

`config/content-guidelines.yaml`

## harness.yaml 연동

`verification.post_stage` — stage별 validate 매핑

## Anti-pattern

검증 없이 "완료" 선언 → Harness 위반
