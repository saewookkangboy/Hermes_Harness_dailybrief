---
name: humanize-korean
description: "im-not-ai 기반 한글 AI 티 제거 — 콘텐츠 파이프라인 문체 윤문."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [humanize, im-not-ai, korean, voice, style]
    related_skills: [content-orchestration, channels/blog, channels/linkedin]
    upstream: https://github.com/epoko77-ai/im-not-ai
---

# Humanize Korean (im-not-ai)

[im-not-ai](https://github.com/epoko77-ai/im-not-ai) — AI가 쓴 글이 아닌 것처럼 윤문.

## Hermes 통합

| 단계 | 방식 |
|------|------|
| **M2 결정적 (기본)** | `scripts/lib/humanize_korean.py` — assemble 후 자동 적용 |
| **M3 LLM (선택)** | `HERMES_HUMANIZE=1` → upstream `humanize-korean` skill |

설정: `config/voice-style.yaml`

## 4대 철칙 (upstream)

1. **의미 불변** — 사실·수치·URL·고유명사 보존
2. **근거 기반** — 탐지된 AI 티 패턴만 수정
3. **장르 유지** — B2B 블로그 / LinkedIn 전문가 톤
4. **과윤문 금지** — 변경률 30% 초과 경고

## 채널별 register

| 채널 | register | 금지 예 |
|------|----------|---------|
| blog | semi_formal (~다) | "~해요" 연속, "다음과 같아요" |
| linkedin | personal_expert (1인칭) | 템플릿 훅, 3인칭 나열 |
| instagram | casual | 과도 이모지 (칼럼·리포트는 C-5) |

## 제거 대상 (S1 핵심)

- D: "결론적으로", "시사하는 바", "주목할 만하다"
- A: "~를 통해", "~에 있어서", "~에 의해", 이중 피동
- H: 문두 "또한/따라서/나아가" 연속
- C: "첫째/둘째/셋째", 연결어미 뒤 쉼표

## 실행

```bash
# 결정적 (assemble-content-package.py 내장)
~/hermes-content-studio/scripts/run-content-package.sh

# LLM humanize (선택)
HERMES_HUMANIZE=1 ~/hermes-content-studio/scripts/run-content-package.sh
```

Upstream 설치 (별도):
```bash
git clone https://github.com/epoko77-ai/im-not-ai.git
cd im-not-ai && ./install.sh --codex-only
```

## Anti-patterns

- humanize로 SEO 구조(H1/H2/FAQ) 삭제
- URL·출처 변경
- LinkedIn을 과도한 격식체(~다만)로 통일
