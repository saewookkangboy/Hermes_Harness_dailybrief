#!/usr/bin/env python3
"""Regenerate assemble-*.py for all sibling studios."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.studio_assemble_templates import render_assemble

STUDIOS = [
    ("course", "Hermes Course Factory", "syllabus", "syllabus", "assemble-course.py"),
    ("intel", "Hermes Competitive Intel", "intel", "intel", "assemble-intel.py"),
    ("seo", "Hermes SEO/AEO Monitor", "seo", "seo", "assemble-seo.py"),
    ("personal", "Hermes Personal Ops", "inbox", "personal", "assemble-personal.py"),
    ("wiki", "Hermes Wiki Curator", "wiki-lint", "wiki-reports", "assemble-wiki.py"),
    ("dev", "Hermes Dev Handoff", "spec", "specs", "assemble-dev.py"),
    ("delivery", "Hermes Client Delivery", "client", "client", "assemble-delivery.py"),
    ("social", "Hermes Social Listener", "social", "social", "assemble-social.py"),
]

for sid, name, ptype, out_subdir, filename in STUDIOS:
    root = Path.home() / f"hermes-{sid}-studio"
    path = root / "scripts" / filename
    path.write_text(
        render_assemble(name=name, sid=sid, ptype=ptype, out_subdir=out_subdir),
        encoding="utf-8",
    )
    print(f"✅ {path}")
