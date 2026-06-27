"""M4 Performance Coach — CTOR 피드백 → 전 채널 코칭 (결정적)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from lib.brief_graph import load_brief_graph
from lib.common import studio_today, truncate
from lib.m4_analytics import build_m4_report, notion_tier_stats
from lib.m4_channel_metrics import format_channel_metrics_block, load_channel_metrics, sync_ctor_to_channel_metrics
from lib.newsletter_ctor_feedback import apply_ctor_feedback_bonus, compute_ctor_feedback, load_ctor_feedback
from lib.newsletter_subject import score_subject_line

WORKDIR = Path.home() / "hermes-content-studio"
LOGS_DIR = WORKDIR / "content" / "logs"
HANDOFF_DIR = WORKDIR / ".harness" / "handoffs"
CONFIG_PATH = WORKDIR / "config" / "m4-coach.yaml"


@dataclass
class ChannelCoach:
    channel: str
    status: str  # PASS | WARN | SKIP
    score: int = 0
    traits: dict[str, bool] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    artifact: str = ""


@dataclass
class CoachReport:
    stamp: str
    analytics_mode: str = "simulation"
    ctor_feedback_applied: bool = False
    channels: list[ChannelCoach] = field(default_factory=list)
    global_actions: list[str] = field(default_factory=list)
    rising_topics: list[str] = field(default_factory=list)


def _load_cfg() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _glob_channel_file(stamp: str, pattern: str) -> Path | None:
    matches = sorted(WORKDIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _trait_weights() -> dict[str, int]:
    fb = load_ctor_feedback()
    if not fb.get("applied"):
        fb = compute_ctor_feedback()
    return dict(fb.get("weights") or {})


def _score_text_traits(text: str, weights: dict[str, int]) -> tuple[int, list[str], dict[str, bool]]:
    from lib.newsletter_ctor_feedback import _subject_traits

    traits = _subject_traits(text)
    bonus, reasons = apply_ctor_feedback_bonus(text, {"applied": bool(weights), "weights": weights})
    base = score_subject_line(text, apply_ctor_feedback=False)
    score = min(100, max(0, base.score + bonus))
    return score, reasons + base.reasons[:2], traits


def _coach_newsletter(stamp: str, weights: dict[str, int]) -> ChannelCoach:
    coach = ChannelCoach(channel="newsletter", status="SKIP")
    scores_path = WORKDIR / "content" / "newsletter" / f"{stamp}_newsletter_subject-scores.json"
    nl_path = _glob_channel_file(stamp, f"content/newsletter/{stamp}_newsletter_*.md")
    if scores_path.exists():
        try:
            data = json.loads(scores_path.read_text(encoding="utf-8"))
            winner = data.get("winner") or {}
            title = str(winner.get("text") or "")
            if title:
                score, reasons, traits = _score_text_traits(title, weights)
                coach.score = score
                coach.traits = traits
                coach.artifact = str(scores_path)
                coach.status = "PASS" if score >= 60 else "WARN"
                coach.recommendations.append(
                    f"제목 score {score} — {', '.join(reasons[:2])}"
                )
        except (json.JSONDecodeError, OSError):
            pass
    metrics = load_channel_metrics().get("channels", {}).get("newsletter") or {}
    if metrics.get("mode") == "live":
        avg = metrics.get("avg_ctor_pct")
        coach.recommendations.append(f"CTOR 실측 avg {avg}% — healthy {metrics.get('healthy_count', 0)}건")
        if avg and float(avg) < 10:
            coach.status = "WARN"
            coach.recommendations.append("CTOR 10% 미만 — 질문형 제목·단일 CTA A/B 테스트 권장")
    elif not coach.artifact:
        coach.recommendations.append(
            "CTOR 실측 없음 — newsletter-ctor-record.sh YYYY-MM-DD --delivered N --opens N --clicks N"
        )
    if nl_path:
        coach.artifact = coach.artifact or str(nl_path)
    return coach


def _coach_linkedin(stamp: str, weights: dict[str, int]) -> ChannelCoach:
    coach = ChannelCoach(channel="linkedin", status="SKIP")
    path = _glob_channel_file(stamp, f"content/linkedin/{stamp}_linkedin_*.md")
    if not path:
        coach.recommendations.append("산출물 없음 — run-content-package.sh 또는 run-linkedin-pipeline.sh")
        return coach
    text = path.read_text(encoding="utf-8", errors="replace")
    post = text.split("---")[0].strip() if "---" in text else text
    lines = [ln.strip() for ln in post.splitlines() if ln.strip()]
    hooks = lines[:2]
    hook_text = " ".join(hooks)
    score, reasons, traits = _score_text_traits(hook_text, weights)
    traits.update(
        {
            "bullet_arrows": "→" in post,
            "comment_cta": bool(re.search(r"댓글|\?", post)),
            "post_length_ok": len(post) <= 1300,
        }
    )
    if traits["bullet_arrows"]:
        score += 5
    if traits["comment_cta"]:
        score += 8
    if not traits["post_length_ok"]:
        score -= 10
        coach.recommendations.append(f"본문 {len(post)}자 — 1300자 이내로 압축")
    coach.score = min(100, score)
    coach.traits = traits
    coach.artifact = str(path)
    coach.status = "PASS" if coach.score >= 55 else "WARN"
    coach.recommendations.insert(0, f"Hook score {coach.score} — {', '.join(reasons[:2])}")

    ch_metrics = load_channel_metrics().get("channels", {}).get("linkedin") or {}
    if ch_metrics.get("mode") == "live":
        coach.recommendations.append(f"실측 import됨 — {ch_metrics.get('source', '')}")
    else:
        coach.recommendations.append(
            "LinkedIn 실측 없음 — m4-import-metrics.sh linkedin metrics.json"
        )
    if weights.get("question", 0) > 0 and not traits.get("question"):
        coach.recommendations.append("CTOR 피드백: 질문형 hook·CTA 추가 (+question trait)")
    return coach


def _coach_blog(stamp: str, weights: dict[str, int]) -> ChannelCoach:
    coach = ChannelCoach(channel="blog", status="SKIP")
    path = _glob_channel_file(stamp, f"content/blog/{stamp}_blog_*.html")
    if not path:
        coach.recommendations.append("산출물 없음 — run-blog-pipeline.sh")
        return coach
    html = path.read_text(encoding="utf-8", errors="replace")
    title_m = re.search(r"<title>([^<]+)</title>", html, re.I)
    title = title_m.group(1).strip() if title_m else ""
    h2_count = len(re.findall(r"<h2", html, re.I))
    traits = {
        "title_length": 20 <= len(title) <= 60 if title else False,
        "h2_count": h2_count >= 3,
        "faq_jsonld": "FAQPage" in html or '"@type": "FAQPage"' in html,
        "geo_block": "geo-quote" in html.lower() or "GEO" in html,
    }
    score = 50
    if traits["title_length"]:
        score += 15
    if traits["h2_count"]:
        score += 15
    if traits["faq_jsonld"]:
        score += 10
    if traits["geo_block"]:
        score += 10
    if title:
        sub_score, reasons, _ = _score_text_traits(title, weights)
        score = (score + sub_score) // 2
        coach.recommendations.append(f"제목 trait — {', '.join(reasons[:2])}")
    if not traits["faq_jsonld"]:
        coach.recommendations.append("FAQ JSON-LD 추가 — AEO 스니펫 강화")
    if not traits["h2_count"]:
        coach.recommendations.append(f"H2 {h2_count}개 — 3개 이상 권장")
    coach.score = score
    coach.traits = traits
    coach.artifact = str(path)
    coach.status = "PASS" if score >= 60 else "WARN"
    ch_metrics = load_channel_metrics().get("channels", {}).get("blog") or {}
    if ch_metrics.get("mode") != "live":
        coach.recommendations.append("Blog 실측 없음 — GA4/search console JSON import 가능")
    return coach


def _coach_instagram(stamp: str, weights: dict[str, int]) -> ChannelCoach:
    coach = ChannelCoach(channel="instagram", status="SKIP")
    path = _glob_channel_file(stamp, f"content/instagram/{stamp}_instagram_*.md")
    if not path:
        coach.recommendations.append("산출물 없음 — run-instagram-pipeline.sh")
        return coach
    text = path.read_text(encoding="utf-8", errors="replace")
    caption_m = re.search(r"## 캡션.*?\n\n(.+?)\n\n---", text, re.S)
    caption = caption_m.group(1).strip() if caption_m else ""
    tags = re.findall(r"#[\w가-힣]+", text)
    slide_count = len(re.findall(r"^### Slide", text, re.M))
    traits = {
        "caption_hook": len(caption) >= 80,
        "hashtag_count": len(tags) >= 5,
        "slide_count": slide_count == 3,
        "alt_text": "Alt text" in text,
        "b2b_kw": bool(re.search(r"AX|AEO|B2B|AI", caption, re.I)),
    }
    score = 45
    if traits["caption_hook"]:
        score += 15
    if traits["hashtag_count"]:
        score += 10
    if traits["slide_count"]:
        score += 15
    if traits["alt_text"]:
        score += 10
    if traits["b2b_kw"]:
        score += 5
    if caption:
        hook_line = caption.splitlines()[0] if caption else ""
        sub, reasons, _ = _score_text_traits(hook_line, weights)
        score = (score + sub) // 2
    if not traits["hashtag_count"]:
        coach.recommendations.append(f"해시태그 {len(tags)}개 — 5개 권장")
    coach.score = score
    coach.traits = traits
    coach.artifact = str(path)
    coach.status = "PASS" if score >= 55 else "WARN"
    return coach


def _rising_topics(limit: int = 3) -> list[str]:
    graph = load_brief_graph()
    streaks = graph.get("streaks") or []
    out: list[str] = []
    for s in sorted(streaks, key=lambda x: (-x.get("streak_days", 0), -x.get("appearances", 0)))[:limit]:
        out.append(f"{s.get('topic_key')}: {truncate(s.get('latest_title', ''), 40)} ({s.get('streak_days')}d)")
    return out


def _global_actions(report_data: dict, fb: dict) -> list[str]:
    actions: list[str] = []
    if not fb.get("applied"):
        actions.append("CTOR 실측 2건 이상 기록 후 trait 가중치 자동 학습")
    nt = notion_tier_stats()
    if nt.get("draft_ratio_pct", 0) > 20:
        actions.append(f"Notion draft 비율 {nt['draft_ratio_pct']}% — notion_quality 개선 후 재동기화")
    regressions = [
        st
        for st, s in (report_data.get("stages") or {}).items()
        if s.get("vs_baseline_pct") and s["vs_baseline_pct"] > 25
    ]
    if regressions:
        actions.append(f"SLA 회귀 stage: {', '.join(regressions[:3])}")
    weights = fb.get("weights") or {}
    top_traits = sorted(weights.items(), key=lambda x: -x[1])[:2]
    if top_traits:
        trait_names = ", ".join(f"{k}({v:+d})" for k, v in top_traits)
        actions.append(f"CTOR 우수 trait — 전 채널에 반영: {trait_names}")
    return actions


def run_m4_coach(stamp: str | None = None, *, days: int = 7, write_report: bool = True) -> CoachReport:
    """전 채널 성과 코칭 리포트."""
    stamp = stamp or studio_today()
    sync_ctor_to_channel_metrics()
    fb = compute_ctor_feedback()
    weights = _trait_weights()
    m4 = build_m4_report(days, stamp=stamp)

    report = CoachReport(
        stamp=stamp,
        analytics_mode=str(m4.get("analytics_mode", "simulation")),
        ctor_feedback_applied=bool(fb.get("applied")),
    )
    report.channels = [
        _coach_newsletter(stamp, weights),
        _coach_linkedin(stamp, weights),
        _coach_blog(stamp, weights),
        _coach_instagram(stamp, weights),
    ]
    report.rising_topics = _rising_topics()
    report.global_actions = _global_actions(m4, fb)

    if write_report:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        md_path = LOGS_DIR / f"{stamp}_m4-coach.md"
        md_path.write_text(format_coach_report(report, fb), encoding="utf-8")
        HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
        handoff = HANDOFF_DIR / f"{stamp}_m4-coach.json"
        handoff.write_text(
            json.dumps(
                {
                    "stamp": stamp,
                    "analytics_mode": report.analytics_mode,
                    "ctor_feedback_applied": report.ctor_feedback_applied,
                    "channels": [
                        {
                            "channel": c.channel,
                            "status": c.status,
                            "score": c.score,
                            "recommendations": c.recommendations,
                        }
                        for c in report.channels
                    ],
                    "global_actions": report.global_actions,
                    "rising_topics": report.rising_topics,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    return report


def format_coach_report(report: CoachReport, fb: dict | None = None) -> str:
    fb = fb or load_ctor_feedback()
    lines = [
        f"# M4 Performance Coach — {report.stamp}",
        "",
        f"- **M4 모드:** {report.analytics_mode}",
        f"- **CTOR 피드백:** {'✅ 적용' if report.ctor_feedback_applied else '⏳ 대기 (실측 부족)'}",
        "",
        "## 채널별 코칭",
        "",
        "| 채널 | 상태 | Score | 권장 |",
        "|------|------|------:|------|",
    ]
    for ch in report.channels:
        sym = {"PASS": "✅", "WARN": "⚠️", "SKIP": "⏭"}.get(ch.status, "·")
        rec = ch.recommendations[0] if ch.recommendations else "—"
        lines.append(f"| {ch.channel} | {sym} | {ch.score} | {truncate(rec, 50)} |")

    if fb.get("trait_avgs"):
        lines.extend(["", "## CTOR trait 평균", ""])
        for k, v in sorted((fb.get("trait_avgs") or {}).items(), key=lambda x: -x[1]):
            w = (fb.get("weights") or {}).get(k, 0)
            lines.append(f"- `{k}`: avg {v}% · weight {w:+d}")

    if report.global_actions:
        lines.extend(["", "## 글로벌 액션", ""])
        lines.extend(f"- {a}" for a in report.global_actions)

    if report.rising_topics:
        lines.extend(["", "## Brief Graph 상승 주제", ""])
        lines.extend(f"- {t}" for t in report.rising_topics)

    lines.extend(["", "## Channel metrics", "", format_channel_metrics_block()])
    return "\n".join(lines)


def format_coach_summary(report: CoachReport) -> str:
    warn = sum(1 for c in report.channels if c.status == "WARN")
    lines = [
        f"🎯 M4 Coach · {report.stamp}",
        "",
        f"모드: {report.analytics_mode} · CTOR 피드백: {'ON' if report.ctor_feedback_applied else 'OFF'} · WARN {warn}",
        "",
    ]
    for ch in report.channels:
        if ch.status == "SKIP" and not ch.recommendations:
            continue
        sym = {"PASS": "✅", "WARN": "⚠️", "SKIP": "⏭"}.get(ch.status, "·")
        top = ch.recommendations[0] if ch.recommendations else ""
        lines.append(f"{sym} {ch.channel} ({ch.score}): {truncate(top, 55)}")
    if report.global_actions:
        lines.append("")
        lines.append(f"→ {report.global_actions[0]}")
    lines.append(f"\n📋 `content/logs/{report.stamp}_m4-coach.md`")
    return "\n".join(lines)
