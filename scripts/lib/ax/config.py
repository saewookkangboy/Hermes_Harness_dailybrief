"""config/topic-research.yaml 로더 + 경로 헬퍼."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

WORKDIR = Path(os.environ.get("HERMES_WORKDIR") or Path(__file__).resolve().parents[3])
CONFIG_PATH = WORKDIR / "config" / "topic-research.yaml"


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def topics_root() -> Path:
    override = os.environ.get("HERMES_TOPICS_ROOT")
    if override:
        return Path(override)
    return WORKDIR / (load_config().get("output") or {}).get("root", "content/topics")


def topic_dir(slug: str) -> Path:
    return topics_root() / slug


def index_path() -> Path:
    return topics_root() / "_index.json"


def lens_feedback_path() -> Path:
    override = os.environ.get("HERMES_TOPIC_FEEDBACK")
    if override:
        return Path(override)
    rel = (load_config().get("output") or {}).get("lens_feedback", ".harness/topic-lens-feedback.json")
    return WORKDIR / rel


def artifact_path(slug: str, stamp: str, kind: str, ext: str = "md") -> Path:
    return topic_dir(slug) / f"{stamp}_{kind}_{slug}.{ext}"
