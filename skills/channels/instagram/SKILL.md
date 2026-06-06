---
name: channel-instagram
description: "M2 Instagram: 3슬라이드 정보형 캐러셀(4:5) + Nano Banana Pro 2 + 캡션."
version: 1.1.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [M2, instagram, carousel, gemini]
    stage: M2
    related_skills: [content-orchestration, shared/validate]
---

# Channel: Instagram (M2)

## Phase 맵

| Phase | Step | 출력 |
|-------|------|------|
| P0 | brief | — |
| P1 | instagram-context | `packages/{date}_instagram-context.md` |
| P2 | carousel md | `instagram/{date}_instagram_*.md` |
| P3 | validate | 3 slides, 4:5, prompts, alt, hashtags×5 |

## 실행

```bash
~/hermes-content-studio/scripts/run-content-package.sh
~/hermes-content-studio/scripts/validate-output.sh instagram-context content/packages/YYYY-MM-DD_instagram-context.md
~/hermes-content-studio/scripts/validate-output.sh instagram content/instagram/YYYY-MM-DD_instagram_*.md
```

## 품질 (`config/content-guidelines.yaml#instagram`)

- 캐러셀 3장 · **4:5 (1080×1350)** — 2026 뉴스피드 권장
- 정보형 인포그래피 (저장형 · 완독 유도)
- Gemini Nano Banana Pro 2 · aspect_ratio=4:5
- 나눔고딕 · Hangul 정확 렌더링 · alt text/slide
- 뉴스피드 알고리즘: save · swipe completion · 125자 캡션 훅
- **해시태그 5개** (과다 태그 회피)

## 템플릿

`templates/social/instagram-carousel.md`

## Anti-patterns

- 1:1 웹툰 말풍선만 (구 스펙)
- 이미지 프롬pt 없이 캡션만
- 해시태그 8개 이상
- Pretendard (Instagram 채널은 나눔고딕)
