#!/usr/bin/env python3
"""기존 SKILL.md → STABLE / LEARNED 분할. 1회만 실행.

기존 내용 전체를 STABLE로 옮기고, 빈 LEARNED 섹션을 추가한다.
내용을 재작성하거나 요약하지 않는다.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import playbook as P  # noqa: E402
from lib.token_budget import load_yaml_flat  # noqa: E402

HEADER = """<!--
이 파일은 두 섹션으로 나뉩니다.
  ## STABLE   — 브랜드 규칙·품질 게이트. 사람만 편집.
  ## LEARNED  — 경험적 학습. scripts/curate-playbook.sh 만 편집.
                append-only + tombstone. 삭제 금지.
-->
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skill", help="특정 스킬만")
    a = ap.parse_args()

    idx = load_yaml_flat(P.STUDIO / "config" / "skill-index.yaml")
    keys = [a.skill] if a.skill else list((idx.get("skills") or {}).keys())

    for key in keys:
        try:
            path = P.skill_path(key)
        except KeyError:
            print(f"⚠ {key}: skill-index에 없음 — 건너뜀")
            continue
        if not path.exists():
            print(f"⚠ {key}: {path} 없음 — 건너뜀")
            continue

        md = path.read_text(encoding="utf-8")
        if "## LEARNED" in md:
            print(f"= {key}: 이미 분할됨")
            continue

        stable = md.rstrip()
        if not stable.lstrip().startswith("<!--"):
            stable = HEADER + "\n" + stable
        if "## STABLE" not in stable:
            if stable.lstrip().startswith("---"):
                parts = stable.split("---", 2)
                if len(parts) >= 3:
                    stable = f"---{parts[1]}---\n\n## STABLE\n{parts[2].lstrip()}"
                else:
                    stable = HEADER + "\n## STABLE\n" + stable
            else:
                stable = stable.replace(HEADER, HEADER + "\n## STABLE\n", 1)
                if "## STABLE" not in stable:
                    stable = HEADER + "\n## STABLE\n" + md.rstrip()

        out = P.render(stable.rstrip() + "\n", [])
        if a.dry_run:
            print(f"[dry-run] {key} → {path}  ({len(md)} → {len(out)} bytes)")
            continue

        shutil.copy2(path, path.with_suffix(".md.pre-split"))
        path.write_text(out, encoding="utf-8")
        print(f"✓ {key}: 분할 완료 (백업 {path.name}.pre-split)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
