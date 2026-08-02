<p align="center">
  <img src="../../../assets/docs/plan-newsletter.svg" width="100%" alt="Newsletter Production Readiness (implementation) plan banner">
</p>

> 구현 계획 문서 · [Docs 허브](../../README.md) · 현행 로직: [`SYSTEM-LOGIC.md`](../../architecture/SYSTEM-LOGIC.md)

# Newsletter Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Daily Brief 신선도를 보존하면서 이메일·LinkedIn 장문·실CTA·16:9 이미지 프롬프트·붙여넣기 팩을 품질 게이트 통과 후에만 발행 가능 상태로 만든다.

**Architecture:** 결정적 셀렉터(선별·중복·안전·정합) → 선택적 LLM 산문(`HERMES_ENHANCE=1`) → 결정적 검증/승인 게이트. 게이트 실패 시 Notion 배포 차단.

**Tech Stack:** Python 3, `scripts/lib/newsletter_*.py`, `config/newsletter.yaml`, `validate-output.sh`, `newsletter-eval.sh`, JSONL issue ledger

**Spec:** `docs/plans/2026-07-27-001-feat-newsletter-production-readiness-plan.md` (R1–R30)

## Global Constraints

- Daily Brief SoT 유지 — 뉴스레터 전용 리서치 파이프라인 추가 금지
- `HERMES_ENHANCE=0`/LLM 실패 시에도 신선한 결정적 초안 필수
- 이미지 API 호출·실제 PNG 생성 금지 (프롬프트만)
- ESP 자동 발송 금지 (`esp_send: false` 유지)
- 단일 CTA + 실제 HTTPS URL만 허용
- 품질 게이트 실패 시 발행 가능 표시·Notion 배포 금지
- 평가 시드 CTOR을 실측 학습으로 취급 금지

## Quality Approval Gates (사용자 요청)

| Gate | 통과 조건 | 실패 시 |
|------|-----------|---------|
| **A** Freshness/Safety/Title | 최근 7호와 제목·Hero 비반복, NSFW 제외, 영문↔한글 정합 | 보완 후 재검증 |
| **B** Email/LinkedIn/CTA/Image | 이메일 600–1200단어, LI 800–1500단어, HTTPS CTA, 16:9 프롬프트 | 보완 후 재검증 |
| **C** Validate/Publish Block | `validate-output` + freshness/consistency eval PASS, Notion 차단 동작 | 보완 후 재검증 |
| **D** CTOR Learning + E2E | 시드 제외 학습, 당일 샘플 재생성 품질 통과 | 보완 후 재검증 |

각 Gate 종료 시 **사용자 승인** 후 다음 Gate 진행.

## File Map

| File | Responsibility |
|------|----------------|
| `config/newsletter.yaml` | 패턴·안전 블록·길이·게이트·제목 로테이션 설정 |
| `scripts/lib/newsletter_select.py` | 인사이트 선별·중복 원장·안전 필터·제목 정합 |
| `scripts/lib/newsletter_issue_ledger.py` | 최근 N호 topic/title/url/pattern 원장 |
| `scripts/lib/newsletter_quality.py` | 조립기 재구성 — 하드코딩 Hero/CTA 제거 |
| `scripts/lib/newsletter_linkedin.py` | LinkedIn 장문 조립 |
| `scripts/lib/newsletter_image_prompt.py` | 16:9 타이틀 이미지 프롬프트 |
| `scripts/lib/newsletter_cta.py` | 실제 HTTPS CTA 생성·검증 |
| `scripts/lib/newsletter_gates.py` | freshness/consistency/boilerplate/CTA 게이트 |
| `scripts/lib/newsletter_paste.py` | paste 팩에 LinkedIn·이미지·CTA URL 섹션 추가 |
| `scripts/lib/newsletter_html.py` | HTML에 이미지 자리·실CTA |
| `scripts/lib/newsletter_subject.py` | 패턴 로테이션·시드 제외 피드백 |
| `scripts/lib/newsletter_ctor_feedback.py` | 시드 제외·패턴별 가중치 |
| `scripts/validate-output.sh` | 신규 타입·게이트 연결 |
| `scripts/newsletter-eval.sh` | Gate A–D 자동 점검 |
| `scripts/run-newsletter.sh` | 게이트 실패 시 exit≠0 |
| `content/newsletter/issue-ledger.jsonl` | 발행 이력 원장 |

---

### Task 1: Gate A — Freshness, Safety, Title Selection

**Files:**
- Create: `scripts/lib/newsletter_issue_ledger.py`
- Create: `scripts/lib/newsletter_select.py`
- Create: `scripts/lib/newsletter_gates.py` (freshness/safety 부분)
- Modify: `config/newsletter.yaml`
- Modify: `scripts/lib/newsletter_quality.py` (`_newsletter_title`, `_subject_candidates`, assemble entry)
- Test: `scripts/newsletter-freshness-eval.sh` (신규)

**Interfaces:**
- Produces: `select_issue_insights(stamp, insights, cfg) -> SelectedIssue`
- Produces: `SelectedIssue{hero, modules[3], topic_key, subject_pattern, cta_url, reasons}`
- Produces: `append_issue_ledger(stamp, payload)`, `recent_topics(n=7)`
- Produces: `assert_freshness(stamp, md_text, cfg) -> list[str]` failures

- [ ] **Step 1: Add config for freshness/safety/patterns**

In `config/newsletter.yaml` add:

```yaml
freshness:
  lookback_issues: 7
  max_topic_reuse: 0
  max_subject_pattern_streak: 1
  ledger_path: content/newsletter/issue-ledger.jsonl

safety:
  block_url_substrings:
    - undress
    - undresser
    - nsfw
    - deepnude
  block_title_substrings:
    - Undress
    - NSFW

subject_patterns:
  - id: question
    template: "{topic} — 지금 손댈 곳은?"
  - id: number
    template: "{topic}, 3분이면 돼요"
  - id: contrast
    template: "{topic} — PoC가 아니라 FAQ"
  - id: noun
    template: "{topic} 실무 체크리스트"

title_integrity:
  prefer_source_when_korean_mismatch: true
  stale_korean_titles:
    - "한국 AX 전환 — 교육·FAQ·사례 중심"
    - "ChatGPT Workspace Agents 실무 검토"
    - "Claude 엔터프라이즈 — 거버넌스·컨텍스트"
```

- [ ] **Step 2: Implement issue ledger**

`newsletter_issue_ledger.py`: append-only JSONL with `{stamp, topic_key, subject, pattern_id, urls[], hero_hash}`. `recent(n)` returns last n stamps newest-first.

- [ ] **Step 3: Implement selector with title integrity**

When Korean title is in `stale_korean_titles` OR clearly mismatches English source (ads title vs Workspace body), rebuild display title from English source via improved `localize_title` path that preserves concrete nouns (HSAD, Deep Agent Builder, ChatGPT ads) instead of collapsing to AX boilerplate.

Reject insights matching safety blocklists. Skip topics present in last `lookback_issues`. Rotate subject pattern so same `pattern_id` is not used on consecutive issues.

- [ ] **Step 4: Wire selector into `assemble_newsletter`**

Replace `insights[:3]` blind slice with `select_issue_insights`. Replace `_newsletter_title` static collapse. Remove hardcoded SEO/AEO sentence from `_hero_block`.

- [ ] **Step 5: Freshness eval script + run Gate A quality check**

Create `scripts/newsletter-freshness-eval.sh` that:
1. Regenerates today with `HERMES_ENHANCE=0`
2. Asserts winner subject ≠ last 7 identical winners
3. Asserts no blocked URLs
4. Asserts no stale Korean boilerplate as winner when fresher source exists

**Gate A Approval:** Show before/after subject+Hero for 2026-07-27; wait for user OK.

---

### Task 2: Gate B — Email Longform, LinkedIn, CTA, Image Prompt

**Files:**
- Create: `scripts/lib/newsletter_cta.py`
- Create: `scripts/lib/newsletter_linkedin.py`
- Create: `scripts/lib/newsletter_image_prompt.py`
- Modify: `scripts/lib/newsletter_quality.py`
- Modify: `scripts/lib/newsletter_html.py`
- Modify: `scripts/lib/newsletter_paste.py`
- Modify: `templates/email/newsletter.html` (image slot)

**Interfaces:**
- Produces: `build_cta(ins, stamp, cfg) -> Cta{label, url, reason}`
- Produces: `build_linkedin_article(stamp, selected, cfg) -> Path`
- Produces: `build_title_image_prompt(stamp, selected) -> Path`
- CTA URL resolution order: blog permalink for stamp → Notion archive URL → insight.source URL (must be https)

- [ ] **Step 1: Real CTA module** — reject `#`, empty, placeholder phrases
- [ ] **Step 2: Expand email body** to 600–1200 words with problem→explanation→insight→apply; no process notes
- [ ] **Step 3: LinkedIn article** 800–1500 words, H2 every ~250 words, image alt slot, single CTA
- [ ] **Step 4: 16:9 image prompt file** with topic/metaphor/composition/color/lighting/forbidden/text-overlay
- [ ] **Step 5: Update paste pack** sections §1–§7 (subject, preheader, email md, html, linkedin, cta url, image prompt)
- [ ] **Step 6: Regenerate sample and measure lengths**

**Gate B Approval:** Paste pack preview + word counts + CTA URL; wait for user OK.

---

### Task 3: Gate C — Validation & Publish Blocking

**Files:**
- Modify: `scripts/validate-output.sh`
- Modify: `scripts/newsletter-eval.sh`
- Modify: `scripts/run-newsletter.sh`
- Modify: `scripts/lib/newsletter_gates.py`
- Modify: `scripts/archive-to-notion.sh` or newsletter Notion step to respect publish flag

- [ ] **Step 1: Gates** — freshness, title-body-source consistency, CTA https, boilerplate ban (`SEO·AEO·GEO 인용`, `맥롽`, `통합 컨텍스트에서 전문`), length bands
- [ ] **Step 2: `validate-output.sh`** newsletter / paste / new linkedin-newsletter / title-image types
- [ ] **Step 3: On gate fail** write `content/packages/{stamp}_newsletter-publish.json` with `{"publishable": false, "failures":[...]}` and exit 1
- [ ] **Step 4: Notion archive skips** non-publishable newsletter categories
- [ ] **Step 5: Eval report includes Gate A/B/C rows**

**Gate C Approval:** Fail-injection test (bad CTA) blocked + good run passes; wait for user OK.

---

### Task 4: Gate D — CTOR Learning Hardening + E2E

**Files:**
- Modify: `scripts/lib/newsletter_ctor.py`
- Modify: `scripts/lib/newsletter_ctor_feedback.py`
- Modify: `scripts/lib/newsletter_subject.py`
- Modify: `.harness/feature_list.json` / `.harness/progress.md`

- [ ] **Step 1:** Mark seed records (`notes` contains `p4-eval-seed` or `seed:true`) excluded from feedback
- [ ] **Step 2:** Record pattern_id with campaigns; weight by pattern not only traits
- [ ] **Step 3:** Add replies/unsub optional fields to metrics schema
- [ ] **Step 4:** Full E2E: `run-newsletter.sh 2026-07-27 --validate` + freshness-eval + newsletter-eval PASS
- [ ] **Step 5:** Update progress.md with Gate results

**Gate D Approval:** Final sample package review; user signs off for merge/commit.

---

## Spec Coverage Checklist

| Req | Task |
|-----|------|
| R1–R6, AE1–AE3, AE6 | Task 1 |
| R7–R23, AE5, AE7 | Task 2 |
| R28–R30, AE4 | Task 3 |
| R24–R27, AE8 | Task 4 |
