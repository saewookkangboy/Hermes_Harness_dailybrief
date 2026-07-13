# Hermes Content Studio — System Logic (v2.0)

> **현행** · 2026-07-13 · Parent Commander + 8 sibling studios + JARVIS memory  
> 이전 버전: [archive/](./archive/)

---

## 0. 한 줄 정의

**Hermes Content Studio**는 Brief SoT(`{date}_brief.md`)를 중심으로 M1→M5 결정적 파이프라인을 돌리고, Telegram·Slack·PlayMCP·cron이 **Commander**로 감독·알림·HITL을 담당하며, 8개 sibling studio가 upstream 산출물을 소비하는 **자체호스팅 콘텐츠 공장**이다.

---

## 1. 버전 타임라인

```mermaid
timeline
  title Implementation Versions
  section v1.0 Baseline
    2026-06-07 : M1 Top 7 결정적 brief
               : gather → assemble → validate
  section v1.1 Commander
    2026-06-08 : Telegram/Slack slash
               : Notion M5 archive
               : Brief SoT gate
  section v1.2 Newsletter
    2026-06-08 : M2b newsletter P0-P6
               : hermes-agent CLI
  section v1.3 Loops + Agents
    2026-06-27 : daily-triage L1
               : supervised-pipeline L2
               : Agents A-D Wiki Squad
  section v1.4 Quality
    2026-07-01 : voice/naturalness blocking
               : loop_budget cost-ledger
               : PlayMCP E2E
  section v2.0 Multi-Studio
    2026-07-12 : 8 studio bootstrap
               : JARVIS + EasyTool
    2026-07-13 : Notion OAuth watch
               : channel_artifacts stale
               : Tier 1-3 upstream eval
```

---

## 2. 마스터 아키텍처 (v2.0)

```mermaid
flowchart TB
  subgraph L0["Layer 0 · Commander"]
    TG["Telegram"]
    SL["Slack"]
    PM["PlayMCP Kakao"]
    CRON["hermes cron"]
    CLI["hermes-agent.sh"]
  end

  subgraph L1["Layer 1 · Orchestration"]
    TP["telegram-pipeline.sh"]
    SP["cron-supervised-pipeline"]
    DT["cron-daily-content-triage"]
    ST["cron-staging-supervised"]
    PSUP["pipeline_supervisor.py"]
  end

  subgraph L2["Layer 2 · M1-M5 Pipeline"]
    M1["M1 run-research-brief"]
    GATE["brief_gate Top 7"]
    M2["M2 run-content-package"]
    M2b["M2b run-newsletter"]
    M5["M5 archive-to-notion"]
  end

  subgraph Q["Quality Stack"]
    AUD["quality_auditor"]
    VOICE["voice_style_audit blocking"]
    HUM["humanize_polish"]
    NAT["naturalness_audit blocking"]
    BUD["loop_budget WARN"]
  end

  subgraph MEM["Memory · SoT"]
    BRIEF["{date}_brief.md"]
    WIKI["content/wiki/"]
    JAR["JARVIS.md + OMM"]
    NOTION[("Notion Daily Archive")]
  end

  subgraph MS["Multi-Studio Tier 1-3"]
    S1["course · intel · seo"]
    S2["personal · wiki · dev"]
    S3["delivery · social"]
  end

  L0 --> L1
  TP & SP --> PSUP
  PSUP --> M1 --> GATE --> M2 --> M2b
  M2b --> AUD --> VOICE --> HUM --> NAT --> BUD --> M5
  M1 --> BRIEF
  M2 --> BRIEF
  M5 --> NOTION
  BRIEF -.-> WIKI
  CLI --> JAR
  BRIEF -.-> MS
  M2 -.->|blog HTML| S1
  NOTION -.->|OAuth watch| M5
```

---

## 3. 실행 모드 (결정적 vs 대화형)

| 축 | 결정적 | 대화형 |
|----|--------|--------|
| 목적 | 일일 콘텐츠·Notion 재현 | 심화 리서치·개인화·코딩 핸드오프 |
| 진입 | `run-pipeline.sh`, `/pipeline`, cron | `hermes-agent.sh`, `/ask`, `/deep`, `/automate` |
| 도구 | assemble-*.py, `-t hermes-cli` | skills + MCP + Codex(선택) |
| SLA | M1 ~20s · full ~70s | 가변 |
| 검증 | `validate-output.sh` 필수 | harness 가드레일 |

**통합 원칙:** 대화형이 트리거해도 M1→M5는 **동일 스크립트·동일 lib**을 탄다.

---

## 4. M1 → M5 + Quality Gate Chain

```mermaid
flowchart LR
  subgraph M1["M1 Research"]
    G1["gather-web-research.py"]
    A1["assemble-research-brief.py"]
    G1 --> A1 --> B["{date}_brief.md"]
  end

  subgraph GATE["Gate"]
    BG["brief_gate.py"]
    B --> BG
  end

  subgraph M2["M2 Content"]
    CP["assemble-content-package.py"]
    BG -->|PASS| CP
    CP --> CH["blog · instagram · linkedin"]
    CP --> PKG["packages/*-context.md"]
  end

  subgraph M2b["M2b Newsletter"]
    NL["assemble-newsletter.py"]
    CP --> NL --> NLO["newsletter md/html"]
  end

  subgraph QA["Quality P4-P14"]
    QA1["quality_auditor"]
    QA2["voice_style_audit"]
    QA3["humanize_polish"]
    QA4["naturalness_audit"]
    QA5["loop_budget"]
    NLO --> QA1 --> QA2 --> QA3 --> QA4 --> QA5
  end

  subgraph M5["M5 Archive"]
    ARC["archive-to-notion.py"]
    QA5 --> ARC --> N["Notion 8p + Permalink"]
  end
```

| Stage | 스크립트 | 산출 SoT | 차단 |
|-------|----------|----------|------|
| M1 | `run-research-brief.sh` | `_search_context_{date}.json`, `{date}_brief.md` | validate FAIL |
| GATE | `brief_gate.py` | Top 7 freshness | FAIL → M2 skip |
| M2 | `run-content-package.sh` | blog/instagram/linkedin, packages | validate FAIL |
| M2b | `run-newsletter.sh` | newsletter md/html/scores | newsletter-eval FAIL |
| AUDIT | `quality_auditor.py` | audit report | WARN only |
| VOICE | `voice_style_audit.py` | — | **blocking ON** |
| HUMANIZE | `run-humanize-polish.sh` | polished channels | WARN |
| NATURALNESS | `naturalness_audit.py` | — | **blocking ON** |
| BUDGET | `loop_budget.py` | cost-ledger | WARN (cap 초과) |
| M5 | `archive-to-notion.sh --force` | Notion pages | OAuth/MCP FAIL |

설정 SoT: `config/content-orchestration.yaml` · `config/content-quality.yaml`

---

## 5. Commander · hermes-agent Intent Map

```mermaid
flowchart TB
  subgraph Slash["Slash / Quick Commands"]
    P["/pipeline"]
    R["/research /content /newsletter"]
    I["/morning /catch-up /ask /deep"]
    H["/publish /pending /approve"]
    O["/sync /notion-status"]
  end

  subgraph Agent["hermes-agent.sh"]
    MOR["morning"]
    RT["route / ask"]
    SQ["squad Research Squad"]
    WK["wiki lint|seed|ingest"]
    CO["coach M4"]
    SC["schedule HITL"]
    PB["publish + approve"]
  end

  subgraph Pipe["Deterministic"]
    TPS["telegram-pipeline.sh qc|auto"]
    SUP["run-supervised-pipeline.sh"]
  end

  Slash --> TPS
  TPS --> Pipe
  I --> Agent
  Agent --> Pipe
  H --> PB
```

| Intent | 진입 | 실행 |
|--------|------|------|
| pipeline | `/pipeline` | M1+M2+M2b+M5 (~70s) |
| morning | `/morning`, cron 09:00 | proactive + brief top3 |
| ask | `/ask`, `hermes-agent ask` | memory_router + brief graph |
| deep | `/deep` | research_squad Scout→Archivist |
| publish | `/publish` | HITL gate → approve |
| wiki | `hermes-agent wiki` | wiki_curator |
| coach | `/coach` | m4_coach CTOR feedback |

라우팅 SoT: `config/telegram-routing.yaml` · `config/slack-routing.yaml` · `config/agent-commands.yaml` · `config/commander-easytool.yaml`

---

## 6. Content Loops (L1 / L2 / L3)

```mermaid
flowchart TB
  subgraph L1["L1 Report Only"]
    MB["cron-morning-brief 09:00"]
    DT["cron-daily-triage 09:30"]
    HA["cron-health-alert 10/18"]
    CW["cron-competitive-watch 월"]
    NO["cron-notion-oauth-watch 2h"]
  end

  subgraph L2["L2 Assisted Factory"]
    SP["cron-supervised-pipeline 10:00"]
    SS["cron-staging-supervised 토"]
    SCH["cron-publish-schedule */15"]
  end

  subgraph L3["L3 Human Gate"]
    HITL["publish_gate approve"]
  end

  DT --> SP
  SP --> HITL
  SCH --> HITL
```

상세: [content-loops.md](../content-loops.md)

---

## 7. Multi-Studio (8 siblings)

```mermaid
flowchart TB
  PARENT["hermes-content-studio<br/>Parent Commander"]
  REG["studios-registry.yaml"]
  UP["studio_upstream.py"]

  PARENT --> REG
  PARENT -->|brief SoT| T1
  PARENT -->|blog HTML| T1
  PARENT -->|wiki concepts| T2
  PARENT -->|linkedin| T3

  subgraph T1["Tier 1"]
    C1["course-studio"]
    C2["intel-studio"]
    C3["seo-studio"]
  end

  subgraph T2["Tier 2"]
    C4["personal-studio"]
    C5["wiki-studio"]
    C6["dev-studio"]
  end

  subgraph T3["Tier 3"]
    C7["delivery-studio"]
    C8["social-studio"]
  end

  REG --> T1 & T2 & T3
  UP --> T1 & T2 & T3
```

```bash
~/hermes-content-studio/scripts/bootstrap-hermes-studios.sh
~/hermes-content-studio/scripts/studios-all-upstream-eval.sh {date}
```

상세: [MULTI-STUDIO-ARCHITECTURE.md](../MULTI-STUDIO-ARCHITECTURE.md)

---

## 8. Notion M5 · OAuth Resilience

```mermaid
sequenceDiagram
  participant CRON as cron-supervised
  participant ARC as archive-to-notion
  participant OAUTH as notion_oauth.py
  participant MCP as Notion MCP
  participant TG as Telegram

  CRON->>ARC: M5 --force
  ARC->>OAUTH: preflight token
  alt token valid
    OAUTH->>MCP: tools registered
    MCP->>ARC: create/update pages
    ARC->>TG: Permalink --notify-final
  else token expired
    OAUTH-->>ARC: is_archived_notion_error
    Note over ARC: --reset-notion-state
    ARC-->>TG: reauth-notion-mcp.sh 안내
  end
```

| 복구 | 스크립트 |
|------|----------|
| OAuth 재인증 | `reauth-notion-mcp.sh` |
| 날짜 백필 | `backfill-notion-archive.sh` |
| 지속 감시 | `cron-notion-oauth-watch.sh` |
| 중복 slug | `channel_artifacts.py` → `content/_stale/` |

---

## 9. JARVIS · EasyTool · OMM

| 컴포넌트 | 경로 | 역할 |
|----------|------|------|
| JARVIS | `JARVIS.md` | NOW/LAW/BAN/MAP 프로젝트 메모리 |
| OMM | `lib/omm.py` · `.harness/omm.jsonl` | 실수 → 방어선 기록 |
| EasyTool | `lib/easytool_prompt.py` | compact commander prompt (~893 chars) |
| JARVIS CODE | `jarvis-code-pilot.sh` | macOS 로컬 recall 파일럿 |

---

## 10. 리소스 계층 (Layer 0–7)

| Layer | 구성 | 대표 아티팩트 |
|-------|------|---------------|
| 0 | Commander | telegram/slack/playmcp routing yaml |
| 1 | Orchestration | supervised · triage · hermes-agent |
| 2 | Stage scripts | run-*-brief/package/newsletter/pipeline |
| 3 | Assemble | gather-*.py · assemble-*.py |
| 4 | Domain lib | brief_* · content_quality · notion_* · pipeline_supervisor |
| 5 | Config | config/*.yaml |
| 6 | Harness state | .harness/* · content/.notion-*-state.json |
| 7 | External | Notion MCP · ddgs · Codex · Telegram API |

---

## 11. 검증 기준선 (v2.0)

```bash
./scripts/init.sh --skip-health
./scripts/harness-eval.sh --quick                    # struct + wiring
./scripts/e2e-smoke-test.sh $(date +%Y-%m-%d) --telegram   # 23/23
./scripts/pipeline-integrity-eval.sh                 # 17/17
./scripts/studios-all-upstream-eval.sh $(date +%Y-%m-%d)
./scripts/jarvis-memory-eval.sh
HERMES_PLAYMCP_E2E_LIVE=1 ./scripts/playmcp-routing-e2e.sh
HERMES_M5_E2E_LIVE=1 ./scripts/m5-notion-eval.sh $(date +%Y-%m-%d)
./scripts/generate-architecture-md.py
```

---

## 12. 변경 시 워크플로

1. 구현 완료 → `validate-output.sh` · 해당 eval PASS
2. `.harness/progress.md` 갱신
3. **major 변경 시:** `SYSTEM-LOGIC.md` → `archive/v{X.Y}-*.md` 복사 후 현행 수정
4. `generate-architecture-md.py` 실행 → Notion `export-architecture-notion.sh`

---
*System Logic v2.0 · archived versions in [archive/](./archive/) · generated diagrams also in `content/logs/{date}_studio-dependency-diagrams.md`*
