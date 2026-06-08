"""뉴스레터 ESP 발송 — dry-run manifest + 선택적 Resend live."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.newsletter_quality import load_newsletter_config, _preheader  # noqa: PLC2701

WORKDIR = Path.home() / "hermes-content-studio"
LOG_DIR = WORKDIR / "content" / "logs"


def _esp_cfg(cfg: dict | None = None) -> dict[str, Any]:
    c = cfg or load_newsletter_config()
    return dict(c.get("esp") or {})


def resolve_newsletter_pair(stamp: str) -> tuple[Path, Path]:
    """가장 최근 갱신된 md/html 쌍."""
    nl_dir = WORKDIR / "content" / "newsletter"
    pairs: list[tuple[float, Path, Path]] = []
    for html in nl_dir.glob(f"{stamp}_newsletter_*.html"):
        md = html.with_suffix(".md")
        if md.exists():
            pairs.append((html.stat().st_mtime, html, md))
    if not pairs:
        raise FileNotFoundError(f"newsletter html/md not found for {stamp}")
    pairs.sort(key=lambda x: x[0], reverse=True)
    _, html, md = pairs[0]
    return html, md


def _brief_summary(stamp: str) -> str:
    brief = WORKDIR / "content" / "research" / f"{stamp}_brief.md"
    if not brief.exists():
        return ""
    text = brief.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip() and not line.startswith("#"):
            return line.strip()[:200]
    return ""


def _load_scores(stamp: str) -> dict[str, Any]:
    path = WORKDIR / "content" / "newsletter" / f"{stamp}_newsletter_subject-scores.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def build_send_manifest(stamp: str, *, cfg: dict | None = None) -> dict[str, Any]:
    c = cfg or load_newsletter_config()
    esp = _esp_cfg(c)
    html_path, md_path = resolve_newsletter_pair(stamp)
    scores = _load_scores(stamp)
    winner = scores.get("winner") or {}
    subject = str(winner.get("text") or "Hermes Weekly")
    summary = _brief_summary(stamp)
    preheader = _preheader(summary, c)
    voice = c.get("voice") or {}
    return {
        "stamp": stamp,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "dry_run",
        "provider": esp.get("provider", "resend"),
        "from": esp.get("from", "Hermes Studio <onboarding@resend.dev>"),
        "to": esp.get("test_recipient", ""),
        "subject": subject,
        "preheader": preheader,
        "html_path": str(html_path),
        "md_path": str(md_path),
        "winner_score": winner.get("score"),
        "send_window": c.get("send_window"),
    }


def write_send_manifest(stamp: str, *, cfg: dict | None = None) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_send_manifest(stamp, cfg=cfg)
    path = LOG_DIR / f"{stamp}_newsletter-send-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def send_via_resend(manifest: dict[str, Any], *, api_key: str) -> dict[str, Any]:
    html_path = Path(manifest["html_path"])
    body = {
        "from": manifest["from"],
        "to": [manifest["to"]] if manifest.get("to") else [],
        "subject": manifest["subject"],
        "html": html_path.read_text(encoding="utf-8"),
        "headers": {"X-Entity-Ref-ID": manifest.get("stamp", "")},
    }
    if manifest.get("preheader"):
        body["headers"]["X-Preheader"] = manifest["preheader"]
    if not body["to"]:
        raise ValueError("esp.test_recipient or --to required for live send")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend API {e.code}: {detail}") from e


def execute_send(stamp: str, *, live: bool = False, to: str = "") -> dict[str, Any]:
    manifest = build_send_manifest(stamp)
    path = write_send_manifest(stamp)
    result: dict[str, Any] = {"stamp": stamp, "manifest_path": str(path), "mode": "dry_run"}

    if live:
        api_key = os.environ.get("RESEND_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError("RESEND_API_KEY required for --live")
        if to:
            manifest["to"] = to
        esp = _esp_cfg()
        if not manifest.get("to"):
            manifest["to"] = esp.get("test_recipient", "")
        manifest["mode"] = "live"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        api_resp = send_via_resend(manifest, api_key=api_key)
        result.update({"mode": "live", "provider_response": api_resp})
    return result
