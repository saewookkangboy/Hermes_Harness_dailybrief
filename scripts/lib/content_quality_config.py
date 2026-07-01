"""콘텐츠 품질 통합 설정 로더 — config/content-quality.yaml SoT."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

WORKDIR = Path.home() / "hermes-content-studio"
CONFIG_PATH = WORKDIR / "config" / "content-quality.yaml"
LEGACY_VOICE = WORKDIR / "config" / "voice-style.yaml"
LEGACY_LONGFORM = WORKDIR / "config" / "longform-content.yaml"
LEGACY_COACH = WORKDIR / "config" / "m4-coach.yaml"


@lru_cache(maxsize=1)
def load_content_quality_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def voice_config() -> dict[str, Any]:
    cfg = load_content_quality_config()
    if cfg.get("voice"):
        return dict(cfg["voice"])
    if LEGACY_VOICE.exists():
        with LEGACY_VOICE.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def longform_config() -> dict[str, Any]:
    cfg = load_content_quality_config()
    if cfg.get("longform"):
        lf = dict(cfg["longform"])
        if "sentence_policy" in cfg:
            lf["sentence_policy"] = cfg["sentence_policy"]
        return lf
    if LEGACY_LONGFORM.exists():
        with LEGACY_LONGFORM.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def coach_config() -> dict[str, Any]:
    cfg = load_content_quality_config()
    if cfg.get("coach"):
        ch = dict(cfg["coach"])
        ch.setdefault("channels", ch.get("channels") or {})
        ch.setdefault("trait_propagation", ch.get("trait_propagation") or {})
        ch.setdefault("coaching", {
            "min_ctor_records": ch.pop("min_ctor_records", 2),
            "recommend_top_n": ch.pop("recommend_top_n", 5),
        })
        return ch
    if LEGACY_COACH.exists():
        with LEGACY_COACH.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def sentence_policy() -> dict[str, Any]:
    cfg = load_content_quality_config()
    return dict(cfg.get("sentence_policy") or {})


def change_rate_max() -> float:
    voice = voice_config()
    for p in voice.get("principles") or []:
        if isinstance(p, str) and "change_rate_max" in p:
            try:
                return float(p.split(":")[-1].strip())
            except ValueError:
                pass
    cfg = load_content_quality_config()
    ev = cfg.get("eval") or {}
    return float(ev.get("change_rate_max") or voice.get("change_rate_max") or 0.30)


def ai_tell_patterns() -> tuple[str, ...]:
    voice = voice_config()
    tells = voice.get("ai_tells")
    if tells:
        return tuple(str(t) for t in tells)
    return (
        "결론적으로",
        "요약하면",
        "정리하면",
        "혁신적인",
        "획기적인",
        "시사하는 바",
        "본질적으로",
        "핵심적으로",
    )


def naturalness_config() -> dict[str, Any]:
    cfg = load_content_quality_config()
    return dict(cfg.get("naturalness") or {})


def budget_config() -> dict[str, Any]:
    cfg = load_content_quality_config()
    return dict(cfg.get("budget") or {})


def naturalness_min_score(channel: str) -> int:
    nc = naturalness_config()
    ch = (nc.get("channels") or {}).get(channel) or {}
    return int(ch.get("min_score") or nc.get("target_score") or 60)


def supervised_cron_defaults() -> dict[str, bool]:
    """평일 cron-supervised-pipeline 기본 env (HERMES_CRON_* override 가능)."""
    cfg = load_content_quality_config()
    defaults = (cfg.get("supervised") or {}).get("cron_defaults") or {}
    return {
        "humanize": bool(defaults.get("humanize", False)),
        "skip_newsletter": bool(defaults.get("skip_newsletter", True)),
        "skip_notion": bool(defaults.get("skip_notion", False)),
        "skip_audit": bool(defaults.get("skip_audit", False)),
    }


def supervised_config() -> dict[str, Any]:
    return dict(load_content_quality_config().get("supervised") or {})


def supervised_stage_blocking(stage: str) -> bool:
    """VOICE | HUMANIZE | NATURALNESS | BUDGET — yaml supervised.*_blocking."""
    key = f"{stage.lower()}_blocking"
    env_key = f"HERMES_{stage.upper()}_BLOCKING"
    if os.environ.get(env_key, "") == "1":
        return True
    cfg = supervised_config()
    if os.environ.get("HERMES_SUPERVISED_STAGING", "0") == "1":
        staging = cfg.get("staging") or {}
        if key in staging:
            return bool(staging[key])
    return bool(cfg.get(key, False))


def humanize_llm_config() -> dict[str, Any]:
    return dict(load_content_quality_config().get("humanize_llm") or {})


def humanize_llm_timeout(channel: str) -> int:
    """채널별 LLM timeout — env HERMES_HUMANIZE_LLM_TIMEOUT_{CHANNEL} > yaml > default."""
    cfg = humanize_llm_config()
    env_key = f"HERMES_HUMANIZE_LLM_TIMEOUT_{channel.upper()}"
    if os.environ.get(env_key):
        return int(os.environ[env_key])
    per = cfg.get("channel_timeouts") or {}
    if channel in per:
        return int(per[channel])
    if os.environ.get("HERMES_HUMANIZE_LLM_TIMEOUT"):
        return int(os.environ["HERMES_HUMANIZE_LLM_TIMEOUT"])
    return int(cfg.get("default_timeout_sec") or 120)


def humanize_llm_use_codex() -> bool:
    cfg = humanize_llm_config()
    if os.environ.get("HERMES_USE_CODEX", "") == "0":
        return False
    if os.environ.get("HERMES_USE_CODEX", "") == "1":
        return True
    return bool(cfg.get("use_codex", True))
