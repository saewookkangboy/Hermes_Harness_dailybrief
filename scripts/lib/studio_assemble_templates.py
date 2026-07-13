"""Assemble script templates for Hermes sibling studios."""
from __future__ import annotations

ASSEMBLE_BODIES: dict[str, str] = {
    "syllabus": '''#!/usr/bin/env python3
"""Deterministic assembler — {name}"""
from __future__ import annotations

import argparse
from datetime import date as date_cls
from pathlib import Path


def _primary_body(date: str, title: str) -> str:
    return f"""# {{title}}

## 학습 목표
- AI 마케팅 기초 개념 이해
- 실무 적용 체크리스트 작성
- 케이스 스터디 분석

## 모듈
### 1. 도입
### 2. 핵심 개념
### 3. 실습

## 출처
- https://example.com/course-ref
"""


def _lab_body(date: str, title: str) -> str:
    return f"# {{title}} 실습\\n\\n## 실습\\n- Step 1\\n- Step 2\\n"


def _quiz_body(date: str, title: str) -> str:
    return f"# {{title}} 퀴즈\\n\\n## 퀴즈\\n1. Q1?\\n2. Q2?\\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date_cls.today().isoformat())
    p.add_argument("--workdir", required=True)
    p.add_argument("--title", default="{name} 샘플")
    args = p.parse_args()
    root = Path(args.workdir).expanduser().resolve()
    date, slug, title = args.date, "{sid}", args.title
    out_path = root / "content" / "{out_subdir}" / f"{{date}}_{ptype}_{{slug}}.md"
    _write(out_path, _primary_body(date, title))
    _write(root / "content/labs" / f"{{date}}_lab_{{slug}}.md", _lab_body(date, title))
    _write(root / "content/quizzes" / f"{{date}}_quiz_{{slug}}.md", _quiz_body(date, title))
    print(f"Wrote {{out_path}}")


if __name__ == "__main__":
    main()
''',
    "intel": '''#!/usr/bin/env python3
"""Deterministic assembler — {name}"""
from __future__ import annotations

import argparse
from datetime import date as date_cls
from pathlib import Path


def _primary_body(date: str, title: str) -> str:
    return f"""# Competitive Intel — {{date}}

## 경쟁사 Top 5
1. Competitor A — pricing change
2. Competitor B — feature launch

## 변화 감지
- diff detected: 2 items

## 출처
- https://example.com/intel-feed
"""


def _matrix_body(date: str) -> str:
    return f"# 비교 매트릭스 — {{date}}\\n\\n## 비교 매트릭스\\n| 항목 | A | B |\\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date_cls.today().isoformat())
    p.add_argument("--workdir", required=True)
    p.add_argument("--title", default="{name} 샘플")
    args = p.parse_args()
    root = Path(args.workdir).expanduser().resolve()
    date, slug = args.date, "{sid}"
    out_path = root / "content" / "{out_subdir}" / f"{{date}}_{ptype}_{{slug}}.md"
    _write(out_path, _primary_body(date, args.title))
    _write(root / "content/matrices" / f"{{date}}_matrix_{{slug}}.md", _matrix_body(date))
    print(f"Wrote {{out_path}}")


if __name__ == "__main__":
    main()
''',
    "seo": '''#!/usr/bin/env python3
"""Deterministic assembler — {name}"""
from __future__ import annotations

import argparse
from datetime import date as date_cls
from pathlib import Path


def _primary_body(date: str, title: str) -> str:
    return f"""# SEO Audit — {{date}}

## SEO 점수
- Technical: 85
- Content: 78

## 권고
- meta description 개선
- FAQ schema 추가

## 출처
- https://example.com/blog
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date_cls.today().isoformat())
    p.add_argument("--workdir", required=True)
    args = p.parse_args()
    root = Path(args.workdir).expanduser().resolve()
    date, slug = args.date, "{sid}"
    out_path = root / "content" / "{out_subdir}" / f"{{date}}_{ptype}_{{slug}}.md"
    _write(out_path, _primary_body(date, "{name}"))
    print(f"Wrote {{out_path}}")


if __name__ == "__main__":
    main()
''',
    "inbox": '''#!/usr/bin/env python3
"""Deterministic assembler — {name}"""
from __future__ import annotations

import argparse
from datetime import date as date_cls
from pathlib import Path


def _primary_body(date: str, title: str) -> str:
    return f"""# Inbox Digest — {{date}}

## 요약
- 수신 12건, 액션 필요 3건

## 액션 아이템
- [ ] 회신: 프로젝트 A
- [ ] 일정 확인: 미팅 B
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date_cls.today().isoformat())
    p.add_argument("--workdir", required=True)
    args = p.parse_args()
    root = Path(args.workdir).expanduser().resolve()
    date, slug = args.date, "{sid}"
    out_path = root / "content" / "{out_subdir}" / f"{{date}}_{ptype}_{{slug}}.md"
    _write(out_path, _primary_body(date, "{name}"))
    print(f"Wrote {{out_path}}")


if __name__ == "__main__":
    main()
''',
    "wiki-lint": '''#!/usr/bin/env python3
"""Deterministic assembler — {name}"""
from __future__ import annotations

import argparse
from datetime import date as date_cls
from pathlib import Path


def _primary_body(date: str, title: str) -> str:
    return f"""# Wiki Lint — {{date}}

## Lint 결과
- stale URL: 0
- orphan concepts: 1

## 개념
- concepts: 12
- entities: 5
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date_cls.today().isoformat())
    p.add_argument("--workdir", required=True)
    args = p.parse_args()
    root = Path(args.workdir).expanduser().resolve()
    date, slug = args.date, "{sid}"
    out_path = root / "content" / "{out_subdir}" / f"{{date}}_{ptype}_{{slug}}.md"
    _write(out_path, _primary_body(date, "{name}"))
    print(f"Wrote {{out_path}}")


if __name__ == "__main__":
    main()
''',
    "spec": '''#!/usr/bin/env python3
"""Deterministic assembler — {name}"""
from __future__ import annotations

import argparse
from datetime import date as date_cls
from pathlib import Path


def _primary_body(date: str, title: str) -> str:
    return f"""# Spec — {{title}}

## 요구사항
- FR-1: 기능 A
- FR-2: 기능 B

## AC
- [ ] validate 통과
- [ ] CI green
"""


def _handoff_body(date: str, title: str) -> str:
    return f"# HANDOFF — {{title}}\\n\\n## HANDOFF\\n- Cursor Agent 실행\\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date_cls.today().isoformat())
    p.add_argument("--workdir", required=True)
    p.add_argument("--title", default="{name} 샘플")
    args = p.parse_args()
    root = Path(args.workdir).expanduser().resolve()
    date, slug, title = args.date, "{sid}", args.title
    out_path = root / "content" / "{out_subdir}" / f"{{date}}_{ptype}_{{slug}}.md"
    _write(out_path, _primary_body(date, title))
    _write(root / "content/handoff" / f"{{date}}_handoff_{{slug}}.md", _handoff_body(date, title))
    print(f"Wrote {{out_path}}")


if __name__ == "__main__":
    main()
''',
    "client": '''#!/usr/bin/env python3
"""Deterministic assembler — {name}"""
from __future__ import annotations

import argparse
from datetime import date as date_cls
from pathlib import Path


def _primary_body(date: str, title: str) -> str:
    return f"""# Client Brief — {{date}}

## 클라이언트
- Industry: B2B SaaS

## Deliverable
- 주간 리포트
- 제안서 v1
"""


def _proposal_body(date: str, title: str) -> str:
    return f"# Proposal — {{date}}\\n\\n## 제안\\n- Scope\\n- Timeline\\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date_cls.today().isoformat())
    p.add_argument("--workdir", required=True)
    p.add_argument("--title", default="{name} 샘플")
    args = p.parse_args()
    root = Path(args.workdir).expanduser().resolve()
    date, slug, title = args.date, "{sid}", args.title
    out_path = root / "content" / "{out_subdir}" / f"{{date}}_{ptype}_{{slug}}.md"
    _write(out_path, _primary_body(date, title))
    _write(root / "content/proposals" / f"{{date}}_proposal_{{slug}}.md", _proposal_body(date, title))
    print(f"Wrote {{out_path}}")


if __name__ == "__main__":
    main()
''',
    "social": '''#!/usr/bin/env python3
"""Deterministic assembler — {name}"""
from __future__ import annotations

import argparse
from datetime import date as date_cls
from pathlib import Path


def _primary_body(date: str, title: str) -> str:
    return f"""# Social Pulse — {{date}}

## 멘션 요약
- LinkedIn: 5 mentions
- Comments: 12

## 회신 초안
- Draft 1: thank you reply
"""


def _reply_body(date: str) -> str:
    return f"# Reply drafts — {{date}}\\n\\n## 회신\\n- Template A\\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date_cls.today().isoformat())
    p.add_argument("--workdir", required=True)
    args = p.parse_args()
    root = Path(args.workdir).expanduser().resolve()
    date, slug = args.date, "{sid}"
    out_path = root / "content" / "{out_subdir}" / f"{{date}}_{ptype}_{{slug}}.md"
    _write(out_path, _primary_body(date, "{name}"))
    _write(root / "content/replies" / f"{{date}}_reply_{{slug}}.md", _reply_body(date))
    print(f"Wrote {{out_path}}")


if __name__ == "__main__":
    main()
''',
}


def render_assemble(
    *,
    name: str,
    sid: str,
    ptype: str,
    out_subdir: str,
) -> str:
    tpl = ASSEMBLE_BODIES.get(ptype, ASSEMBLE_BODIES["syllabus"])
    return tpl.format(name=name, sid=sid, ptype=ptype, out_subdir=out_subdir)
