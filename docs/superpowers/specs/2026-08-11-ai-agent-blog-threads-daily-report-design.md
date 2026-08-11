<p align="center">
  <img src="../../../assets/docs/plan-blog-threads.svg" width="100%" alt="Design — AI Agent Blog + Threads from Brief SoT">
</p>

# Design: AI Agent 일일 리서치 → Velog형 블로그 + Threads 패키지

**Date:** 2026-08-11  
**Status:** Approved (conversation)  
**Approach:** Config + Assembler 교체 (방식 1)  
**Reference example:** [Velog — 오늘의 AI 트렌드 (08/10)](https://velog.io/@troedynamo/%EC%98%A4%EB%8A%98%EC%9D%98-AI-%ED%8A%B8%EB%A0%8C%EB%93%9C-%ED%86%B5%EC%A0%9C%EA%B6%8C%EA%B3%BC-%EC%98%88%EC%82%B0%EA%B9%8C%EC%A7%80-%EA%B0%96%EC%B6%98-AI-%EC%97%90%EC%9D%B4%EC%A0%84%ED%8A%B80810)

## 1. Goal

AI Agent 관련 최신 동향·이슈를 수집해 매일:

1. SEO/GEO 최적화된 **Velog형 블로그** 완성형 리포트
2. 리드/트래픽 유도용 **Threads** 숏폼

을 Copy & Paste 가능한 형태로 함께 전달한다.

LinkedIn · Instagram · Newsletter는 **기존 채널 포맷을 유지**하고, Brief 소재만 새 리서치 렌즈를 사용한다.

## 2. Decisions (locked)

| ID | 결정 | 선택 |
|----|------|------|
| D1 | M1 Brief 수집 범위 | **A** — Brief 자체를 AI Agent 중심(뉴스·기술·산업·보안/거버넌스)으로 전환. LI/IG/NL은 포맷 유지, 소재는 새 Brief |
| D2 | Threads 산출 위치 | **C** — 우선 `content/packages/{date}_threads.md` 동반 산출. 안정화 후 `content/threads/` 채널 승격 |
| D3 | 블로그 산출 형태 | **A** — 패키지 MD를 Velog형(~3,000자)으로 교체 + HTML 동일 구조. 긴 FAQ JSON-LD / Direct Answer 우선 블록은 제거·비필수 |
| D4 | 구현 방식 | **방식 1** — Config + Assembler 교체 (결정적 Brief SoT 유지) |

## 3. Architecture / Data flow

```
gather-web-research (AI Agent queries)
        ↓
content/research/{date}_brief.md   (Top N insights, Brief SoT)
        ↓
M2 run-content-package
        ├─ content/packages/{date}_blog-article.md   ← Velog형
        ├─ content/blog/{date}_blog_*.html           ← 동일 섹션 HTML
        ├─ content/packages/{date}_threads.md        ← Threads 숏폼
        ├─ content/linkedin/...                      ← 기존 포맷
        ├─ content/instagram/...                     ← 기존 포맷
        └─ (M2b) content/newsletter/...              ← 기존 포맷
        ↓
validate-output.sh → (optional) archive-to-notion.sh
```

원칙:

- Brief SoT 유지 (`content/research/{date}_brief.md`)
- 결정적 조립 우선 (LLM polish는 기존과 같이 선택)
- 채널 포맷 분리는 assembler / validate에서만 수행

## 4. M1 Research lens

### 4.1 Persona (조정)

현업 디지털 마케터 / 성장 전략가 시선. AI Agent 동향을 마케팅·도입·거버넌스 관점으로 해석.

### 4.2 Coverage pillars (교체 대상)

기존 LLM 4사·AX 분산 렌즈를 다음 축으로 재정의:

| Pillar | 수집 초점 |
|--------|-----------|
| agent_news | AI Agent 최신 뉴스·제품 발표 |
| agent_tech | 멀티에이전트·툴유즈·예산/결제·런타임 등 기술 트렌드 |
| agent_industry | 산업·엔터프라이즈 적용 사례 |
| agent_security_gov | 보안·통제권·거버넌스·규제(예: EU AI Act) |

`config/research-brief.yaml`의 `coverage.pillars`, `search_queries`, `priority_queries`를 위 축에 맞게 교체한다.  
`insight_limit`은 기존 7을 유지하되, 블로그 본문은 Top 이슈를 **테마로 압축**해 ≤3,000자에 맞춘다 (Brief 표 ≠ 블로그 장문 FAQ).

### 4.3 Freshness

기존 `freshness` / `schedule.period: single_day` 유지. 일일 렌즈.

## 5. Blog format (Velog형)

### 5.1 Paths

- `content/packages/{date}_blog-article.md` (주 산출 · Copy & Paste)
- `content/blog/{date}_blog_{slug}.html` (동일 구조 HTML)

### 5.2 Required sections

1. **제목:** `[오늘의 AI 트렌드] {핵심 한 줄}({MM/DD})`
2. **프롤로그** (날짜 헤더 + 도입 2–4문단; 별도 H2 없어도 됨)
3. **주요 트렌드 및 개발 이슈** — validate 매칭 H2: `## 1. 주요 트렌드 및 개발 이슈` (하위 H3 ①②…)
4. **요즘 주목하는 기술** — H2: `## 2. 요즘 주목받는 핵심 기술` (또는 `## 2. 요즘 주목하는 기술`)
5. **마케터/전략가를 위한 시사점** — H2: `## 3. 마케터 및 비즈니스 리더를 위한 향후 대책` (또는 동등 시사점 헤더)
6. **출처** — `🔗 출처` 또는 `## 출처` + `https://` ≥ 1
7. **한 줄 요약** — `💡 한 줄 요약` 또는 `## 한 줄 요약`

참고 예시(Velog) 헤더 문구를 기본으로 하고, validate는 **동의어 헤더 1개 이상** 허용으로 구현한다.

### 5.3 Constraints

| 항목 | 규칙 |
|------|------|
| 분량 | 공백 포함 ≤ 3,000자 (본문; 출처 URL 목록은 soft) |
| 톤 | `~습니다` / `~합니다` (`formal_hamnida`) |
| SEO/GEO | H2/H3 구조, 핵심 키워드 맥락 배치, 요약·시사점, 출처 URL |
| 제거/비필수 | 긴 FAQ JSON-LD blocking, Direct Answer 최상단 우선 블록, 기존 `ax-faq` 장문 가이드 템플릿 |
| 가독성 | 단락 구분, bullet, 강조 표기 |

### 5.4 HTML

MD와 동일 섹션으로 렌더. FAQ 스키마 강제하지 않음. 메타 title/description은 제목·한 줄 요약에서 파생.

## 6. Threads format (package companion)

### 6.1 Path

`content/packages/{date}_threads.md`

### 6.2 Structure

1. 후킹 헤드라인
2. 임팩트 핵심 포인트 3–5줄 (숏폼)
3. 블로그 유입 문구 + `[블로그 링크]` 플레이스홀더
4. 댓글 참여/질문 CTA

톤: 숏폼·호기심 유도. LinkedIn 해요체 게이트와 분리 (독립 soft validate).

### 6.3 Future promotion

안정화 후 `content/threads/` 채널 + `validate-output.sh threads` + studio/orchestration 정식 등록.

## 7. Validation gates

### 7.1 Change — blog / blog-article

**Blocking:**

- 필수 섹션 헤더 존재
- 본문 ≤ 3,000자
- 출처 URL ≥ 1
- 제목 패턴 또는 `[오늘의 AI 트렌드]` 포함

**Non-blocking / removed as hard fail:**

- FAQ JSON-LD 필수
- GEO 인용 블록 필수
- Direct Answer first 필수
- min_h2_sections=5 (기존 longform) — Velog 섹션 수에 맞게 재정의

### 7.2 New — threads-package (soft)

- 헤드라인 존재
- `[블로그 링크]` 존재
- CTA(질문/댓글 유도) 존재

### 7.3 Unchanged

- `linkedin`, `instagram`, `newsletter` (+ paste/subject-scores 등) 게이트

## 8. Config / code touch list

| Area | Files (expected) |
|------|------------------|
| Research | `config/research-brief.yaml`, gather query consumers |
| Blog assemble | `scripts/lib/content_quality.py`, `scripts/lib/longform_context.py`, `templates/html/blog-post.html` (as needed) |
| Threads | assemble path in content package writer |
| Quality SoT | `config/content-quality.yaml` (`longform.blog`, `seo_aeo_geo` flags for blog) |
| Validate | `scripts/validate-output.sh` |
| Orchestration | `config/content-orchestration.yaml` (threads package output) |
| Archive (optional) | `config/notion-archive.yaml` (threads glob) |
| Skills | `skills/channels/blog/SKILL.md`, research skill docs |
| Progress | `.harness/progress.md` |

## 9. Out of scope

- LinkedIn / Instagram / Newsletter format or validate changes
- Lectures, wiki seed/ingest
- Threads formal channel (`content/threads/`) in this iteration
- Auto-publish to Velog / Threads / ESP
- LLM으로 Brief·블로그 전체 재생성 (결정적 조립 유지)

## 10. Definition of Done

1. `scripts/run-research-brief.sh` → AI Agent 렌즈 Brief
2. `scripts/run-content-package.sh` → Velog형 blog MD/HTML + `{date}_threads.md`
3. LI / IG / NL 기존 validate PASS
4. `validate-output.sh blog` 및 `blog-article` 신 게이트 PASS
5. Threads soft validate PASS (또는 warn-only with documented gate)
6. `.harness/progress.md` 업데이트

## 11. Rollback

- Revert `research-brief.yaml` + blog/threads assembler commits → previous lens and FAQ blog
- Threads package files are additive; no channel directory migration to reverse
- LI/IG/NL assemblers unchanged → format regression risk low

## 12. Risks / mitigations

| Risk | Mitigation |
|------|------------|
| Brief 테마가 AI Agent로 좁혀져 LI/IG/NL 소재 다양성 감소 | pillars에 industry·security 포함, insight_limit 7 유지 |
| 3,000자 캡으로 출처·시사점 잘림 | 출처 목록 soft; 본문만 hard cap |
| 기존 FAQ/GEO eval·coach trait 실패 | blog coach traits·eval 스크립트를 신 게이트에 맞춤 (구현 계획에서 명시) |
| Notion archive가 구 blog 스키마 가정 | archive excerpt 길이·섹션 키 확인 후 최소 수정 |

## 13. Implementation note

코드 구현은 본 스펙 승인 후 `writing-plans` → 구현 계획 → 하네스/에이전트 규칙에 따라 진행한다.  
이 문서는 설계 SoT이며, 구현 중 게이트 세부 문자열은 plan에서 확정한다.
