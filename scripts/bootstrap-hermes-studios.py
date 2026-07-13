#!/usr/bin/env python3
"""Bootstrap Hermes sibling studios (Tier 1–3) with Harness v1.2 scaffold."""
from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

CONTENT_STUDIO = Path.home() / "hermes-content-studio"
SCRIPTS = CONTENT_STUDIO / "scripts"
NOW = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")

STUDIOS: list[dict] = [
    {
        "id": "course",
        "dir": "hermes-course-studio",
        "name": "Hermes Course Factory",
        "tier": 1,
        "tagline": "강의 커리큘럼·실습·퀴즈 결정적 공장",
        "content_dirs": ["syllabus", "labs", "quizzes", "lectures", "packages"],
        "channels": {
            "syllabus": {"format": "markdown", "output": "content/syllabus"},
            "labs": {"format": "markdown", "output": "content/labs"},
            "quizzes": {"format": "markdown", "output": "content/quizzes"},
        },
        "stages": ["M1_syllabus", "M2_materials", "M2b_email", "M3_design", "M5_archive"],
        "pipeline": "run-course-pipeline.sh",
        "assemble": "assemble-course.py",
        "validate_types": ["syllabus", "lab", "quiz"],
        "primary_type": "syllabus",
        "sla": {"syllabus": 20, "full_pipeline": 90},
        "upstream": "content-studio brief SoT",
    },
    {
        "id": "intel",
        "dir": "hermes-intel-studio",
        "name": "Hermes Competitive Intel",
        "tier": 1,
        "tagline": "경쟁사·시장 변화 모니터링",
        "content_dirs": ["intel", "matrices", "entities", "packages"],
        "channels": {
            "intel": {"format": "markdown", "output": "content/intel"},
            "matrices": {"format": "markdown", "output": "content/matrices"},
        },
        "stages": ["M1_intel", "M2_matrix", "M4_metrics", "M5_archive"],
        "pipeline": "run-intel-pipeline.sh",
        "assemble": "assemble-intel.py",
        "validate_types": ["intel", "matrix"],
        "primary_type": "intel",
        "sla": {"intel": 25, "full_pipeline": 60},
        "upstream": "RSS/feeds + wiki entities",
    },
    {
        "id": "seo",
        "dir": "hermes-seo-studio",
        "name": "Hermes SEO/AEO Monitor",
        "tier": 1,
        "tagline": "blog SEO/AEO 감사·수정 권고",
        "content_dirs": ["seo", "patches", "packages"],
        "channels": {
            "seo": {"format": "markdown", "output": "content/seo"},
            "patches": {"format": "markdown", "output": "content/patches"},
        },
        "stages": ["M1_audit", "M2_patches", "M3_enhance", "M5_archive"],
        "pipeline": "run-seo-pipeline.sh",
        "assemble": "assemble-seo.py",
        "validate_types": ["seo", "patch"],
        "primary_type": "seo",
        "sla": {"seo": 20, "full_pipeline": 45},
        "upstream": "content-studio blog HTML",
    },
    {
        "id": "personal",
        "dir": "hermes-personal-studio",
        "name": "Hermes Personal Ops",
        "tier": 2,
        "tagline": "이메일·액션·개인 브리핑",
        "content_dirs": ["personal", "actions", "packages"],
        "channels": {
            "personal": {"format": "markdown", "output": "content/personal"},
            "actions": {"format": "markdown", "output": "content/actions"},
        },
        "stages": ["M1_inbox", "M2_actions", "M5_archive"],
        "pipeline": "run-personal-pipeline.sh",
        "assemble": "assemble-personal.py",
        "validate_types": ["inbox", "actions"],
        "primary_type": "inbox",
        "sla": {"inbox": 30, "full_pipeline": 60},
        "upstream": "mail-digest.py",
    },
    {
        "id": "wiki",
        "dir": "hermes-wiki-studio",
        "name": "Hermes Wiki Curator",
        "tier": 2,
        "tagline": "누적 wiki Seed·Ingest·Lint",
        "content_dirs": ["wiki-reports", "concepts", "packages"],
        "channels": {
            "wiki-report": {"format": "markdown", "output": "content/wiki-reports"},
        },
        "stages": ["M1w_seed", "M2_ingest", "M3_lint", "M5_archive"],
        "pipeline": "run-wiki-pipeline.sh",
        "assemble": "assemble-wiki.py",
        "validate_types": ["wiki-lint"],
        "primary_type": "wiki-lint",
        "sla": {"wiki": 15, "full_pipeline": 30},
        "upstream": "content-studio wiki + brief graph",
    },
    {
        "id": "dev",
        "dir": "hermes-dev-studio",
        "name": "Hermes Dev Handoff",
        "tier": 2,
        "tagline": "스펙→Cursor HANDOFF→구현 위임",
        "content_dirs": ["specs", "handoff", "logs", "packages"],
        "channels": {
            "spec": {"format": "markdown", "output": "content/specs"},
            "handoff": {"format": "markdown", "output": "content/handoff"},
        },
        "stages": ["M1_spec", "M2_handoff", "M3_cursor", "M4_ci", "M5_archive"],
        "pipeline": "run-dev-pipeline.sh",
        "assemble": "assemble-dev.py",
        "validate_types": ["spec", "handoff"],
        "primary_type": "spec",
        "sla": {"spec": 15, "full_pipeline": 120},
        "upstream": "user request + projects",
    },
    {
        "id": "delivery",
        "dir": "hermes-delivery-studio",
        "name": "Hermes Client Delivery",
        "tier": 3,
        "tagline": "B2B 제안·리포트·인수인계",
        "content_dirs": ["client", "proposals", "reports", "packages"],
        "channels": {
            "client": {"format": "markdown", "output": "content/client"},
            "proposal": {"format": "markdown", "output": "content/proposals"},
        },
        "stages": ["M1_client", "M2_proposal", "M5_archive"],
        "pipeline": "run-delivery-pipeline.sh",
        "assemble": "assemble-delivery.py",
        "validate_types": ["client", "proposal"],
        "primary_type": "client",
        "sla": {"client": 20, "full_pipeline": 60},
        "upstream": "meeting notes",
    },
    {
        "id": "social",
        "dir": "hermes-social-studio",
        "name": "Hermes Social Listener",
        "tier": 3,
        "tagline": "소셜 멘션·반응 모니터링",
        "content_dirs": ["social", "replies", "packages"],
        "channels": {
            "social": {"format": "markdown", "output": "content/social"},
            "replies": {"format": "markdown", "output": "content/replies"},
        },
        "stages": ["M1_pulse", "M2_replies", "M4_metrics", "M5_archive"],
        "pipeline": "run-social-pipeline.sh",
        "assemble": "assemble-social.py",
        "validate_types": ["social", "reply"],
        "primary_type": "social",
        "sla": {"social": 20, "full_pipeline": 45},
        "upstream": "LinkedIn + feeds",
    },
]


def write(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def agents_md(studio: dict, root: Path) -> str:
    return dedent(
        f"""\
        # {studio["name"]} — Agent Context

        Harness v1.2.0 · Tier {studio["tier"]} · {studio["tagline"]}

        ## 세션 시작 (필수)

        ```bash
        HERMES_WORKDIR={root} {root}/scripts/init.sh
        cat {root}/.harness/progress.md
        ```

        ## 워크스페이스

        - 산출물: `{root}/content/{{channel}}/`
        - 파일명: `YYYY-MM-DD_{{channel}}_{{slug}}.{{ext}}`
        - 언어: 한국어 (기술 용어 영문 병기)
        - upstream: {studio["upstream"]}

        ## 파이프라인

        ```bash
        HERMES_WORKDIR={root} {root}/scripts/{studio["pipeline"]}
        HERMES_WORKDIR={root} {root}/scripts/validate-output.sh {studio["primary_type"]} <file>
        HERMES_WORKDIR={root} {root}/scripts/harness-eval.sh --quick
        ```

        ## 공유 인프라

        - lib: `{CONTENT_STUDIO}/scripts/lib` (symlink)
        - Commander: `{CONTENT_STUDIO}/scripts/hermes-agent.sh`
        - Notion M5: `{CONTENT_STUDIO}/scripts/archive-to-notion.sh` (studio slug 전달)

        상세: `HARNESS.md` · 레지스트리: `{CONTENT_STUDIO}/config/studios-registry.yaml`
        """
    )


def harness_md(studio: dict, root: Path) -> str:
    return dedent(
        f"""\
        # {studio["name"]} — Harness Engineering

        > Parent: hermes-content-studio · CAR: Control–Agency–Runtime

        ## 5-Subsystem

        | 서브시스템 | 아티팩트 |
        |-----------|---------|
        | Instructions | `AGENTS.md`, `HARNESS.md` |
        | State | `.harness/feature_list.json`, `progress.md` |
        | Verification | `init.sh`, `validate-output.sh`, `harness-eval.sh` |
        | Scope | single_active_feature |
        | Lifecycle | init → work → session-handoff.md |

        ## 결정적 파이프라인

        ```bash
        HERMES_WORKDIR={root} {root}/scripts/{studio["pipeline"]}
        ```

        LLM polish는 `HERMES_ENHANCE=1` 일 때만.

        ## SLA (초)

        | 단계 | SLA |
        |------|-----|
        | primary | {studio["sla"].get(studio["primary_type"], studio["sla"].get("syllabus", 20))} |
        | full_pipeline | {studio["sla"]["full_pipeline"]} |

        설정: `config/harness.yaml`
        """
    )


def studio_yaml(studio: dict, root: Path) -> str:
    channels_yaml = "\n".join(
        f"  {k}:\n    enabled: true\n    format: {v['format']}\n    output: {v['output']}"
        for k, v in studio["channels"].items()
    )
    return dedent(
        f"""\
        studio:
          name: {studio["name"]}
          id: {studio["id"]}
          version: "1.0.0"
          tier: {studio["tier"]}
          harness: config/harness.yaml
          harness_doc: HARNESS.md
          workspace: {root}
          parent: {CONTENT_STUDIO}

        channels:
        {channels_yaml}

        integrations:
          parent_studio: {CONTENT_STUDIO}
          shared_lib: {CONTENT_STUDIO}/scripts/lib
          commander: {CONTENT_STUDIO}/scripts/hermes-agent.sh
          notion_archive: {CONTENT_STUDIO}/scripts/archive-to-notion.sh
        """
    )


def harness_yaml(studio: dict) -> str:
    sla = studio["sla"]
    primary_key = studio["primary_type"]
    primary_sla = sla.get(primary_key, sla.get("syllabus", sla.get("intel", 20)))
    return dedent(
        f"""\
        harness:
          version: "1.2.0"
          reference: awesome-harness-engineering
          parent: hermes-content-studio

        paths:
          harness_dir: .harness
          feature_list: .harness/feature_list.json
          progress: .harness/progress.md
          session_handoff: .harness/session-handoff.md
          traces: .harness/traces
          cost_ledger: .harness/cost-ledger.jsonl

        performance:
          deterministic_first: true
          sla_seconds:
            primary: {primary_sla}
            full_pipeline: {sla["full_pipeline"]}

        guardrails:
          deny_paths:
            - ~/.hermes/.env
            - ~/.ssh
            - "**/.env"
            - "**/credentials*"
          require_validation_before_done: true

        verification:
          post_stage:
            primary: scripts/validate-output.sh {studio["primary_type"]}
          post_pipeline:
            - scripts/harness-eval.sh --quick
        """
    )


def orchestration_yaml(studio: dict) -> str:
    stages_lines = []
    for i, stage in enumerate(studio["stages"], 1):
        stages_lines.append(
            f"  S{i}:\n    name: {stage}\n    script: scripts/{studio['pipeline']}\n    deterministic: true"
        )
    return dedent(
        f"""\
        version: "1.0.0"
        studio_id: {studio["id"]}
        stages:
        {chr(10).join(stages_lines)}

        pipelines:
          daily:
            script: scripts/{studio["pipeline"]}
            stages: {json.dumps(studio["stages"])}
        """
    )


def feature_list(studio: dict) -> dict:
    fid = studio["id"]
    features = [
        {
            "id": f"{fid}-001",
            "priority": 1,
            "area": studio["primary_type"],
            "title": f"M1 {studio['name']} (결정적)",
            "user_visible_behavior": f"{studio['pipeline']} 실행 시 primary 산출물 생성",
            "status": "in_progress",
            "verification": [
                f"scripts/init.sh",
                f"scripts/{studio['pipeline']}",
                f"scripts/validate-output.sh {studio['primary_type']}",
            ],
            "notes": f"assemble: scripts/{studio['assemble']}",
        },
        {
            "id": f"{fid}-002",
            "priority": 2,
            "area": "harness",
            "title": "Harness eval + validate",
            "user_visible_behavior": "harness-eval.sh --quick 통과",
            "status": "not_started",
            "verification": ["scripts/harness-eval.sh --quick"],
        },
        {
            "id": f"{fid}-003",
            "priority": 3,
            "area": "notion",
            "title": "Notion M5 archive (parent script)",
            "user_visible_behavior": "parent archive-to-notion.sh --studio {fid}",
            "status": "not_started",
            "verification": [f"{CONTENT_STUDIO}/scripts/archive-to-notion.sh"],
        },
    ]
    return {
        "project": studio["dir"],
        "last_updated": NOW,
        "rules": {
            "single_active_feature": True,
            "passing_requires_evidence": True,
            "deterministic_first": True,
        },
        "features": features,
    }


def progress_md(studio: dict, root: Path) -> str:
    return dedent(
        f"""\
        # Harness Progress — {studio["name"]}

        > 부트스트랩: {NOW}

        ## 현재 최우선

        - **{studio["id"]}-001** M1 결정적 파이프라인 scaffold 완료·검증

        ## 다음 단계

        1. `{studio["pipeline"]}` E2E 실행
        2. `validate-output.sh {studio["primary_type"]}` 통과
        3. Commander 라우팅 (`config/studios-registry.yaml`)

        ## 워크스페이스

        `{root}`
        """
    )


def init_sh(studio: dict, root: Path) -> str:
    dirs = " ".join(f'"{root}/content/{d}"' for d in studio["content_dirs"])
    return dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        DIR="$(cd "$(dirname "$0")" && pwd)"
        WORKDIR="${{HERMES_WORKDIR:-{root}}}"
        export HERMES_WORKDIR="$WORKDIR"
        PARENT="{CONTENT_STUDIO}"

        echo "=== {studio["name"]} init.sh ==="
        mkdir -p "$WORKDIR/.harness/traces" {dirs}
        chmod +x "$DIR"/*.sh 2>/dev/null || true

        if [[ -f "$PARENT/scripts/health-check.sh" ]]; then
          HERMES_WORKDIR="$PARENT" "$PARENT/scripts/health-check.sh" --quick 2>/dev/null || true
        fi

        if command -v jq >/dev/null 2>&1 && [[ -f "$WORKDIR/.harness/feature_list.json" ]]; then
          jq -r '.features[] | select(.status=="in_progress") | .id + ": " + .title' \\
            "$WORKDIR/.harness/feature_list.json" 2>/dev/null | head -1 || true
        fi
        echo "✅ init OK: $WORKDIR"
        """
    )


def pipeline_sh(studio: dict, root: Path) -> str:
    ptype = studio["primary_type"]
    return dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        DIR="$(cd "$(dirname "$0")" && pwd)"
        WORKDIR="${{HERMES_WORKDIR:-{root}}}"
        export HERMES_WORKDIR="$WORKDIR"
        DATE="${{1:-$(date +%F)}}"
        ASSEMBLE="$DIR/{studio["assemble"]}"
        SLUG="{studio["id"]}"
        PTYPE="{ptype}"
        SUBDIR="{list(studio["channels"].values())[0]["output"].split("/")[-1]}"
        PRIMARY="$WORKDIR/content/$SUBDIR/${{DATE}}_${{PTYPE}}_${{SLUG}}.md"

        echo "=== {studio["name"]} pipeline ($DATE) ==="
        python3 "$ASSEMBLE" --date "$DATE" --workdir "$WORKDIR"
        [[ -f "$PRIMARY" ]] || {{ echo "❌ primary missing: $PRIMARY"; exit 1; }}
        "$DIR/validate-output.sh" "$PTYPE" "$PRIMARY"
        echo "✅ pipeline OK"
        """
    )


def validate_sh(studio: dict) -> str:
    checks: dict[str, str] = {
        "syllabus": 'grep -q "## 학습 목표" "$FILE" && grep -q "## 모듈" "$FILE"',
        "intel": 'grep -q "## 경쟁사 Top" "$FILE" && grep -qE "https?://" "$FILE"',
        "seo": 'grep -q "## SEO 점수" "$FILE" && grep -q "## 권고" "$FILE"',
        "inbox": 'grep -q "## 액션 아이템" "$FILE" && grep -q "## 요약" "$FILE"',
        "wiki-lint": 'grep -q "## Lint 결과" "$FILE" && grep -q "## 개념" "$FILE"',
        "spec": 'grep -q "## 요구사항" "$FILE" && grep -q "## AC" "$FILE"',
        "client": 'grep -q "## 클라이언트" "$FILE" && grep -q "## Deliverable" "$FILE"',
        "social": 'grep -q "## 멘션 요약" "$FILE" && grep -q "## 회신 초안" "$FILE"',
        "lab": 'grep -q "## 실습" "$FILE"',
        "quiz": 'grep -q "## 퀴즈" "$FILE"',
        "matrix": 'grep -q "## 비교 매트릭스" "$FILE"',
        "patch": 'grep -q "## 패치" "$FILE"',
        "actions": 'grep -q "## 액션" "$FILE"',
        "handoff": 'grep -q "## HANDOFF" "$FILE"',
        "proposal": 'grep -q "## 제안" "$FILE"',
        "reply": 'grep -q "## 회신" "$FILE"',
    }
    cases = []
    for vtype in studio["validate_types"]:
        body = checks.get(vtype, 'grep -q "# " "$FILE"')
        cases.append(
            f'  {vtype})\n    {body}\n    pass "{vtype} OK: $FILE"\n    ;;'
        )
    return dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        WORKDIR="${{HERMES_WORKDIR:-{Path.home() / studio["dir"]}}}"
        TYPE="${{1:?Usage: validate-output.sh TYPE FILE}}"
        FILE="${{2:?Missing file}}"

        fail() {{ echo "❌ $1" >&2; exit 1; }}
        pass() {{ echo "✅ $1"; }}

        [[ -f "$FILE" ]] || fail "파일 없음: $FILE"
        SIZE=$(wc -c < "$FILE" | tr -d ' ')
        (( SIZE > 100 )) || fail "파일 너무 짧음 (${{SIZE}} bytes)"

        case "$TYPE" in
        {chr(10).join(cases)}
          *)
            fail "Unknown type: $TYPE"
            ;;
        esac
        """
    )


def harness_eval_sh(root: Path) -> str:
    return dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        WORKDIR="${{HERMES_WORKDIR:-{root}}}"
        QUICK=0
        for arg in "$@"; do [[ "$arg" == "--quick" ]] && QUICK=1; done

        echo "=== harness-eval ({root.name}) ==="
        [[ -f "$WORKDIR/HARNESS.md" ]] || {{ echo "❌ HARNESS.md"; exit 1; }}
        [[ -f "$WORKDIR/config/harness.yaml" ]] || {{ echo "❌ harness.yaml"; exit 1; }}
        [[ -f "$WORKDIR/.harness/feature_list.json" ]] || {{ echo "❌ feature_list"; exit 1; }}
        [[ -x "$WORKDIR/scripts/init.sh" ]] || {{ echo "❌ init.sh"; exit 1; }}
        echo "✅ struct OK"
        exit 0
        """
    )


def assemble_py(studio: dict) -> str:
    import sys

    sys.path.insert(0, str(SCRIPTS))
    from lib.studio_assemble_templates import render_assemble

    ptype = studio["primary_type"]
    out_subdir = list(studio["channels"].values())[0]["output"].split("/")[-1]
    return render_assemble(
        name=studio["name"],
        sid=studio["id"],
        ptype=ptype,
        out_subdir=out_subdir,
    )


def bootstrap_studio(studio: dict) -> Path:
    root = Path.home() / studio["dir"]
    scripts = root / "scripts"
    config = root / "config"

    write(root / "AGENTS.md", agents_md(studio, root))
    write(root / "HARNESS.md", harness_md(studio, root))
    write(config / "studio.yaml", studio_yaml(studio, root))
    write(config / "harness.yaml", harness_yaml(studio))
    write(config / "orchestration.yaml", orchestration_yaml(studio))
    write(root / "requirements.txt", "PyYAML>=6.0\n")

    harness = root / ".harness"
    write(harness / "feature_list.json", json.dumps(feature_list(studio), ensure_ascii=False, indent=2))
    write(harness / "progress.md", progress_md(studio, root))
    write(harness / "session-handoff.md", f"# Session Handoff\n\n> {studio['name']} — {NOW}\n")

    write(scripts / "init.sh", init_sh(studio, root), executable=True)
    write(scripts / studio["pipeline"], pipeline_sh(studio, root), executable=True)
    write(scripts / "validate-output.sh", validate_sh(studio), executable=True)
    write(scripts / "harness-eval.sh", harness_eval_sh(root), executable=True)
    # Tier 1 assemble scripts are hand-maintained (upstream-aware). Preserve if marked.
    assemble_path = scripts / studio["assemble"]
    preserve = assemble_path.exists() and "upstream" in assemble_path.read_text(encoding="utf-8")[:400]
    if not preserve:
        write(assemble_path, assemble_py(studio), executable=True)
    else:
        print(f"  ↷ preserve {assemble_path.name} (upstream)")

    lib_link = scripts / "lib"
    if not lib_link.exists():
        try:
            lib_link.symlink_to(CONTENT_STUDIO / "scripts" / "lib")
        except OSError:
            pass

    for d in studio["content_dirs"]:
        (root / "content" / d).mkdir(parents=True, exist_ok=True)

    return root


def main() -> None:
    created = []
    for studio in STUDIOS:
        root = bootstrap_studio(studio)
        created.append(str(root))
        print(f"✅ {studio['name']} → {root}")

    manifest = CONTENT_STUDIO / "content" / "logs" / f"{datetime.now().strftime('%Y-%m-%d')}_studios-bootstrap.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({"created": created, "at": NOW, "count": len(created)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n📦 Manifest: {manifest}")


if __name__ == "__main__":
    main()
