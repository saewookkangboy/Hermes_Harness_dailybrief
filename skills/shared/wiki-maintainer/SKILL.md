---
name: wiki-maintainer
description: "LLM Wiki 유지보수 — Ingest · Query · Lint. Karpathy 패턴, Hermes 이중 메모리 계층."
version: 1.0.0
author: chunghyo
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [wiki, memory, second-brain, ingest, lint]
    related_skills: [marketing-research, personal-assistant, harness-ops]
---

# Wiki Maintainer — LLM Wiki 스키마

전략 SoT: `docs/LLM-WIKI-INTEGRATION.md` · 설정: `config/wiki.yaml`

**원칙:** 일별 `{date}_brief.md` SoT는 유지. Wiki는 **누적 합성 계층**만 담당.

## 디렉터리

| 경로 | 역할 | 수정 주체 |
|------|------|----------|
| `content/research/raw/` | 불변 소스 (클립·PDF·메모) | 사람 |
| `content/wiki/concepts/` | topic_key 개념 페이지 | Seed(결정적) · Ingest(LLM) |
| `content/wiki/entities/` | 회사·제품 엔티티 | Ingest(LLM) |
| `content/wiki/index.md` | 카탈로그 (Query 시 1순위) | Seed · Ingest |
| `content/wiki/log.md` | append-only 타임라인 | 모든 작업 |
| `content/wiki/output/` | Query·비교·분석 아카이브 | Query |

## 페이지 형식

```markdown
---
topic_key: llm_anthropic
updated_at: YYYY-MM-DD
source_count: 3
streak_days: 2
---

# {제목}

## 최신 요약
{한국어 2~4문장}

## 출처
- YYYY-MM-DD: [제목](url)

## 관련
[[korea_ax]] · [[general]]
```

내부 링크: `[[wikilink]]` 권장.

## Workflow: Ingest (`HERMES_WIKI_INGEST=1`)

1. `content/research/raw/` 신규 파일 읽기
2. 사용자와 핵심 takeaway 확인 (선택)
3. `wiki/sources/` 요약 페이지 작성 (있을 경우)
4. `wiki/index.md` 갱신
5. 관련 `concepts/` · `entities/` 10~15페이지까지 갱신
6. 모순 시 기존 페이지에 `> ⚠️ 모순` callout
7. `wiki/log.md` append: `## [YYYY-MM-DD] ingest | {제목}`

**금지:** M1 `run-research-brief.sh` 동기 경로에서 Ingest 실행.

## Workflow: Query (`/ask`)

1. `wiki/index.md` 읽기 → 관련 페이지 목록
2. concepts · entities · brief fallback 순 읽기
3. 출처 링크 포함 합성
4. 가치 있는 답변 → `wiki/output/{date}_{slug}.md` 저장
5. `wiki/log.md` append: `## [YYYY-MM-DD] query | {질의 요약}`

## Workflow: Lint (`HERMES_WIKI_LINT=1`)

1. concepts · entities 전수 스캔
2. 검사: 모순 · stale URL · orphan · 누락 개념 페이지 · broken wikilink
3. `content/logs/{date}_wiki-lint-report.md` 작성
4. `wiki/log.md` append: `## [YYYY-MM-DD] lint | {이슈 N건}`

## 실행

```bash
# 결정적 Seed (LLM 없음)
HERMES_WIKI_SEED=1 ~/hermes-content-studio/scripts/wiki-seed.sh

# LLM Ingest
HERMES_WIKI_INGEST=1 ~/hermes-content-studio/scripts/run-wiki-ingest.sh

# LLM Lint
HERMES_WIKI_LINT=1 ~/hermes-content-studio/scripts/run-wiki-lint.sh

# 구조 eval
~/hermes-content-studio/scripts/wiki-lint-eval.sh
```

## 도구

- `-t hermes-cli` only (콘텐츠 파이프라인과 동일 tool masking)
- `web_search`는 wiki miss + brief miss 시에만
