"""M5 Content Execution — Topic Pack(Brief·Blueprint·Resource·Future) → 채널 초안 + naturalness 채점."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lib.ax.config import artifact_path
from lib.ax.evidence import EvidencePack, select_top
from lib.ax.text import clip, eulreul, eunneun, euro, ieyo
from lib.ax.topic_spec import TopicSpec
from lib.content_quality_config import naturalness_min_score
from lib.naturalness_audit import score_naturalness

CHANNELS = ("blog", "linkedin", "newsletter", "threads", "instagram")


def hashtags(spec: TopicSpec) -> list[str]:
    tags = []
    for tok, en in zip(spec.tokens, spec.en_tokens):
        tags.append("#" + re.sub(r"[^0-9A-Za-z가-힣]", "", tok))
        if en and en != tok:
            tags.append("#" + "".join(w.capitalize() for w in re.split(r"[\s\-]+", en)))
    tags.append("#" + re.sub(r"\s+", "", spec.ko_query))
    tags += ["#마케팅자동화", "#AX", "#AI마케팅", "#마케팅트렌드"]
    return list(dict.fromkeys(t for t in tags if len(t) > 1))[:8]


def _ranked(bp: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(bp.get("opportunities") or [], key=lambda o: o["priority"], reverse=True)


def _short_automation(o: dict[str, Any]) -> str:
    return o["automation"].split(" — ")[0]


def repr_kpi(o: dict[str, Any]) -> str:
    return f"'{o['kpi']}'"


def build_linkedin(spec: TopicSpec, pack: EvidencePack, bp: dict, rm: dict, fa: dict) -> str:
    ranked = _ranked(bp)
    first = ranked[0]
    now = next((p for p in fa["predictions"] if p["horizon"] == "now"), None)
    lines = [
        f"'{spec.ko_query}', 지금 어디까지 자동화할 수 있을까요?",
        f"저는 이번에 근거 {pack.relevant_count}건을 7개 렌즈로 나눠 다시 봤어요.",
        "",
        f"가장 먼저 손댈 곳은 {ieyo(first['label'])}.",
        "",
    ]
    for o in ranked[:3]:
        lines.append(f"→ {o['label']}: {_short_automation(o)}부터 시작해요.")
    lines.append(f"→ 지켜야 할 선: {first['hitl']}.")
    lines.append("")
    if now:
        lines.append(f"{now['statement'].split('. ')[0]}.")
    tool = next((t["name"] for t in rm.get("tools") or []), "")
    if tool:
        lines.append(f"도구는 {tool}처럼 이미 검증된 것부터 붙이는 편이 빨라요.")
    lines += [
        "",
        f"여러분 팀은 '{spec.ko_query}'에서 어느 단계부터 자동화하고 계신가요? 댓글로 알려 주실래요?",
    ]
    body = "\n".join(lines)
    sources = [ev.url for ev in select_top(pack, 3)]
    return body + "\n\n---\n\n" + " ".join(hashtags(spec)) + "\n\n출처:\n" + "\n".join(f"- {u}" for u in sources) + "\n"


def build_newsletter(spec: TopicSpec, pack: EvidencePack, bp: dict, rm: dict, fa: dict) -> str:
    ranked = _ranked(bp)
    top = select_top(pack, 3)
    preds = {p["horizon"]: p for p in fa["predictions"]}
    subject_a = clip(f"{spec.ko_query}, 어디부터 자동화할까요", 50).rstrip(".")
    subject_b = clip(f"{spec.ko_query} 실무 지도: 도구·사례·전망", 50).rstrip(".")
    out = [
        f"# {spec.keyword} — AX 실무 레터",
        "",
        "## 제목 후보",
        "",
        f"- A: {subject_a}",
        f"- B: {subject_b}",
        "",
        "## 30초 TLDR",
        "",
        f"- 근거 {pack.relevant_count}건을 7개 렌즈로 정리했고, 가장 먼저 자동화할 단계는 {ieyo(ranked[0]['label'])}.",
        f"- 성숙도는 {bp['maturity']['current']}에서 {bp['maturity']['target']}까지 끌어올리는 걸 목표로 잡았어요.",
        f"- 18개월 이후 신호도 {len(fa['weak_signals'])}개 잡혀 있어서 관찰 목록에 올려 뒀어요.",
        "",
        "## 오늘의 1가지",
        "",
        f"저는 이번 주 '{spec.ko_query}' 자료를 보면서 {ranked[0]['label']} 단계의 자동화 여지가 가장 크다고 판단했어요. "
        f"{_short_automation(ranked[0])}부터 시작하고, 성과는 {euro(repr_kpi(ranked[0]))} 확인해요.",
        "",
        "## 3분 읽기",
        "",
        "### 1. AX 설계",
        "",
        *[f"- {o['label']} ({o['quadrant_label']}): {_short_automation(o)}부터 시작해요." for o in ranked[:3]],
        "",
        "### 2. 도구와 리소스",
        "",
        *[f"- {t['name']}: {t.get('note', '')} 용도로 써요. {t['url']}" for t in (rm.get("tools") or [])[:3]],
        "",
        "### 3. 앞으로의 흐름",
        "",
        *[f"- {p['label']}: {p['statement'].split('. ')[0]}." for p in preds.values()],
        "",
        "## 이번 주 실습 1가지",
        "",
        f"{fa['actions'][0]} 한 주 뒤에 숫자를 비교해 보세요.",
        "",
        "## 출처",
        "",
        *[f"- {ev.title} — {ev.url}" for ev in top],
        "",
    ]
    return "\n".join(out)


def build_blog(spec: TopicSpec, pack: EvidencePack, bp: dict, rm: dict, fa: dict) -> str:
    ranked = _ranked(bp)
    top = select_top(pack, 5)
    out = [
        f"# [AX 리서치] {spec.keyword}: 자동화 지도와 앞으로의 방향",
        "",
        "## 주요 트렌드",
        "",
        f"{spec.ko_query} 관련 근거 {pack.relevant_count}건을 정의, 시장, 기술, 사례, 규제, 한국 맥락, 미래 신호의 7개 렌즈로 분류했습니다.",
        "",
        *[f"- {ev.title} ({ev.domain})" for ev in top],
        "",
        "## 핵심 기술",
        "",
        *[f"- {t['name']}: {t.get('note', '')} 용도로 활용할 수 있습니다." for t in (rm.get("tools") or [])[:4]],
        *[f"- 오픈소스 {r['name']}: 최근 업데이트 {r['updated'] or '미상'} 기준으로 검토할 만합니다." for r in (rm.get("open_source") or [])[:2]],
        "",
        "## AX 자동화 설계",
        "",
        f"현재 성숙도는 {bp['maturity']['current']}로 가정하고, 목표는 {bp['maturity']['target']}로 설정했습니다.",
        "",
        *[f"- {o['label']} ({o['quadrant_label']}): {eulreul(_short_automation(o))} 우선 검토합니다. 핵심 지표는 {o['kpi']}입니다." for o in ranked[:4]],
        "",
        "## 시사점",
        "",
        *[f"- {p['label']}: 신뢰도 {p['confidence_label']} 수준의 신호가 확인됩니다." for p in fa["predictions"]],
        f"- 자동화의 속도보다 승인 단계와 중단 기준을 먼저 갖추는 것이 중요합니다.",
        "",
        "## 한 줄 요약",
        "",
        f"{eunneun(spec.ko_query)} {ranked[0]['label']} 단계부터 작게 자동화하고, 규제 신호를 함께 추적하는 것이 현실적인 출발점입니다.",
        "",
        "## 출처",
        "",
        *[f"- {ev.url}" for ev in top],
        "",
    ]
    return "\n".join(out)


def build_threads(spec: TopicSpec, pack: EvidencePack, bp: dict, rm: dict, fa: dict) -> str:
    first = _ranked(bp)[0]
    return "\n".join(
        [
            f"'{spec.ko_query}' 자동화, {first['label']}부터 시작해 보세요.",
            "",
            f"근거 {pack.relevant_count}건을 7개 렌즈로 정리했고, 6개월·18개월·36개월 흐름까지 붙였어요.",
            "",
            "[블로그 링크]",
            "",
            "여러분 팀은 지금 어느 단계에 계신가요?",
            "",
        ]
    )


def build_instagram(spec: TopicSpec, pack: EvidencePack, bp: dict, rm: dict, fa: dict) -> str:
    ranked = _ranked(bp)
    slides = [
        (f"{spec.ko_query}, 어디부터 자동화할까", f"근거 {pack.relevant_count}건 · 7개 렌즈"),
        (f"1순위는 {ranked[0]['label']}", _short_automation(ranked[0])),
        ("앞으로 36개월", " / ".join(p["label"].split(" ")[0] for p in fa["predictions"])),
    ]
    out = [f"# [Instagram] {spec.keyword}", ""]
    for i, (title, sub) in enumerate(slides, 1):
        out += [
            f"### Slide {i}",
            "",
            f"- **카피:** {title}",
            f"- **보조:** {sub}",
            f"- **이미지 생성 프롬프트:** Minimal editorial card, 4:5 (1080×1350), headline '{title}', clean grid, brand accent color",
            f"- **Alt text:** {title} — {sub}",
            "",
        ]
    caption = [
        f"'{spec.ko_query}' 자동화 지도를 3장으로 정리했어요.",
        f"→ 1순위는 {ieyo(ranked[0]['label'])}.",
        f"→ 성숙도 목표는 {ieyo(bp['maturity']['target'])}.",
        "→ 규제 신호도 함께 봐야 해요.",
        "나중에 다시 보려면 저장하고, 팀에도 공유해 주세요.",
        "여러분 팀은 어느 단계부터 시작할 건가요?",
    ]
    out += ["## 캡션", "", "\n".join(caption), "", "---", "", "## 해시태그", "", " ".join(hashtags(spec)), ""]
    return "\n".join(out)


BUILDERS = {
    "blog": build_blog,
    "linkedin": build_linkedin,
    "newsletter": build_newsletter,
    "threads": build_threads,
    "instagram": build_instagram,
}


def _scored_text(channel: str, text: str) -> str:
    if channel == "linkedin":
        return text.split("---")[0].strip()
    if channel == "instagram":
        m = re.search(r"## 캡션\n\n(.+?)\n\n---", text, re.S)
        return m.group(1) if m else text
    return text


def score_channels(drafts: dict[str, str]) -> dict[str, dict[str, Any]]:
    out = {}
    for ch in ("blog", "linkedin", "newsletter", "instagram"):
        if ch not in drafts:
            continue
        ns = score_naturalness(_scored_text(ch, drafts[ch]), channel=ch)
        minimum = naturalness_min_score(ch)
        out[ch] = {"score": ns.score, "min": minimum, "passed": ns.score >= minimum, "issues": ns.issues[:3]}
    return out


def build_channels(spec: TopicSpec, pack: EvidencePack, bp: dict, rm: dict, fa: dict) -> dict[str, str]:
    return {ch: fn(spec, pack, bp, rm, fa) for ch, fn in BUILDERS.items()}


def write_channels(spec: TopicSpec, drafts: dict[str, str]) -> dict[str, Path]:
    paths = {}
    for ch, text in drafts.items():
        p = artifact_path(spec.slug, spec.stamp, ch)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        paths[ch] = p
    return paths
