---
name: telegram-commander
description: "Telegram 커맨더: 결정적 파이프라인 + Instagram 4:5 캐러셀 + Notion Permalink."
version: 1.4.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [telegram, notion, commander, pipeline, content, instagram, personal]
    related_skills: [content-orchestration, content-pipeline, channels/instagram, channels/linkedin, notion-archive, personal-assistant, marketing-research]
---

# Telegram Commander — v1.4

Telegram·Slack에서 주간/일일 콘텐츠 파이프라인을 트리거하고, Notion Permalink까지 전달하는 커맨더 스킬입니다.

## A) 파이프라인 (결정적, LLM ❌) · Brief SoT

| 명령 | 동작 |
|------|------|
| `/pipeline` | **M1(gather→brief Top 7) → M2 → M5** (~45s) |
| `/research` | M1 — `run-research-brief.sh` (일일 최신 수집) |
| `/content` | **M1 선행(당일) + M2** — brief SoT → blog · instagram · linkedin |
| `/sync` | M5 — Notion Permalink |
| `/studio` | 상태 점검 |

**흐름:** `_search_context_{date}.json` → `{date}_brief.md` → M2 채널

→ `scripts/telegram-pipeline.sh`

### M2 산출물 (Telegram `/content` · `/pipeline` 완료 시)

| 채널 | 로컬 경로 | packages |
|------|-----------|----------|
| blog | `content/blog/{date}_blog_*.html` | `{date}_blog-article.md` |
| **instagram** | `content/instagram/{date}_instagram_*.md` | `{date}_instagram-context.md` |
| linkedin | `content/linkedin/{date}_linkedin_*.md` | `{date}_linkedin-context.md` |
| 통합 | — | `{date}_unified-context.md` |

## B) Instagram — 뉴스피드 최적화 (M2 필수)

Telegram 파이프라인의 Instagram 산출물은 **`channels/instagram`** · `config/content-guidelines.yaml#instagram` 스펙을 따릅니다.

### 알고리즘·포맷

| 항목 | 스펙 |
|------|------|
| 장수 | **3장 캐러셀** (Hook → Insight → CTA) |
| 비율 | **4:5 · 1080×1350** — 2026 뉴스피드 세로 점유 권장 |
| 포맷 | **정보형 인포그래피** (저장형 · 완독 유도) |
| 1장 | 3초 훅 · swipe cue · 저장 암시 |
| 2장 | 불릿 2~3 · save-worthy 인사이트 |
| 3장 | 저장·공유 CTA — 미완독 재노출 대비 |
| 캡션 | 첫 **125자 훅** · 줄바꿈 가독성 |
| 해시태그 | **5개 고정** (주제별 자동 · 과다 태그 회피) |
| 안전 영역 | 텍스트·아이콘 중앙 **1080×1080** (그리드 크롭 대비) |

### 이미지 생성 (Nano Banana Pro 2)

- **엔진:** `gemini-3-pro-image-preview` (Nano Banana Pro 2)
- **API:** `aspect_ratio=4:5`, `image_size=2K`, `response_modalities=['TEXT','IMAGE']`
- **폰트:** **나눔고딕** (Nanum Gothic Bold/Regular) — Instagram 채널 전용
- **Hangul:** 프롬프트에 헤드라인·본문 **정확한 한국어 문자열** 명시
- **Negative:** broken Korean, 1:1 square, speech bubbles, cluttered layout

프롬프트 구조 (`scripts/lib/content_quality.py` · `build_gemini_instagram_feed_prompt`):

```
[Instagram Feed Carousel N/3 — {Hook|Insight|CTA} · 4:5 Portrait · 1080×1350]
Prompt: … informational infographic … Nanum Gothic … exact Korean strings …
Negative: …
Alt text (KO): …
Gemini API: model=gemini-3-pro-image-preview (Nano Banana Pro 2), aspect_ratio=4:5, …
```

### 검증 (완료 선언 전)

```bash
~/hermes-content-studio/scripts/validate-output.sh instagram \
  content/instagram/YYYY-MM-DD_instagram_*.md
~/hermes-content-studio/scripts/validate-output.sh instagram-context \
  content/packages/YYYY-MM-DD_instagram-context.md
```

게이트: Slide×3 · 4:5 · Nano Banana Pro 2 · 나눔고딕 · 해시태그 5개 · alt text

### 샘플 구조 (Permalink·Notion 참조용)

- 헤더: `# 인스타그램 캐러셀 — {주제}` · 4:5 · Nano Banana Pro 2
- `## 뉴스피드 알고리즘 최적화` — save · swipe · 125자 훅 · 해시태그 5개
- `### Slide 1/3 — Hook` · `2/3 Insight` · `3/3 CTA`
- 각 슬라이드: `#### Gemini Nano Banana Pro 2 이미지 생성 프롬프트` (코드블록)
- `## 캡션 (가독성 최적화)` — 💬 훅 · 📌 핵심 · 💡 한 줄 · 👉 저장 CTA
- `## 해시태그 (5개)` — 예: `#ClaudeAI #LLM #AIMarketing #B2B마케팅 #AX`

레퍼런스: `content/instagram/2026-06-07_instagram_claude-opus-47-anthropic.md`

## C) 개인화 (Codex, 백그라운드)

| 명령 | 동작 |
|------|------|
| `/mail` | Mail.app 이메일 다이제스트 |
| `/personal <요청>` | 맞춤 리서치·분석 |
| `/automate <설명>` | Codex 자동화 구현 |

→ `scripts/telegram-custom.sh` · `content/personal/`

## 라우팅

- 파이프라인 키워드 (리서치, 콘텐츠, blog, **instagram**, linkedin, pipeline) → `telegram-pipeline.sh auto`
- 개인화 키워드 (이메일, codex, 자동화, 맞춤) → `telegram-custom.sh auto`

## Definition of Done (Telegram 요청)

1. **M1:** `gather-web-research.py` + `{date}_brief.md` Top 7 · validate research
2. **M2:** brief SoT 기반 blog · instagram · linkedin · validate 전 채널
3. `archive-to-notion.sh --force` + **Permalink**
4. `.harness/progress.md` 업데이트

환경 변수: `HERMES_SKIP_RESEARCH=1` (brief 재수집 생략) · `HERMES_FORCE_RESEARCH=1` (강제 재수집)

## 설정

```bash
~/hermes-content-studio/scripts/setup-telegram-routing.sh
~/hermes-content-studio/scripts/setup-codex.sh   # 개인화 필수
```

## Anti-patterns

- `/pipeline`으로 이메일·자동화 요청
- gemma4 장문 생성 (Codex 사용)
- Notion 없이 파이프라인만 "완료" 선언
- Instagram **1:1 웹툰·Pretendard** (구 스펙 — v1.4부터 4:5 정보형·나눔고딕)
- Instagram 해시태그 8개 이상
- 이미지 프롬pt 없이 캡션만 전송

## 참조

- Instagram 채널: `skills/channels/instagram/SKILL.md`
- 템플릿: `templates/social/instagram-carousel.md`
- 가이드: `config/content-guidelines.yaml#instagram`
