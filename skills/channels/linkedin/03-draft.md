# LinkedIn Step 3 — Draft (M3)

**입력:** `{date}_linkedin-strategy.md`, `{date}_linkedin-context.md` (결정적 산출물)
**템플릿:** `templates/social/linkedin-post.md`

## 목적

전략을 **1300자 이내 포스트 초안**으로 작성합니다.

## 출력

`content/linkedin/{date}_linkedin_{slug}.md`

구조:
```
### Hook (첫 2줄)
...

### Context
...

### Insight
→ ...
→ ...
→ ...

### Actionable takeaway
...

### CTA
...

---
#hashtag ...
```

## 작성 규칙

1. 1인칭 전문가, 과장 금지
2. whitespace breaks — 문단 2줄 이내
3. 데이터/출처 1개 이상 (brief 인용)
4. 본문 URL 없음 — "첫 댓글에 URL" 멘트만
5. 한국어, 기술 용어 영문 병기

## 결정적 vs LLM

- **기본:** `assemble-content-package.py` → context + md
- **M3 enhance:** strategy 기반으로 draft 덮어쓰기 (구조 유지)

## 다음

→ `04-validate.md`
