"""뉴스레터 인사이트 선별 — 신선도·안전·제목 정합 (결정적)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from lib.content_quality import Insight, has_meaningful_korean, polish_display_title
from lib.newsletter_issue_ledger import recent_excluding, topic_key

_STALE_DEFAULT = [
    "한국 AX 전환 — 교육·FAQ·사례 중심",
    "ChatGPT Workspace Agents 실무 검토",
    "Claude 엔터프라이즈 — 거버넌스·컨텍스트",
    "2026 AI·마케팅 실무 인사이트",
]


@dataclass
class SelectedIssue:
    hero: Insight
    modules: list[Insight]
    display_titles: dict[int, str]  # insight id(index) -> display title
    topic: str
    pattern_id: str
    subject_candidates: list[str]
    reasons: list[str] = field(default_factory=list)

    @property
    def insights(self) -> list[Insight]:
        out = [self.hero]
        for m in self.modules:
            if m is not self.hero:
                out.append(m)
        # unique by url+title
        seen: set[str] = set()
        uniq: list[Insight] = []
        for ins in out:
            key = f"{ins.url}|{ins.title}"
            if key in seen:
                continue
            seen.add(key)
            uniq.append(ins)
        return uniq[:3] if uniq else [self.hero]


def _cfg_list(cfg: dict, *path: str, default: list | None = None) -> list:
    cur: Any = cfg
    for key in path:
        if not isinstance(cur, dict):
            return list(default or [])
        cur = cur.get(key)
    if isinstance(cur, list):
        return cur
    return list(default or [])


def is_unsafe_insight(ins: Insight, cfg: dict | None = None) -> bool:
    c = cfg or {}
    safety = c.get("safety") or {}
    blob = " ".join(
        [
            ins.source_title or "",
            ins.title or "",
            ins.url or "",
            ins.summary or "",
            ins.marketer_view or "",
        ]
    ).lower()
    for needle in safety.get("block_url_substrings") or [
        "undress",
        "undresser",
        "nsfw",
        "deepnude",
    ]:
        if needle.lower() in blob:
            return True
    for needle in safety.get("block_title_substrings") or ["Undress", "NSFW"]:
        if needle.lower() in blob:
            return True
    return False


def _source_title(ins: Insight) -> str:
    return (getattr(ins, "source_title", None) or "").strip()


def concrete_localize(source_title: str) -> str:
    """영문 원제목을 구체 한국어로 — 정적 AX 폴백 금지."""
    raw = re.sub(r"\.{2,}$", "", (source_title or "").strip())
    if not raw:
        return "이번 주 B2B AI 실무 신호"
    if has_meaningful_korean(raw) and len(re.findall(r"[가-힣]", raw)) >= 8:
        return re.sub(r"\s+", " ", raw).strip()
    tl = raw.lower()

    rules = [
        (r"aeo|answer engine|ai search statistics|ai overviews", "AEO·AI 검색 인용 실무"),
        (r"hsad|deep agent builder", "HSAD Deep Agent Builder — 마케터용 에이전트"),
        (r"ads?\s+on\s+chatgpt|chatgpt.*\bads?\b|advertising.*chatgpt", "ChatGPT 광고 테스트 — B2B 영향"),
        (r"claude.*(?:update|release|july)", "Claude 7월 업데이트 — 엔터프라이즈"),
        (r"megazone|korean re", "메가존·코리안리 AX 협력 신호"),
        (r"kolon|benit|win-win ax", "코오롱베니트 SME AX 파일럿"),
        (r"gemini", "Google Gemini 업데이트 — AEO·Workspace"),
        (r"perplexity", "Perplexity·AI 검색 최적화 실무"),
        (r"anthropic|claude", "Claude 엔터프라이즈 실무 점검"),
        (r"openai.*news|openai news", "OpenAI 주간 릴리스 — 마케팅 활용"),
        (r"workspace agent", "ChatGPT Workspace Agents 파일럿"),
        (r"release notes|chatgpt business", "ChatGPT 릴리스 노트 주간 펄스"),
    ]
    for pat, label in rules:
        if re.search(pat, tl, re.I):
            return label

    # Brand + short gloss — never collapse to generic AX
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]+", raw)
    brand = " ".join(words[:4]).strip()
    if brand:
        gloss = polish_display_title(raw)
        if gloss and gloss not in _STALE_DEFAULT and "실무 인사이트" not in gloss:
            return gloss if has_meaningful_korean(gloss) else f"{brand} — 실무 점검"
        return f"{brand} — 실무 점검"
    return "이번 주 B2B AI 실무 신호"


def title_integrity_ok(ins: Insight, cfg: dict | None = None) -> bool:
    """한국어 표시제와 영문 원제/본문/URL 정합."""
    c = cfg or {}
    integrity = c.get("title_integrity") or {}
    stale = set(integrity.get("stale_korean_titles") or _STALE_DEFAULT)
    display = (ins.title or "").strip()
    source = _source_title(ins)
    if display in stale and source:
        return False
    if not source:
        return display not in stale

    sl = source.lower()
    dl = display.lower()
    body = f"{ins.summary} {ins.insight_derivation} {ins.marketer_view}".lower()
    url = (ins.url or "").lower()

    if re.search(r"\bads?\b|advertis", sl) and "workspace" in dl:
        return False
    if re.search(r"hsad|deep agent", sl) and ("한국 ax" in dl or "교육·faq" in dl or "교육·faq" in display):
        return False
    if "advertis" in url and "workspace" in body and not re.search(r"\bads?\b|advertis", body):
        return False
    if re.search(r"hsad|deep agent", sl) and "ax 전환" in body and "agent builder" not in body and "hsad" not in body:
        # body drifted to generic AX essay
        return False
    return True


def display_title_for(ins: Insight, cfg: dict | None = None) -> str:
    c = cfg or {}
    integrity = c.get("title_integrity") or {}
    prefer = bool(integrity.get("prefer_source_when_korean_mismatch", True))
    stale = set(integrity.get("stale_korean_titles") or _STALE_DEFAULT)
    source = _source_title(ins)
    display = (ins.title or "").strip()

    if prefer and source and (display in stale or not title_integrity_ok(ins, c)):
        return concrete_localize(source)
    if display and display not in stale and has_meaningful_korean(display):
        return re.sub(r"\s+", " ", display).strip()
    if source:
        return concrete_localize(source)
    return concrete_localize(display or "B2B AI")


def coherence_score(ins: Insight, cfg: dict | None = None) -> int:
    if is_unsafe_insight(ins, cfg):
        return -10_000
    score = 40
    source = _source_title(ins)
    if source:
        score += 15
    if title_integrity_ok(ins, cfg):
        score += 25
    else:
        score -= 20
    if ins.url.startswith("https://"):
        score += 10
    body = f"{ins.insight_derivation} {ins.marketer_view} {ins.utilization}"
    if has_meaningful_korean(body) and len(body) >= 80:
        score += 10
    # Prefer concrete entities in source
    if source and re.search(r"[A-Z]{2,}|\d{4}|Builder|Ads|Release|Pilot", source):
        score += 8
    return score


def _pick_pattern_id(stamp: str, recent: list[dict], cfg: dict) -> str:
    patterns = cfg.get("subject_patterns") or []
    ids = [str(p.get("id") or f"p{i}") for i, p in enumerate(patterns)]
    if not ids:
        return "question"
    last = str(recent[0].get("pattern_id")) if recent else None
    streak = int((cfg.get("freshness") or {}).get("max_subject_pattern_streak", 1))

    # 실측 CTOR 가중치가 있으면 성과 좋은 패턴 우선 — 연속 사용 한도는 유지 (R26)
    try:
        from lib.newsletter_ctor_feedback import preferred_pattern_ids

        for pid in preferred_pattern_ids():
            if pid in ids and not (streak <= 1 and pid == last):
                return pid
    except ImportError:
        pass

    if last in ids:
        idx = (ids.index(last) + 1) % len(ids)
        return ids[idx]
    # deterministic by stamp day
    day = int(stamp.replace("-", "")[-2:] or "1")
    return ids[day % len(ids)]


def _subject_from_patterns(topic: str, stamp: str, pattern_id: str, cfg: dict) -> list[str]:
    from lib.newsletter_prose import fit_topic_for_subject, fix_subject_topic
    from lib.newsletter_subject import subject_limits

    max_c, _, _ = subject_limits(cfg)
    patterns = cfg.get("subject_patterns") or []
    by_id = {str(p.get("id")): str(p.get("template") or "") for p in patterns}
    primary = by_id.get(pattern_id) or "{topic} — 지금 손댈 곳은?"
    ordered = [pattern_id] + [i for i in by_id if i != pattern_id]
    out: list[str] = []
    for pid in ordered:
        tpl = by_id.get(pid) or primary
        t = fit_topic_for_subject(topic.strip().rstrip("."), tpl, max_c)
        cand = fix_subject_topic(t, tpl, stamp=stamp)
        if len(cand) > max_c:
            # 템플릿 예산에 맞춰 topic만 한 번 더 줄임 — mid-word 말줄임 금지
            t2 = fit_topic_for_subject(t, tpl, max_c - 2)
            cand = fix_subject_topic(t2, tpl, stamp=stamp)
            if len(cand) > max_c:
                # 최후: 공백/구분자 경계에서만 자르고 말줄임 없이 닫기
                cut = cand[:max_c].rstrip()
                for sep in (" ", "—", "·", ",", "-"):
                    if sep in cut[max(0, max_c - 12) :]:
                        cut = cut.rsplit(sep, 1)[0].rstrip()
                        break
                cand = cut[:max_c]
        out.append(cand)
        if len(out) >= 3:
            break
    while len(out) < 3:
        out.append(f"[{stamp}] B2B AI 주간 신호"[:max_c])
    return out


def select_issue_insights(
    stamp: str,
    insights: list[Insight],
    cfg: dict | None = None,
) -> SelectedIssue:
    """안전·정합·신선도 기준으로 히어로+모듈 선별."""
    c = cfg or {}
    fresh = c.get("freshness") or {}
    recent = recent_excluding(stamp, c, lookback=int(fresh.get("lookback_issues", 7)))
    recent_topics = {str(r.get("topic_key") or "") for r in recent}
    recent_subjects = {str(r.get("subject") or "") for r in recent}

    scored: list[tuple[int, Insight, str]] = []
    reasons: list[str] = []
    for ins in insights:
        if is_unsafe_insight(ins, c):
            reasons.append(f"skip_unsafe:{(_source_title(ins) or ins.title)[:40]}")
            continue
        title = display_title_for(ins, c)
        key = topic_key(title)
        score = coherence_score(ins, c)
        if key in recent_topics:
            score -= 50
            reasons.append(f"penalize_reuse:{key}")
        scored.append((score, ins, title))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        # absolute fallback — first non-unsafe or first insight
        safe = [i for i in insights if not is_unsafe_insight(i, c)] or list(insights)
        hero = safe[0]
        title = display_title_for(hero, c)
        pattern_id = _pick_pattern_id(stamp, recent, c)
        return SelectedIssue(
            hero=hero,
            modules=safe[:3],
            display_titles={0: title},
            topic=title,
            pattern_id=pattern_id,
            subject_candidates=_subject_from_patterns(title, stamp, pattern_id, c),
            reasons=reasons + ["fallback_empty_scored"],
        )

    picked: list[tuple[Insight, str]] = []
    used_keys: set[str] = set()
    for score, ins, title in scored:
        key = topic_key(title)
        if key in used_keys:
            continue
        picked.append((ins, title))
        used_keys.add(key)
        if len(picked) >= 3:
            break

    hero_ins, hero_title = picked[0]
    # Avoid repeating exact winning subject from recent
    pattern_id = _pick_pattern_id(stamp, recent, c)
    subjects = _subject_from_patterns(hero_title, stamp, pattern_id, c)
    subjects = [s for s in subjects if s not in recent_subjects] or subjects

    display_map = {i: t for i, (_, t) in enumerate(picked)}
    reasons.append(f"hero={hero_title}")
    reasons.append(f"pattern={pattern_id}")
    reasons.append(f"scores={[coherence_score(ins, c) for ins, _ in picked]}")

    return SelectedIssue(
        hero=hero_ins,
        modules=[ins for ins, _ in picked],
        display_titles=display_map,
        topic=hero_title,
        pattern_id=pattern_id,
        subject_candidates=subjects,
        reasons=reasons,
    )
