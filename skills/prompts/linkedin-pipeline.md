# LinkedIn Pipeline — Analyze → Strategy → Draft

[linkedin-feed-strategy-maker](https://github.com/saewookkangboy/linkedin-feed-strategy-maker) API 파이프를 Hermes skill step으로 매핑.

## Hermes vs LFSA

| LFSA Route | Hermes |
|------------|--------|
| `/analyze` | `channels/linkedin/01-analyze.md` |
| `/strategy` | `channels/linkedin/02-strategy.md` |
| `/drafts` | `channels/linkedin/03-draft.md` |
| `/checklist` | `channels/linkedin/04-validate.md` |
| `/agent/pipeline` | M3 enhance: analyze→strategy→draft 연속 |
| 결정적 폴백 | `assemble-content-package.py` |

## 결정적 경로 (기본)

```bash
~/hermes-content-studio/scripts/run-content-package.sh
```

→ `linkedin-context.md` + `linkedin_*.md` (규칙 기반, OpenAI 불필요)

## M3 LLM 경로 (선택)

```bash
HERMES_ENHANCE=1 ~/hermes-content-studio/scripts/run-content-package.sh
```

또는:

```bash
~/hermes-content-studio/scripts/hermes-run.sh \
  "M3 LinkedIn: brief 기반 analyze→strategy→draft. 04-validate 체크리스트 준수." \
  --skills channel-linkedin -t hermes-cli
```

## 피드 문법 체크리스트

- 첫 2줄 = see more 전 가치
- dwell time: 짧은 문단, whitespace
- 댓글 CTA > 좋아요 유도
- native text > 외부 링크 본문
- personal_frame: 1인칭 전문가

## 컴플라이언스

- LinkedIn 공식 알고리즘 재현·조작 없음
- 사용자 제공·리서치 수집 텍스트만 사용
- 자동 피드 API 없음

## Handoff

M3 완료 → M5 `archive-to-notion.sh` → Telegram Permalink
