---
title: M1 Research Brief Redesign - Plan
date: 2026-07-20
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-brainstorm
execution: code
---

# M1 Research Brief Redesign - Plan

## Goal Capsule

- Objective: Raise research trust and channel content quality while keeping Brief SoT stable, and let Slack keyword research merge (default) or replace (flag) into the daily pipeline—with an optional approval track for high-risk writes.
- Product authority: Hermes Content Studio daily M1→M5 pipeline; `{date}_brief.md` remains the content SoT; deterministic gather/assemble preferred over full LLM regenerate.
- Open blockers: none. Planning pins below resolve prior deferred questions (`require_approve_on_replace: true`, Top N = 7, research staging commands separate from publish HITL).

## Product Contract

### Summary

Phased redesign of M1: **P1** strengthens trust/diversity/handoff gates and Slack keyword merge/replace on the existing gather→assemble→validate path; **P2** introduces an Evidence Pack middle SoT that Brief and (optionally) downstream consume; **P2b** ships research staging via **dedicated** `/research-pending` → `/research-approve` (not publish `/pending`/`/approve`) so replace and opt-in runs never silently overwrite live Brief.

### Problem Frame

Daily Top-7 briefs feel shallow, repetitive, and weakly differentiated, so blog/LinkedIn/newsletter inherit weak hooks.
Process is search-snippet assembly without a durable evidence layer, which hurts trust and auditability.
Slack can trigger `/research`, but keyword-driven research does not reliably rewrite Brief SoT and re-run content packages under clear merge/replace/approve rules.

### Key Decisions

- **Staged delivery (option 4):** Ship P1 fast gates first; then P2 Evidence Pack as the structural upgrade; P2b approval track ships with P1 commands and deepens with Evidence staging in P2.
- **Default merge, explicit replace:** `/research <keywords>` merges into today's Brief; `--replace` only replaces SoT.
- **Approval is complementary, not default:** Auto-reflect on merge unless `--approve`. Replace defaults to requiring approve (`require_approve_on_replace: true`).
- **Research staging ≠ publish HITL:** Existing `/pending`/`/approve` remain publish-queue only (`.harness/publish-queue/`). Research uses `/research-pending` and `/research-approve`.
- **Brief SoT unchanged for consumers:** `{date}_brief.md` stays M2/M2b/Notion contract; Evidence is upstream input, not a breaking channel dependency in P1.
- **One ops path, variable depth:** Daily cron and Slack keyword share the same schemas; keyword runs may gather deeper but do not invent a second Brief format.
- **Wiki LLM stays off M1 SLA:** Optional wiki seed remains outside the blocking path (`HERMES_WIKI_SEED`).
- **NL collision avoidance:** Bare 「승인」/ `/approve` stays **publish-only**. Research approve NL is 「리서치 승인」 / `/research-approve` only.
- **Keyword delivery:** Fixed `quick_commands.research` cannot carry args — keyword mode uses `telegram-pipeline.sh auto "<message>"` and/or `HERMES_RESEARCH_KEYWORDS` + flags env; `qc research` with argv when Hermes forwards trailing args (detect and support both).
- **channel_hooks P1 vs P1b:** P1 emits + validates hooks on Brief; M2 structured consume is U4b in same P1 release train (Success Criteria requires U4b before claiming channel consumption).
- **PlayMCP:** Same `qc` spine — include `config/playmcp-routing.yaml` in P1 commander parity (**confirmed 3-A**).

### Actors

- Operator (Slack/Telegram commander): requests keyword research, chooses flags, approves research staging.
- Deterministic M1 pipeline: gather, (P2) evidence, assemble, validate, brief_gate.
- Downstream M2/M2b: consume Brief (+ handoff fields); skip if gate fails.
- Research approval track: `content/research/_staging/` + `/research-pending` + `/research-approve`.
- Publish HITL (unchanged): `.harness/publish-queue/` + `/pending` + `/approve`.

### Key Flows

```text
[cron queries] OR [Slack/TG /research keywords [--replace] [--approve]]
        │
        ▼
   gather (+ keyword queries when present)
        │
        ▼
   P1 gates on results ──► (P2) Evidence Pack
        │
        ├─ default merge → validate → Brief SoT → M2/M2b
        ├─ --replace + require_approve → research staging only
        ├─ --approve → research staging only
        └─ /research-approve → commit SoT (+ evidence) → M2/M2b
```

**F1. Keyword merge (default):** Operator sends `/research RAG 평가`. System gathers, merges insights (keyword wins on URL/title similarity), caps Top N, validates, updates Brief, runs content package, replies with paths/summary.

**F2. Replace with approve (default policy):** Operator sends `/research … --replace`. System builds staging candidate, warns that live Top N will be discarded on approve, lists via `/research-pending`. Live Brief unchanged until `/research-approve`.

**F3. Opt-in approve on merge:** `/research … --approve` writes staging merge candidate; `/research-approve` applies merge transactionally.

**F4. Daily cron:** Unchanged entrypoint timing; after P2, writes thin Evidence then Brief; no research approve required.

**F5. Failure:** Gather/validate failure keeps previous Brief; Slack gets failure notice; no partial SoT write.

### Requirements

**Trust and quality (P1)**

- R1. Source trust scoring and deny/spam filters apply before insight selection; each insight exposes a trust/confidence field.
- R2. Topic diversity limits near-duplicate stories across the Top N (cluster/similarity cut plus priority-query balance).
- R3. Validate rejects generic reinterpretation and English-snippet paste patterns; KO summary minimum length and marketer-view duplication checks remain blocking.
- R4. Each insight includes `channel_hooks` (blog, linkedin, instagram, newsletter one-liners) for M2 consumption.
- R5. A research-trust eval covers URL presence, duplicate rate, diversity, and handoff field coverage.

**Slack keyword → pipeline (P1)**

- R6a. `/research <keywords>` (or auto/env equivalent) runs keyword-augmented gather, **merges** into `{date}_brief.md`, and validates (SoT update).
- R6b. After a successful live SoT commit from keyword merge or research-approve, re-run M2 + M2b (content package + newsletter).
- R7. `/research <keywords> --replace` produces a full Brief replacement candidate; with `require_approve_on_replace: true` it only lands via `/research-approve`. When config sets `require_approve_on_replace: false`, replace writes SoT immediately after validate (with `.prev.md` backup) and then R6b.
- R8. `/research <keywords> --approve` (with or without `--replace`) writes research staging only; live SoT unchanged until research-approve.
- R9. `/research-pending` lists staging runs (id, keywords, mode, time, insight count); `/research-approve [id|all]` commits then runs R6b.
- R10. Keyword-less `/research` keeps today's daily M1 behavior.
- R11. Natural-language intents: merge default; 「교체」→replace; 「리서치 승인」→`/research-approve`. Bare 「승인」 must not map to research.
- R11b. Publish `/pending`/`/approve` behavior and queue paths must remain unchanged (bidirectional isolation).
- R11c. Keyword/flag delivery works via `auto "<message>"` and/or env (`HERMES_RESEARCH_KEYWORDS`, `HERMES_RESEARCH_REPLACE`, `HERMES_RESEARCH_APPROVE`) when slash QC cannot forward argv.

**Stability and ops**

- R12. Before SoT overwrite, write `*_brief.prev.md` (or equivalent); failed validate/write restores previous Brief.
- R13. Merge and approve applies are transactional: all-or-nothing for Brief (+ evidence when present); never half-merged Top N.
- R14. Each run records an audit file under `content/research/_runs/` with requester, mode, keywords, fingerprint, output paths.
- R15. Same-day same-keyword fingerprint may skip or announce refresh rather than silently duplicating work.
- R16. `brief_gate` continues to block M2 when Top N or Executive Summary (and after P2, minimum evidence claims) are unmet.

**Evidence Pack (P2)**

- R17. Evidence Pack is the structured upstream of Brief: claims with quote, source_url, domain_trust, topic_key, plus run meta (keywords, mode, run_id, fingerprint).
- R18. Paths: `content/research/_evidence_{date}.json`; staging uses `content/research/_staging/{run_id}/`.
- R19. Brief assemble reads Evidence claims only for Top N / Exec Summary / depth sections after P2 cutover.
- R20. Daily and keyword paths share the Evidence schema; keyword may populate more/deeper claims without a second format.
- R21. Channel scripts keep Brief as required input; direct Evidence reads stay optional post-P2.

**Compatibility**

- R22. `{date}_brief.md` naming, validate-output research contract, and Notion archive expectations remain unless an explicit migration note is planned.
- R23. Wiki LLM ingest stays off the M1 blocking SLA path.

### Acceptance Examples

- AE1. When operator runs `/research RAG 평가` and daily Brief already has 7 insights, the new keyword insights merge in, Top N stays at the configured cap, validate passes, and LinkedIn/blog/newsletter regenerate from the new Brief.
- AE2. When operator runs `/research … --replace` with default config, live `{date}_brief.md` is unchanged and `/research-pending` shows a replace candidate until `/research-approve`.
- AE3. When `/research-approve` runs on a replace candidate, previous Brief is backed up, new Brief becomes SoT, M2/M2b run, and staging entry clears.
- AE4. When gather returns only spam/denied domains, Brief is not overwritten and Slack reports failure.
- AE5. When two insights share the same canonical URL during merge, the keyword-run insight wins and only one remains in Top N.
- AE6. After P2, a Brief insight maps to at least one Evidence claim with `source_url`, and research-trust eval can trace that URL.
- AE7. When operator runs publish `/pending`, output still reflects `.harness/publish-queue/` only (no research staging leakage). Publish `/approve` does not commit research staging; `/research-approve` does not mutate publish-queue.
- AE8. When operator runs keyword research with `--approve` (merge), live Brief unchanged until `/research-approve`, which then merges and runs R6b.
- AE9. When `require_approve_on_replace: false` and `--replace` is used, live Brief is replaced after validate (with backup) without staging.

### Success Criteria

- Trust: research-trust eval passes on spam/dup/diversity/handoff thresholds in Verification Contract; claim→URL traceability after P2.
- Quality: Brief emits validated `channel_hooks` (P1); after U4b, channel packages consume them instead of inventing empty hooks.
- Stability: no silent replace of live SoT; backup+rollback on failure; brief_gate blocks bad Brief from M2; publish HITL untouched.
- Ops: documented QC path keyword → merge|research-staging → research-approve → pipeline; audit runs exist per request.

### Scope Boundaries

**In scope**

- M1 gather/assemble/validate evolution; Slack/Telegram QC parity for research keyword modes; research staging/approve; Evidence Pack; research-trust eval; Brief handoff fields for M2.

**Deferred**

- Auto merge-vs-replace ML judgment.
- Evidence-native channel assemblers (Brief remains required).
- Changing newsletter ESP send or Notion IA.

**Out of scope**

- Lecture pipeline changes.
- Putting Wiki LLM ingest on the M1 SLA critical path.
- Full LLM regeneration of Brief as the default (optional enhance remains optional).
- Repurposing publish `/pending`/`/approve` for research.

### Dependencies / Assumptions

- Assumption: Slack/Telegram routing continues to exec `telegram-pipeline.sh` QC entrypoints; new research flags and research-pending/approve are parsed there.
- Assumption: Top N default remains 7 (`insight_limit`) unless config changes.
- Assumption: `require_approve_on_replace: true` is the shipped default; operators may set `false` in `config/research-brief.yaml` with documented risk.
- Dependency: Existing `brief_gate`, `validate-output.sh research`, `run-content-package.sh` / newsletter assemble stay the downstream spine.
- Dependency: `scripts/lib/publish_gate.py` remains publish-only.
- Grounding: M1 is `gather-web-research.py` → `assemble-research-brief.py` → validate; SoT `content/research/{date}_brief.md`.

### Outstanding Questions

**Resolved in planning (pinned defaults — override in Step 3 if needed)**

- Research staging commands: `/research-pending` + `/research-approve` (not publish `/pending`).
- Keyword path downstream: always re-run M2 + M2b after successful SoT commit (merge or research-approve).
- Telegram + Slack routing parity: same P1 change set.
- `require_approve_on_replace`: default `true` in `config/research-brief.yaml`; override allowed.

**Deferred to Implementation (non-blocking)**

- Exact title-token overlap threshold after first eval failures (start ≥ 0.55).
- PlayMCP P1 parity: **confirmed include** (3-A).

### Sources / Research

- `scripts/run-research-brief.sh`, `scripts/gather-web-research.py`, `scripts/assemble-research-brief.py`
- `config/research-brief.yaml`, `config/content-orchestration.yaml`, `config/slack-routing.yaml`, `config/telegram-routing.yaml`
- `scripts/lib/brief_gate.py`, `scripts/lib/brief_quality.py`, `scripts/lib/publish_gate.py`, `scripts/telegram-pipeline.sh`
- `docs/LLM-WIKI-INTEGRATION.md`, `docs/architecture/SYSTEM-LOGIC.md`

## Planning Contract

### Key Technical Decisions

- **KTD1 — Research staging namespace:** Use `content/research/_staging/{run_id}/` with `meta.json` + `brief.md` (+ optional `evidence.json` in P2). Commands: `qc research-pending` / `qc research-approve`. Register in routing yamls + `agent-commands` / intent list. Do not extend `publish_gate.py`.
- **KTD2 — Keyword gather:** Extend `gather-web-research.py` to accept extra queries from CLI/env (`HERMES_RESEARCH_KEYWORDS`); keep yaml queries for daily mode.
- **KTD3 — Merge algorithm:** Canonicalize URL (strip tracking params); exact URL match → keyword wins; else title token overlap ≥ 0.55 → keyword wins; fill remaining slots by trust then priority-query diversity.
- **KTD4 — channel_hooks:** Deterministic templates in `brief_quality.enrich_insight`; Brief markdown emit + validate in U1; structured M2 consume in U4b (`parse_brief_insights` / assemblers).
- **KTD5 — Backup:** Before overwrite copy `{date}_brief.md` → `{date}_brief.prev.md`; on validate failure restore prev and exit non-zero. Commit of Brief(+evidence) is all-or-nothing (temp write + rename).
- **KTD6 — P2 cutover:** Feature flag `HERMES_EVIDENCE=1` (default off until eval green); when on, assemble reads `_evidence_{date}.json` only.
- **KTD7 — Commander parity:** Same P1 change set updates `telegram-pipeline.sh`, `config/telegram-routing.yaml`, `config/slack-routing.yaml`, and `config/playmcp-routing.yaml` (PlayMCP in P1, confirmed 3-A).
- **KTD8 — Keyword argv gap:** Prefer `telegram-pipeline.sh auto "<full message>"` for keyword+flags; also accept env injection; support `qc research -- …` if Hermes forwards args.

### Sequencing

1. U1 trust/diversity/hooks emit+validate + research-trust-eval  
2. U2 keyword gather + merge SoT path + backup + replace **candidate artifacts** (no staging I/O API yet)  
3. U3 research staging I/O + research-pending/approve + routing + agent-commands (**hard dep after U2**)  
4. U4 commander keyword UX (auto/env) + R6b downstream re-run + eval  
4b. U4b M2 consume channel_hooks  
5. U5 Evidence Pack (P2) behind flag  
6. U6 Evidence cutover + brief_gate claim minimum  

### Assumptions for implementers

- `assess_trust` / `is_usable_search_result` already exist in `brief_quality.py` — extend rather than replace.
- `pipeline-integrity-eval.sh` must keep asserting deterministic assemble (no new LLM imports on hot path).

## Implementation Units

### U1. P1 trust, diversity, channel_hooks emit, research-trust-eval

- **Goal:** Strengthen Brief quality gates and add measurable trust eval without changing Slack keyword UX yet.
- **Requirements:** R1–R5
- **Files:** `scripts/lib/brief_quality.py`, `scripts/assemble-research-brief.py`, `scripts/validate-output.sh`, `config/research-brief.yaml`, `scripts/research-trust-eval.sh` (new), `.harness/feature_list.json`
- **Approach:** Tighten selection filters; add diversity cut; emit trust + channel_hooks in assemble; validate checks hooks presence and anti-paste rules; eval PASS/FAIL + `content/logs/` report.
- **Test scenarios:**
  - Wikipedia/shortener-only corpus → filter rejects unusable set.
  - Two near-duplicate titles → only one in Top N.
  - Assembled brief contains 신뢰도 and 채널 훅 for each insight.
  - `research-trust-eval.sh` exits 0 on golden fixture.
- **Verify:** `scripts/research-trust-eval.sh`; `scripts/validate-output.sh research` on fixture.

### U2. Keyword gather + merge SoT + backup (+ replace candidate blobs)

- **Goal:** Keyword-augmented research can merge to live SoT safely; replace produces **candidate artifacts** consumed by U3 staging API.
- **Requirements:** R6a, R7 (candidate/false-bypass branches), R12–R15, AE4 (gather failure keeps SoT), AE9
- **Files:** `scripts/gather-web-research.py`, `scripts/run-research-brief.sh`, `scripts/lib/research_merge.py` (new), `scripts/lib/research_run_audit.py` (new)
- **Approach:** Env/CLI keywords; merge writes SoT after validate; on `require_approve_on_replace: true`, replace only builds candidate brief text/files for U3 to stage (U2 does not own `_staging/` commits); on `false`, replace writes SoT with backup then caller may R6b; fingerprint skip; transactional temp+rename.
- **Test scenarios:**
  - Merge with shared URL keeps keyword insight.
  - Failed validate restores `.prev.md`; no partial Top N.
  - Mid-write failure leaves prior SoT intact.
  - Identical fingerprint announces skip/refresh.
  - `require_approve_on_replace: false` + replace → live SoT updated with backup.
- **Verify:** fixture/eval via `HERMES_RESEARCH_KEYWORDS`; merge unit tests.

### U3. Research staging commands (separate from publish HITL)

- **Goal:** Operators list and commit research staging without touching publish queue.
- **Requirements:** R8, R9, R11b, AE2, AE3, AE7, AE8, R13
- **Depends on:** U2 candidate artifacts
- **Files:** `scripts/lib/research_staging.py` (new), `scripts/telegram-pipeline.sh`, `config/slack-routing.yaml`, `config/telegram-routing.yaml`, `config/playmcp-routing.yaml`, agent-commands / intent registration files used by Hermes, `scripts/commander-phases-eval.sh`
- **Approach:** Staging dir per KTD1; `qc research-pending` / `qc research-approve`; wire U2 replace/approve candidates into staging writes; bidirectional isolation vs `publish_gate`.
- **Test scenarios:**
  - Replace candidate in research-pending only (not publish-pending).
  - `--approve` merge → pending → research-approve → SoT + R6b.
  - Publish approve does not clear research staging; research-approve does not touch publish-queue.
  - Commit mid-fail leaves staging+live consistent (no half apply).
- **Verify:** extended `commander-phases-eval.sh`.

### U4. Commander keyword UX + R6b downstream

- **Goal:** Keyword research end-to-end via auto/env (and argv if available), including NL mapping without colliding with publish 「승인」.
- **Requirements:** R6b, R10, R11, R11c, AE1, AE4 (Slack failure notice), F1–F3
- **Files:** `scripts/telegram-pipeline.sh`, routing yamls (TG/Slack/PlayMCP), channel_prompt text, `scripts/research-keyword-eval.sh` (new)
- **Approach:** Parse keywords/flags from `auto` message and env; default merge runs R6b; document commands; bare 「승인」 stays publish.
- **Test scenarios:**
  - `auto "리서치 RAG 평가"` merge updates brief + content package + newsletter.
  - `auto "… 교체"` / `--replace` leaves live brief, creates staging via U3.
  - Keyword-less research still daily M1.
  - Spam-only gather → SoT unchanged + failure message.
- **Verify:** `research-keyword-eval.sh`; `pipeline-integrity-eval.sh`; smoke as needed.

### U4b. M2 consumes channel_hooks

- **Goal:** Channel assemblers use Brief hooks instead of empty invented hooks.
- **Requirements:** R4 (consume half), Success Criteria quality
- **Files:** `scripts/lib/studio_upstream.py` (or `content_quality` parse path), channel assemble scripts that build hooks/CTAs
- **Approach:** Parse `채널 훅` into structured fields; prefer them in blog/LI/IG/newsletter builders with safe fallback.
- **Test scenarios:**
  - Fixture brief with hooks → linkedin/blog output contains hook text.
  - Missing hooks → prior fallback behavior, no crash.
- **Verify:** targeted eval or unit assert on assemble fixtures.

### U5. Evidence Pack behind flag (P2)

- **Goal:** Introduce `_evidence_{date}.json` writer/reader without changing default cron behavior until flag on.
- **Requirements:** R17, R18, R20, R21
- **Files:** `scripts/lib/evidence_pack.py` (new), `scripts/assemble-research-brief.py`, `scripts/run-research-brief.sh`, `config/research-brief.yaml` / orchestration env note
- **Approach:** Build claims from filtered search results; write evidence; when `HERMES_EVIDENCE=1`, assemble from claims; staging includes evidence.json.
- **Test scenarios:**
  - Flag off: no evidence file required; assemble unchanged path.
  - Flag on: evidence claim count ≥ min; brief insights trace to claim URLs.
- **Verify:** `research-trust-eval.sh` evidence mode; integrity eval.

### U6. Evidence cutover + brief_gate minimum claims

- **Goal:** Production-ready Evidence path and gate.
- **Requirements:** R16 (evidence clause), R19, AE6
- **Files:** `scripts/lib/brief_gate.py`, `config/content-orchestration.yaml`, docs snippet in `HARNESS.md` or architecture note (minimal)
- **Approach:** Gate checks min claims when evidence enabled; document default-on decision only after eval green (config flip is ops step, not silent).
- **Test scenarios:**
  - Missing evidence with flag on → gate blocks M2.
  - Valid evidence+brief → content package proceeds.
- **Verify:** `brief_gate` unit/eval; full `run-pipeline.sh` smoke with flag.

## Verification Contract

| Gate | Command / check |
|------|-----------------|
| Research trust | `scripts/research-trust-eval.sh [YYYY-MM-DD]` |
| Validate research | `scripts/validate-output.sh research` |
| Pipeline integrity | `scripts/pipeline-integrity-eval.sh` |
| Commander / staging | `scripts/commander-phases-eval.sh` (extended) |
| Keyword E2E | `scripts/research-keyword-eval.sh` (new) or smoke extension |
| Harness quick | `scripts/harness-eval.sh --quick` |
| Optional evidence | `HERMES_EVIDENCE=1 scripts/research-trust-eval.sh` |

**P1 numeric starting thresholds (tune in impl):** duplicate URL rate 0; title-near-dup pairs 0 in Top N; ≥90% insights with https URL; 100% insights with 채널 훅 four channels; trust field present on all.

## Definition of Done

- All U1–U4b green on Verification Contract; U5–U6 green before enabling Evidence by default.
- Product Contract R1–R23 addressed or explicitly deferred in Outstanding Questions.
- Publish HITL regression AE7 passes.
- `.harness/progress.md` updated when work ships; `scripts/validate-output.sh` on produced briefs.
- No credentials committed; wiki LLM still off M1 SLA path.
