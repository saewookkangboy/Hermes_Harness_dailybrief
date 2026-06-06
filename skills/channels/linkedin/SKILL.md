---
name: channel-linkedin
description: "M2+M3 LinkedIn: analyze→strategy→draft 파이프 + 피드 알고리즘 최적화."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [M2, M3, linkedin, feed, b2b]
    stage: M2
    related_skills: [content-orchestration, prompts/linkedin-pipeline, shared/validate]
---

# Channel: LinkedIn (M2 + M3)

[linkedin-feed-strategy-maker](https://github.com/saewookkangboy/linkedin-feed-strategy-maker) **analyze → strategy → draft** 패턴을 Hermes 파이프라인에 통합.

## 이중 파이프라인

### A. 결정적 (기본, ~2s)

```bash
~/hermes-content-studio/scripts/run-content-package.sh
```

산출:
- `content/packages/{date}_linkedin-context.md` (P1)
- `content/linkedin/{date}_linkedin_*.md` (P2)

### B. M3 최적화 (LLM / enhance)

| Step | Skill | 입력 | 출력 |
|------|-------|------|------|
| 1 analyze | `01-analyze.md` | brief, search_context | `packages/{date}_linkedin-analysis.md` |
| 2 strategy | `02-strategy.md` | analysis, strategy profile | `packages/{date}_linkedin-strategy.md` |
| 3 draft | `03-draft.md` | strategy, context | `linkedin/{date}_linkedin_*.md` |
| 4 validate | `04-validate.md` | draft | validate-output.sh |

```bash
# Hermes M3 (선택)
HERMES_ENHANCE=1 ~/hermes-content-studio/scripts/run-content-package.sh
hermes chat -q "..." -s channel-linkedin -t hermes-cli
```

## Phase 맵 (공통)

| Phase | 결정적 | M3 enhance |
|-------|--------|------------|
| P0 INPUT | brief + search_context | + 피드 관측(선택) |
| P1 CONTEXT | linkedin-context.md | + analysis.md |
| P2 ASSEMBLE | linkedin_*.md | strategy → draft |
| P3 VALIDATE | validate linkedin | checklist |
| P4 ARCHIVE | Notion | Permalink |

## 품질 (`config/content-guidelines.yaml#linkedin`)

- Hook 2줄 (see more 전)
- 1300자 이내, 문단 2줄 이내
- → 불릿 3–5개
- 댓글 CTA (질문)
- **링크:** 본문 최소 → 첫 댓글
- 해시태그 3–5, 1인칭 전문가 톤

## 템플릿

`templates/social/linkedin-post.md`

## Step Skills

- [01-analyze](01-analyze.md) — 피드·트렌드 분석
- [02-strategy](02-strategy.md) — 글 각도·훅 설계
- [03-draft](03-draft.md) — 포스트 초안
- [04-validate](04-validate.md) — 피드 문법 체크리스트

## Anti-patterns

- LinkedIn 공식 알고리즘 "재현·조작" 주장
- 본문 URL로 reach 희생
- hook 없이 장문 서론
- 데이터/출처 0개

## 컴플라이언스

- 사용자 제공 텍스트·brief·search_context만 분석
- 자동 피드 수집·API 연동 없음 (로컬 결정적 + 선택 LLM)
