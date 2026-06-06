---
name: shared-handoff
description: "M1~M5 단계 간 handoff JSON 스키마·데이터 연속성 규칙."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [handoff, M1, M2, orchestration]
    related_skills: [content-orchestration]
---

# Shared: Handoff

[marketing-ai-orchestration-harness](https://github.com/saewookkangboy/marketing-ai-orchestration-harness) 데이터 연속성 규칙.

## 스키마

- `schemas/handoff.schema.json`
- `schemas/content-input.schema.json`

## 필수 필드

| 필드 | 설명 |
|------|------|
| `stage` | M1 \| M2 \| M3 \| M4 \| M5 \| SYNTH |
| `channel` | research \| blog \| instagram \| linkedin \| unified \| all |
| `inputs_used` | brief_path, search_context, local_docs[] |
| `artifacts.paths` | 생성 파일 경로 |
| `next_stage_ready` | false면 재실행 |
| `handoff_payload` | 다음 stage 입력 |

## M1 → M2 예시

```json
{
  "stage": "M1",
  "channel": "research",
  "assumptions": ["주간 트렌드 리서치, 한국 시장 1건 포함"],
  "inputs_used": {
    "brief_path": "content/research/2026-06-06_brief.md",
    "search_context": "content/research/_search_context_2026-06-06.md"
  },
  "artifacts": {
    "paths": ["content/research/2026-06-06_brief.md"],
    "conditions_applied": ["topic_clusters from Top 5"]
  },
  "quality_notes": ["validate-output.sh research PASS"],
  "next_stage_ready": true,
  "handoff_payload": {
    "topic_clusters": [
      {"topic": "AX 전환", "channels": ["blog", "linkedin"], "insight_ref": "#1"}
    ],
    "content_calendar": []
  }
}
```

## SYNTH (통합)

M2 완료 후 `content/packages/{date}_unified-context.md`를 SYNTH stage로 기록.

## 규칙

1. `inputs_used.local_docs` — 실제 인용 경로 (감사 가능)
2. handoff 누락 시 다음 stage **재실행** (건너뛰기 금지)
3. `content_output_conditions` → `artifacts.conditions_applied`
