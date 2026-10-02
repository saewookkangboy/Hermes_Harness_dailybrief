"""M3 Resource & Tech Map — 도구 카탈로그 + 오픈소스·논문·최신 릴리스 + 학습 리소스 (신선도 점수)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lib.ax.config import load_config
from lib.ax.evidence import EvidencePack
from lib.ax.topic_spec import TopicSpec


def build_resource_map(
    spec: TopicSpec,
    pack: EvidencePack,
    blueprint: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()
    stage_labels = {k: v.get("label", k) for k, v in (cfg.get("value_chain") or {}).items()}
    priority = {o["stage"]: o["priority"] for o in (blueprint or {}).get("opportunities") or []}

    tools: list[dict[str, Any]] = []
    seen: set[str] = set()
    for d in [spec.domain, *spec.secondary_domains]:
        for t in (cfg.get("domain_tools") or {}).get(d, []):
            if t["name"] not in seen:
                seen.add(t["name"])
                tools.append({**t, "stage_label": stage_labels.get(t.get("stage"), t.get("stage")), "origin": "도메인 특화"})
    for stage, items in (cfg.get("tool_catalog") or {}).items():
        for t in items:
            if t["name"] not in seen:
                seen.add(t["name"])
                tools.append({**t, "stage": stage, "stage_label": stage_labels.get(stage, stage), "origin": "공통"})
    tools.sort(key=lambda t: (t["origin"] != "도메인 특화", -priority.get(t.get("stage"), 0)))

    oss = [
        {
            "name": ev.title,
            "url": ev.url,
            "stars": int(ev.meta.get("stars") or 0),
            "language": ev.meta.get("language") or "",
            "updated": ev.published,
            "freshness": ev.freshness,
            "note": ev.snippet,
        }
        for ev in pack.by_source("github")
    ]
    oss.sort(key=lambda r: (r["freshness"], r["stars"]), reverse=True)

    papers = [
        {"title": ev.title, "url": ev.url, "published": ev.published, "freshness": ev.freshness, "note": ev.snippet}
        for ev in pack.by_source("arxiv")
    ]

    latest = [
        {
            "title": ev.title,
            "url": ev.url,
            "source": ev.source_type,
            "published": ev.published,
            "freshness": ev.freshness,
        }
        for ev in pack.items
        if ev.source_type in ("news", "web", "hn") and ("tech_tools" in ev.lenses or "market_news" in ev.lenses)
    ]
    latest.sort(key=lambda r: r["freshness"], reverse=True)

    guides = [
        {"name": ev.title, "url": ev.url, "note": ev.snippet} for ev in pack.by_lens("definition")[:3]
    ]
    learning = guides + list(cfg.get("learning_resources") or [])

    fresh_values = [r["freshness"] for r in oss + papers + latest]
    return {
        "topic": spec.keyword,
        "stamp": spec.stamp,
        "tools": tools,
        "open_source": oss[:8],
        "papers": papers[:6],
        "latest": latest[:8],
        "learning": learning[:8],
        "freshness_avg": round(sum(fresh_values) / len(fresh_values), 2) if fresh_values else 0.0,
    }


def render_resource_map(rm: dict[str, Any]) -> str:
    out = [
        f"# [Resource & Tech Map] {rm['topic']}",
        "",
        f"> {rm['stamp']} · 도구 {len(rm['tools'])} · 오픈소스 {len(rm['open_source'])} · 논문 {len(rm['papers'])} · "
        f"최신 기술 {len(rm['latest'])} · 평균 신선도 {rm['freshness_avg']:.2f}",
        "",
        "## 도구·플랫폼",
        "",
        "| 도구 | 가치사슬 | 구분 | 용도 | URL |",
        "|------|----------|------|------|-----|",
    ]
    for t in rm["tools"]:
        out.append(f"| {t['name']} | {t.get('stage_label', '')} | {t['origin']} | {t.get('note', '')} | {t['url']} |")
    out += ["", "## 오픈소스 (GitHub)", ""]
    if rm["open_source"]:
        out += ["| 레포 | ⭐ | 언어 | 최근 업데이트 | 신선도 | URL |", "|------|----|------|---------------|--------|-----|"]
        for r in rm["open_source"]:
            out.append(f"| {r['name']} | {r['stars']} | {r['language'] or '—'} | {r['updated'] or '—'} | {r['freshness']:.2f} | {r['url']} |")
    else:
        out.append("- 이번 수집에서는 조건(최근 180일·스타 기준)을 만족한 레포가 없었어요.")
    out += ["", "## 연구·논문 (arXiv)", ""]
    if rm["papers"]:
        out += [f"- **{p['title']}** ({p['published'] or '날짜 미상'}) — {p['url']}" for p in rm["papers"]]
    else:
        out.append("- 이번 수집에서는 관련 논문이 없었어요.")
    out += ["", "## 최신 기술·릴리스", ""]
    if rm["latest"]:
        out += [f"- {r['title']} ({r['published'] or '날짜 미상'} · 신선도 {r['freshness']:.2f}) — {r['url']}" for r in rm["latest"]]
    else:
        out.append("- 최근 릴리스 신호가 부족해요. 다음 실행에서 다시 확인해요.")
    out += ["", "## 학습 리소스", ""]
    out += [f"- **{r['name']}** — {r.get('note', '')} {r['url']}".replace("  ", " ") for r in rm["learning"]]
    return "\n".join(out) + "\n"


def write_resource_map(rm: dict[str, Any], md_path: Path, json_path: Path) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_resource_map(rm), encoding="utf-8")
    json_path.write_text(json.dumps(rm, ensure_ascii=False, indent=2), encoding="utf-8")
