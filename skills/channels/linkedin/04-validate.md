# LinkedIn Step 4 — Validate (M3)

## 자동 검증

```bash
~/hermes-content-studio/scripts/validate-output.sh linkedin-context content/packages/YYYY-MM-DD_linkedin-context.md
~/hermes-content-studio/scripts/validate-output.sh linkedin content/linkedin/YYYY-MM-DD_linkedin_*.md
```

## 피드 문법 체크리스트 (linkedin-feed-strategy-maker)

- [ ] 첫 2줄만으로 가치 전달 (see more 전)
- [ ] 1300자 이내
- [ ] → 불릿 3개 이상
- [ ] 댓글 유도 질문 1개
- [ ] 본문 URL 없음 (첫 댓글 전략)
- [ ] 해시태그 3–5
- [ ] 1인칭 전문가 톤
- [ ] 출처/데이터 1개 이상
- [ ] whitespace breaks (짧은 문단)

## 실패 시

| 실패 | 조치 |
|------|------|
| 1300자 초과 | 불릿·Context 압축 → 03-draft 재실행 |
| hook 약함 | 02-strategy hook 재설계 |
| URL 본문 | 제거 + CTA 수정 |

## Handoff → M5

```json
{
  "stage": "M3",
  "channel": "linkedin",
  "next_stage_ready": true,
  "artifacts": {
    "paths": ["content/linkedin/...", "content/packages/..._linkedin-context.md"]
  }
}
```

## Archive

```bash
~/hermes-content-studio/scripts/archive-to-notion.sh YYYY-MM-DD --force
```
