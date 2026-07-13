#!/usr/bin/env python3
"""Generate studio architecture MD exports for Notion (운영 리소스·의존성·Cursor 맵)."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKDIR = Path.home() / "hermes-content-studio"
LOGS = WORKDIR / "content" / "logs"
SKILLS = WORKDIR / "skills"
CONFIG = WORKDIR / "config"
LIB = SCRIPT_DIR / "lib"


def _today() -> str:
    return os.environ.get("STUDIO_DATE") or datetime.now().strftime("%Y-%m-%d")


def _read_yaml_keys(path: Path, section: str) -> dict:
    if not path.exists():
        return {}
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        block = data.get(section) or {}
        return dict(block) if isinstance(block, dict) else {}
    except Exception:
        return {}


def _list_lib_modules() -> list[str]:
    if not LIB.exists():
        return []
    return sorted(p.stem for p in LIB.glob("*.py") if p.name != "__init__.py")


def _list_skills() -> list[str]:
    if not SKILLS.exists():
        return []
    return sorted(
        str(p.relative_to(SKILLS)).replace("/SKILL.md", "").replace("\\SKILL.md", "")
        for p in SKILLS.rglob("SKILL.md")
    )


def _cron_lines() -> list[str]:
    try:
        out = subprocess.run(
            ["hermes", "cron", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        lines = [ln.strip() for ln in (out.stdout or "").splitlines() if ln.strip()]
        return lines[:20] if lines else ["(hermes cron list unavailable)"]
    except Exception:
        return ["(hermes cron list unavailable)"]


def _quality_blocking_table() -> str:
    sup = _read_yaml_keys(CONFIG / "content-quality.yaml", "supervised")
    budget = _read_yaml_keys(CONFIG / "content-quality.yaml", "budget")
    rows = [
        ("voice_blocking", sup.get("voice_blocking", False)),
        ("naturalness_blocking", sup.get("naturalness_blocking", False)),
        ("humanize_blocking", sup.get("humanize_blocking", False)),
        ("budget_blocking", sup.get("budget_blocking", False)),
    ]
    lines = ["| 키 | yaml |", "|----|------|"]
    for key, val in rows:
        lines.append(f"| `{key}` | `{val}` |")
    lines.append("")
    lines.append(f"- `daily_token_cap`: **{budget.get('daily_token_cap', '—')}**")
    path_caps = budget.get("path_daily_token_caps") or {}
    if path_caps:
        for path, cap in path_caps.items():
            lines.append(f"- `path_daily_token_caps.{path}`: **{cap}**")
    return "\n".join(lines)


def build_resources_spec(date: str) -> str:
    libs = _list_lib_modules()
    quality_libs = [
        "naturalness_audit",
        "humanize_polish",
        "humanize_korean",
        "hermes_cost",
        "loop_budget",
        "content_quality_config",
        "pipeline_supervisor",
        "voice_style_audit",
        "studio_upstream",
        "wiki_curator",
        "research_squad",
        "notion_oauth",
        "channel_artifacts",
        "m4_coach",
        "omm",
        "easytool_prompt",
    ]
    libs_extra = [m for m in quality_libs if m in libs]
    cron = _cron_lines()

    return f"""# Hermes Studio — 운영 리소스·기술 스펙 ({date})

> Harness v2.0 · Brief SoT Top 7 · Multi-Studio · JARVIS · Voice/Naturalness/Budget · Notion OAuth watch

## 0. 아키텍처 SoT

| 문서 | 역할 |
|------|------|
| `docs/architecture/SYSTEM-LOGIC.md` | **현행** v2.0 시스템 로직 + Mermaid |
| `docs/architecture/README.md` | 버전 타임라인 · archive 인덱스 |
| `docs/architecture/archive/v*.md` | 구현 단계별 동결 스냅샷 |

## 1. 런타임 개요

| 항목 | 값 |
|------|-----|
| 워크스페이스 | `~/hermes-content-studio` |
| Hermes Agent | `~/.hermes/` (Gateway · sessions · MCP) |
| Harness state | `.harness/progress.md`, `feature_list.json`, `cost-ledger.jsonl` |
| 날짜 SoT | `STUDIO_TZ=Asia/Seoul` · `scripts/lib/common.py` `studio_today()` |

## 2. 파이프라인 Stage (M1→M5 + Quality)

| Stage | 스크립트 | 산출 | 검증 |
|-------|----------|------|------|
| M1 | `run-research-brief.sh` | `content/research/{{date}}_brief.md` | `validate-output research` |
| GATE | `brief_gate.py` | Top 7 SoT | FAIL → M2 차단 |
| M2 | `run-content-package.sh` | blog · instagram · linkedin · packages | validate 채널별 |
| M2b | `run-newsletter.sh` | newsletter md/html | `newsletter-eval` |
| AUDIT | `quality_auditor.py` | audit report | WARN |
| VOICE | `voice_style_audit.py` | — | **blocking ON** |
| HUMANIZE | `run-humanize-polish.sh` | 결정적 polish (+ optional LLM) | WARN |
| NATURALNESS | `naturalness_audit.py` | — | **blocking ON** |
| M5 | `archive-to-notion.sh --force` | Notion 8건 + Permalink | FAIL → blocked |

**Supervised cron:** `cron-supervised-pipeline.sh` (평일 10:00) · **Staging:** `cron-staging-supervised.sh` (토 11:00)

## 3. 프로덕션 blocking · Budget (content-quality.yaml)

{_quality_blocking_table()}

- Budget cap 초과: `budget_blocking: false` → NATURALNESS **WARN** (FAIL 아님)
- LLM humanize: `HERMES_HUMANIZE_LLM=1` 수동 · Codex linkedin timeout **120s**
- Cost ledger: `.harness/cost-ledger.jsonl` · `parse_run_usage` per-channel **delta** (P15)

## 4. Commander 채널

| 채널 | 라우팅 | 상태 |
|------|--------|------|
| Telegram | `setup-telegram-routing.sh` · EasyTool | connected |
| Slack | `setup-slack-routing.sh` · intent pack | connected |
| PlayMCP (Kakao) | `setup-playmcp.sh` · `playmcp-routing-e2e.sh` | LIVE E2E 7/7 |
| Hermes CLI | `hermes-run.sh` · `hermes-agent.sh` | 로컬 |
| JARVIS | `JARVIS.md` · `lib/omm.py` | ON |

## 4b. Multi-Studio (8 siblings)

| Tier | Studio | upstream |
|------|--------|----------|
| 1 | course · intel · seo | brief · wiki · blog HTML |
| 2 | personal · wiki · dev | inbox · wiki · HANDOFF |
| 3 | delivery · social | calendar · linkedin |

`config/studios-registry.yaml` · `studios-all-upstream-eval.sh`

## 5. Config SoT

| 파일 | 역할 |
|------|------|
| `config/harness.yaml` | SLA · guardrails · eval baseline |
| `config/content-orchestration.yaml` | M1–M5 · skill_layers |
| `config/content-quality.yaml` | voice · naturalness · budget · humanize_llm |
| `config/notion-archive.yaml` | M5 categories · MCP tools |
| `config/telegram-routing.yaml` | Telegram quick_commands |
| `config/slack-routing.yaml` | Slack intent |
| `config/playmcp-routing.yaml` | PlayMCP Kakao commands |
| `config/studios-registry.yaml` | 8 sibling studios |
| `config/commander-easytool.yaml` | EasyTool compact prompt |
| `JARVIS.md` | 프로젝트 메모리 NOW/LAW/BAN |

## 6. Domain lib

품질·비용 스택: {", ".join(f"`{m}`" for m in libs_extra)}

전체: {", ".join(f"`{m}`" for m in libs[:40])}{" …" if len(libs) > 40 else ""}

## 7. Eval · 검증 기준선 ({date})

```bash
./scripts/harness-eval.sh --quick
./scripts/e2e-smoke-test.sh {date} --telegram
./scripts/pipeline-integrity-eval.sh
./scripts/studios-all-upstream-eval.sh {date}
./scripts/jarvis-memory-eval.sh
HERMES_CRON_SKIP_NOTION=1 ./scripts/cron-supervised-pipeline.sh
HERMES_PLAYMCP_E2E_LIVE=1 ./scripts/playmcp-routing-e2e.sh
HERMES_M5_E2E_LIVE=1 ./scripts/m5-notion-eval.sh {date}
```

## 8. Cron (hermes)

```
{chr(10).join(cron)}
```

## 9. Notion 아키텍처 페이지

| 페이지 | state key |
|--------|-----------|
| 운영 리소스·기술 스펙 | `resources` |
| 의존성 다이어그램 | `diagrams` |
| Cursor Agent 리소스 맵 | `cursor` |

재동기화: `./scripts/export-architecture-notion.sh` · state `content/.notion-architecture-state.json`

---
*Generated by `generate-architecture-md.py` · {datetime.now().isoformat(timespec="seconds")}*
"""


def build_dependency_diagrams(date: str) -> str:
    return f"""# Hermes Studio — 의존성 다이어그램 ({date})

> v2.0 · Multi-Studio · JARVIS · Content Loops · Quality P4–P15 · Notion OAuth  
> SoT: `docs/architecture/SYSTEM-LOGIC.md` · archive: `docs/architecture/archive/`

## 0. Version Timeline

```mermaid
timeline
  title Implementation Versions
  section v1.0 : 2026-06-07 M1 Top7
  section v1.1 : 2026-06-08 Telegram Notion
  section v1.2 : 2026-06-08 Newsletter hermes-agent
  section v1.3 : 2026-06-27 Content Loops Agents
  section v1.4 : 2026-07-01 Voice Budget PlayMCP
  section v2.0 : 2026-07-13 Multi-Studio JARVIS OAuth
```

## 1. Master Architecture (v2.0)

```mermaid
flowchart TB
  subgraph L0["Commander"]
    TG["Telegram"] & SL["Slack"] & PM["PlayMCP"] & CRON["cron"] & HA["hermes-agent"]
  end
  subgraph L1["Orchestration"]
    SP["supervised-pipeline"] & DT["daily-triage"] & TP["telegram-pipeline"]
  end
  subgraph L2["M1-M5"]
    M1["M1 brief"] --> GATE["brief_gate"] --> M2["M2 content"]
    M2 --> M2b["M2b newsletter"] --> M5["M5 Notion"]
  end
  subgraph Q["Quality"]
    AUD["audit"] --> V["VOICE"] --> H["humanize"] --> N["NATURALNESS"] --> B["budget"]
  end
  subgraph MS["Multi-Studio x8"]
    S1["Tier1"] & S2["Tier2"] & S3["Tier3"]
  end
  L0 --> L1 --> L2
  M2b --> Q --> M5
  M2 -.-> MS
```

## 2. Commander → Pipeline

```mermaid
flowchart TB
  subgraph COMMANDER["Layer 0 · Commander"]
    TG["Telegram"] & SL["Slack"] & PM["PlayMCP Kakao"] & CLI["hermes-agent.sh"]
  end
  subgraph ORCH["Layer 1 · Orchestration"]
    SP["cron-supervised-pipeline"]
    SS["cron-staging-supervised"]
    DT["cron-daily-content-triage"]
    TP["telegram-pipeline.sh"]
  end
  subgraph QUALITY["Quality Stack"]
    VS["voice_style_audit"]
    HP["humanize_polish"]
    NA["naturalness_audit"]
    LB["loop_budget / cost-ledger"]
  end
  COMMANDER --> ORCH
  SP --> M1["M1 brief"] --> M2["M2 content"] --> M2b["M2b newsletter"]
  M2b --> QUALITY --> M5["M5 Notion"]
  SS -.->|HERMES_SUPERVISED_STAGING=1| QUALITY
```

## 3. Brief SoT → Channels

```mermaid
flowchart LR
  SEARCH["_search_context_{{date}}.json"] --> BRIEF["{{date}}_brief.md"]
  BRIEF -->|parse_brief| INS["Insight Top 7"]
  INS --> BLOG["blog/*.html"]
  INS --> IG["instagram/*.md"]
  INS --> LI["linkedin/*.md"]
  INS --> NL["newsletter/*.md"]
  BLOG & IG & LI & NL --> PKG["packages/*"]
  PKG & BRIEF --> NOTION["Notion Daily Archive"]
```

## 4. Supervised Pipeline 단계

```mermaid
flowchart LR
  M1["M1 research"] --> G["brief_gate"]
  G --> M2["M2 content"]
  M2 --> M2b["M2b newsletter"]
  M2b --> A["quality_audit"]
  A --> V["VOICE blocking"]
  V --> H["HUMANIZE"]
  H --> N["NATURALNESS blocking"]
  N --> B{{"budget cap?"}}
  B -->|WARN if over| M5["M5 Notion"]
  B -->|FAIL only if budget_blocking| M5
```

## 5. Multi-Studio + JARVIS

```mermaid
flowchart TB
  PARENT["hermes-content-studio"]
  REG["studios-registry.yaml"]
  JAR["JARVIS.md + OMM"]
  PARENT --> REG
  PARENT -->|brief| T1["Tier1 course intel seo"]
  PARENT -->|wiki blog| T2["Tier2 personal wiki dev"]
  PARENT -->|linkedin| T3["Tier3 delivery social"]
  JAR -.-> PARENT
```

## 6. Notion OAuth Resilience

```mermaid
sequenceDiagram
  participant ARC as archive-to-notion
  participant OAUTH as notion_oauth
  participant MCP as Notion MCP
  ARC->>OAUTH: preflight
  alt valid
    OAUTH->>MCP: sync pages
  else expired
    OAUTH-->>ARC: archived ancestor
    Note over ARC: reauth-notion-mcp.sh
  end
```

## 7. LLM 경로 · Budget

```mermaid
flowchart TB
  subgraph DET["결정적 (cron ON)"]
    HK["humanize_korean.py"]
    HP2["humanize_polish deterministic"]
  end
  subgraph LLM["LLM (수동)"]
    HR["hermes-run humanize-korean"]
    EN["HERMES_ENHANCE polish"]
  end
  LEDGER[".harness/cost-ledger.jsonl"]
  CAP["loop_budget daily 600k / humanize 400k"]
  HR --> HC["hermes_cost parse_run_usage delta"]
  HC --> LEDGER --> CAP
  EN --> LEDGER
```

## 8. lib 의존성 (품질·M5·Studio)

| lib | 소비자 | 역할 |
|-----|--------|------|
| `content_quality_config.py` | supervisor · humanize · loop_budget | yaml SoT 로더 |
| `naturalness_audit.py` | validate-output · supervisor | 채널별 naturalness |
| `humanize_polish.py` | cron-supervised · run-humanize-polish | 결정적+LLM polish |
| `hermes_cost.py` | humanize_polish | tokens/USD · session delta |
| `loop_budget.py` | supervisor · humanize_polish | cap · kill switch |
| `pipeline_supervisor.py` | cron-supervised-pipeline | M1→M5 감독 |
| `notion_client.py` | archive-to-notion | MCP create/update |
| `notify_format.py` | telegram · slack | Permalink · progress |

| `studio_upstream.py` | bootstrap studios | brief/blog/wiki paths |
| `notion_oauth.py` | archive-to-notion | OAuth preflight |
| `channel_artifacts.py` | pipeline_supervisor | stale slug → _stale/ |

## 9. External

| 서비스 | 용도 |
|--------|------|
| Notion MCP | M5 archive · architecture pages |
| Telegram/Slack API | Commander notify |
| ddgs | M1 gather |
| Codex | LLM humanize (`HERMES_USE_CODEX=1`) |
| PlayMCP Gateway | Kakao commander (OTT) |

---
*Generated by `generate-architecture-md.py` · {datetime.now().isoformat(timespec="seconds")}*
"""


def build_cursor_resources(date: str) -> str:
    skills = _list_skills()
    handoff = WORKDIR / "content" / "drafts" / "cursor-handoff"
    handoff_count = len(list(handoff.glob("**/*"))) if handoff.exists() else 0
    cursor_bin = Path.home() / ".local" / "bin" / "cursor-agent"
    cursor_ok = cursor_bin.exists() and os.access(cursor_bin, os.X_OK)

    skill_lines = "\n".join(f"- `{s}`" for s in skills[:35])
    if len(skills) > 35:
        skill_lines += f"\n- … (+{len(skills) - 35} more)"

    return f"""# Hermes Studio — Cursor Agent 리소스 맵 ({date})

> Cursor CLI 핸드오프 · vibe-coding-cursor · Agent transcripts

## 1. Cursor Agent CLI

| 항목 | 경로/명령 |
|------|-----------|
| 바이너리 | `~/.local/bin/cursor-agent` ({'✅ installed' if cursor_ok else '⚠️ missing'}) |
| 설치 | `./scripts/install-cursor-cli.sh` |
| HANDOFF 실행 | `./scripts/run-cursor-handoff.sh --latest` |
| 백그라운드 | `HERMES_CURSOR_AUTO=1` · `/automate` → Codex HANDOFF |
| 핸드오프 패키지 | `content/drafts/cursor-handoff/` ({handoff_count} files) |

## 2. 워크플로

```mermaid
flowchart LR
  TG["Telegram /automate"] --> CODEX["Codex HANDOFF.md"]
  CODEX --> RCH["run-cursor-handoff.sh"]
  RCH --> CA["cursor-agent"]
  CA --> REPO["hermes-content-studio"]
  REPO --> VAL["validate-output.sh"]
```

## 3. 스킬 (Hermes + Cursor)

{skill_lines}

**코딩 핸드오프:** `skills/vibe-coding-cursor/SKILL.md` — 구현은 Cursor Agent에 위임

## 4. Harness Agent 규칙

| 파일 | 역할 |
|------|------|
| `AGENTS.md` | 워크스페이스 규칙 · 실행 커맨더 |
| `HARNESS.md` | CAR · Voice/Naturalness/Budget |
| `.cursor/rules/harness-engineering.mdc` | 세션 init · DoD |
| `.harness/progress.md` | P4–P14 통합 현황 SoT |
| `.harness/session-handoff.md` | 다음 세션 resume |

## 5. Cursor ↔ Hermes 통합 eval

```bash
./scripts/install-cursor-cli.sh
./scripts/run-cursor-handoff.sh --latest --dry-run
./scripts/health-check.sh                    # Cursor Agent CLI WARN/PASS
./scripts/harness-eval.sh --quick
```

## 6. MCP (Cursor IDE)

| 서버 | 용도 |
|------|------|
| notion-workspace | Notion search · pages |
| slack | 채널·메시지 |
| supabase / vercel | (플러그인) |
| browse | browser automation |

Notion archive 시 PlayMCP 노이즈 억제: `notion_client.setup_mcp()` notion-only (기본)

## 7. Agent transcripts

Cursor chat transcripts: `.cursor/projects/.../agent-transcripts/*.jsonl`

---
*Generated by `generate-architecture-md.py` · {datetime.now().isoformat(timespec="seconds")}*
"""


def main() -> int:
    date = _today()
    LOGS.mkdir(parents=True, exist_ok=True)
    outputs = {
        "resources": LOGS / f"{date}_studio-resources-spec.md",
        "diagrams": LOGS / f"{date}_studio-dependency-diagrams.md",
        "cursor": LOGS / f"{date}_cursor-agent-resources.md",
    }
    builders = {
        "resources": build_resources_spec,
        "diagrams": build_dependency_diagrams,
        "cursor": build_cursor_resources,
    }
    for key, path in outputs.items():
        path.write_text(builders[key](date), encoding="utf-8")
        print(f"  wrote {path}")
    meta = {
        "date": date,
        "files": {k: str(v) for k, v in outputs.items()},
        "generated_at": datetime.now().isoformat(),
    }
    meta_path = LOGS / f"{date}_studio-architecture-meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  meta → {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
