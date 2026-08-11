"""뉴스레터 산문 정제 — 중복 문장 제거 · 보일러플레이트 스크럽 (결정적)."""
from __future__ import annotations

import re

_SENT_SPLIT = re.compile(r"(?<=[.!?。])\s+")
# 마침표 없이 붙은 한국어 종결 + 다음 문장 시작
_KO_GLUE = re.compile(
    r"(습니다|해요|이에요|예요|입니다|죠|네요)\s+(?=[A-Za-z가-힣*「『\"])"
)

# 독자용 본문에서 제거할 프로세스/채널 잔여 문구
BOILERPLATE_PHRASES = [
    "블로그 Direct Answer + SEO/AEO/GEO 통합",
    "SEO·AEO·GEO 인용 가능한 형태",
    "SEO·AEO·GEO 인용",
    "글로벌 사례를 국내 AX·에이전트 FAQ·강의·LinkedIn으로 재가공",
    "글로벌 신호를 국내 AX·에이전트 도입 맥락에 맞게 재해석하면 FAQ형 블로그, 소셜 캐러셀, LinkedIn 인사이트 포스트로 일관된 메시지를 유지할 수 있어요.",
    "글로벌 신호를 국내 AX·에이전트 도입 맥락에 맞게 재해석하면 FAQ형 블로그, 소셜 캐러셀, LinkedIn 인사이트 포스트로 일관된 메시지를 유지할 수 있습니다.",
    "브랜드·퍼포먼스·콘텐츠·AX 관점에서 재해석할 여지가 있어요.",
    "브랜드·퍼포먼스·콘텐츠·AX 관점에서 재해석할 여지가 있습니다.",
    "브랜드·퍼포먼스·콘텐츠·AX 관점에서 재해석할 여지가 있어요",
    "브랜드·퍼포먼스·콘텐츠·AX 관점에서 재해석할 여지가 있습니다",
    "2026 AI·마케팅 실무 인사이트 — ",
    "2026 AI·마케팅 실무 인사이트 —",
    "2026 AI·마케팅 실무 인사이트",
    "2026 마케팅 실무 인사이트 — ",
    "2026 마케팅 실무 인사이트 —",
    "2026 마케팅 실무 인사이트",
    "2026 AI 마케팅 실무 인사이트 — ",
    "2026 AI 마케팅 실무 인사이트 —",
    "2026 AI 마케팅 실무 인사이트",
    "글로벌·국내 AI·마케팅 교차 신호이에요.",
    "글로벌·국내 AI·마케팅 교차 신호입니다.",
    "글로벌·대한민국 AI·마케팅 교차 신호이에요.",
    "글로벌·대한민국 AI·마케팅 교차 신호입니다.",
    "통합 컨텍스트 → 채널 재가공 (blog|linkedin)",
    "통합 컨텍스트 → 채널 재가공 (lecture)",
    "통합 컨텍스트 → 채널 재가공 (instagram)",
    "통합 컨텍스트 → 채널 재가공",
    "Direct Answer·AEO 수요",
    "블로그 Direct Answer + SEO/AEO/GEO 통합",
    "맥롽",
]

_META_LEAD = re.compile(
    r"\d+번째\s*(?:로\s+주목할\s+주제는|인사이트는|인사이트)\s*.{0,160}?(?:에 대해 정리해요|에 대해 정리합니다)\.?\s*",
    re.I,
)
_META_SHORT = re.compile(
    r"\d+번째\s*(?:로\s+주목할\s+주제는|인사이트는)\s*",
    re.I,
)
_BRACKET_TAG = re.compile(r"^\[([^\]]+)\]\s*")


def scrub_phrase(text: str) -> str:
    t = (text or "").replace("맥롽", "맥락")
    for phrase in BOILERPLATE_PHRASES:
        t = t.replace(phrase, "")
    t = _META_LEAD.sub("", t)
    t = _META_SHORT.sub("", t)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s+([.!?。,])", r"\1", t)
    t = re.sub(r"(?:^|[.!?。]\s*)—\s*", lambda m: m.group(0).replace("— ", ""), t)
    return t.strip(" ,·/—")


def ensure_sentence_breaks(text: str) -> str:
    """종결어미 뒤에 공백만 있고 마침표가 없으면 문장 경계를 복구."""
    t = scrub_phrase(text)
    if not t:
        return ""
    return _KO_GLUE.sub(r"\1. ", t)


def _tokens(sentence: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9]{2,}|[가-힣]{2,}", sentence.lower()))


def sentence_similar(a: str, b: str, *, threshold: float = 0.68) -> bool:
    """토큰 Jaccard — '인용은/노출은'처럼 핵심 주장 반복을 잡음."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    union = len(ta | tb)
    if union == 0:
        return False
    if inter / union >= threshold:
        return True
    # 짧은 문장이 긴 문장에 거의 포함
    shorter, longer = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if shorter and inter / len(shorter) >= 0.85:
        return True
    return False


def _norm_key(sentence: str) -> str:
    s = re.sub(r"\s+", "", sentence.lower())
    s = re.sub(r"[\"'`“”‘’]", "", s)
    return s[:80]


def _is_dup(part: str, seen_texts: list[str]) -> bool:
    key = _norm_key(part)
    for prev in seen_texts:
        pk = _norm_key(prev)
        if key[:24] == pk[:24] or key[:24] in pk or pk[:24] in key:
            return True
        if sentence_similar(part, prev):
            return True
    return False


def unique_sentences(
    text: str,
    *,
    max_sentences: int | None = None,
    against: list[str] | None = None,
) -> str:
    """인접·유사 문장 제거 후 밀도 높은 산문. against에 이미 쓴 문장도 제외."""
    raw = ensure_sentence_breaks(text)
    if not raw:
        return ""
    parts = [p.strip() for p in _SENT_SPLIT.split(raw) if p.strip()]
    if len(parts) <= 1 and "。" not in raw and "." not in raw and "!" not in raw:
        parts = [raw]
    out: list[str] = []
    seen_texts: list[str] = []
    for block in against or []:
        blk = ensure_sentence_breaks(block)
        bits = [p.strip() for p in _SENT_SPLIT.split(blk) if p.strip()] if blk else []
        seen_texts.extend(bits or ([block] if block else []))
    for part in parts:
        part = scrub_phrase(part)
        if not part:
            continue
        part = _BRACKET_TAG.sub("", part).strip()
        if not part:
            continue
        if part[-1] not in ".!?。":
            part += "."
        if _is_dup(part, seen_texts):
            continue
        seen_texts.append(part)
        out.append(part)
        if max_sentences and len(out) >= max_sentences:
            break
    return " ".join(out)


def densify_hero_parts(
    *,
    title: str,
    problem: str,
    explanation: str,
    insight: str,
    apply: str,
) -> str:
    """Hero: 도입 1문장 + 고유 문장만, 반복·프로세스 문구 제거."""
    clean_title = re.sub(r"[*_`]", "", (title or "")).strip().rstrip(".!?。")
    lead = f"이번 주 가장 먼저 짚을 주제는 **{title}**이에요."
    # Seed against lead/title so bare title echoes never re-enter the body.
    pool: list[str] = [lead, clean_title, f"{clean_title}."]
    for chunk, limit in (
        (problem, 2),
        (explanation, 3),
        (insight, 2),
    ):
        piece = unique_sentences(chunk, max_sentences=limit, against=pool)
        if piece:
            pool.extend([p.strip() for p in _SENT_SPLIT.split(piece) if p.strip()])
    body = " ".join(
        p for p in pool if p not in (lead, clean_title, f"{clean_title}.")
    ).strip()
    # Drop residual title-only fragments after densify
    kept: list[str] = []
    for part in [p.strip() for p in _SENT_SPLIT.split(body) if p.strip()]:
        bare = re.sub(r"[*_`]", "", part).strip().rstrip(".!?。")
        if bare == clean_title:
            continue
        if sentence_similar(part, lead, threshold=0.72):
            continue
        kept.append(part)
    body = unique_sentences(" ".join(kept), max_sentences=5)
    action = unique_sentences(apply, max_sentences=1, against=pool + [lead])
    if action:
        act = action.rstrip(".!?。")
        body = f"{body} 바로 쓸 액션: {act}.".strip()
    return f"{lead} {body}".strip()


def scrub_apply(text: str) -> str:
    """현장 적용 — 채널 배포 메모 제거, 실행 문장만."""
    t = scrub_phrase(text)
    # Drop trailing channel redistribution tips
    t = re.split(r"(?:글로벌 사례를|Tip:)", t, maxsplit=1)[0].strip(" .")
    return unique_sentences(t, max_sentences=3) or "우선순위 1개를 정해 이번 주 안에 실험하세요."


def fit_topic_for_subject(topic: str, template: str, max_chars: int) -> str:
    """제목 후보용 topic — 자연 경계에서 줄이고 mid-word … 잘림을 피함."""
    t = (topic or "").strip().rstrip(".")
    if "—" in t and len(t) > 24:
        left = t.split("—", 1)[0].strip()
        if len(left) >= 8:
            t = left
    probe = template.replace("{topic}", "§").replace("{stamp}", "YYYY-MM-DD")
    overhead = max(0, len(probe) - 1)
    budget = max(10, max_chars - overhead)
    if len(t) <= budget:
        return t
    cut = t[:budget]
    for sep in (" ", "—", "·", "-", "/"):
        if sep in cut:
            cand = cut.rsplit(sep, 1)[0].strip()
            if len(cand) >= 8:
                return cand
    return cut.rstrip(" ,·/—")


def fix_subject_topic(topic: str, template: str, *, stamp: str = "") -> str:
    """'{topic} 실무 체크리스트' 같은 중복 접미 방지."""
    t = (topic or "").strip().rstrip(".")
    tpl = template
    if t.endswith("실무"):
        tpl = tpl.replace("{topic} 실무", "{topic}")
    return tpl.format(topic=t, stamp=stamp)
