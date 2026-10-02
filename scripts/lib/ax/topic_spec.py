"""M1a Topic Framing — 임의 키워드 → topic_spec (도메인·의도·핵심어·동의어)."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from lib.ax.config import load_config

_TOKEN_SPLIT = re.compile(r"[\s,/|·+]+")
_ASCII = re.compile(r"^[a-z0-9][a-z0-9.\-+]*$")
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


@dataclass
class TopicSpec:
    keyword: str
    slug: str
    stamp: str
    tokens: list[str]
    en_tokens: list[str]
    ko_query: str
    en_query: str
    core_groups: list[list[str]]
    domain: str
    domain_label: str
    secondary_domains: list[str] = field(default_factory=list)
    intent: str = "trend"
    intent_label: str = ""
    audience: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopicSpec":
        return cls(**data)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _split_compound(token: str, dictionary: dict[str, str]) -> list[str]:
    """'숏폼커머스' → ['숏폼', '커머스'] (사전 최장 일치, 미등록 구간은 그대로)."""
    if token in dictionary or _ASCII.match(token):
        return [token]
    keys = sorted(dictionary, key=len, reverse=True)
    parts: list[str] = []
    buf = ""
    i = 0
    while i < len(token):
        match = next((k for k in keys if token.startswith(k, i)), None)
        if match:
            if buf:
                parts.append(buf)
                buf = ""
            parts.append(match)
            i += len(match)
        else:
            buf += token[i]
            i += 1
    if buf:
        parts.append(buf)
    if len(parts) > 1 and any(p not in dictionary for p in parts if len(p) < 2):
        return [token]
    return parts


def _intent_words(cfg: dict[str, Any], dictionary: dict[str, str]) -> set[str]:
    """의도 표현(도입·전략·비교…)은 주제어가 아니므로 토큰에서 분리. 사전 등재어(추천 등)는 유지."""
    return {
        t.lower()
        for terms in (cfg.get("intents") or {}).values()
        for t in terms
        if " " not in t and not t.isascii() and t not in dictionary
    }


def tokenize(keyword: str, cfg: dict[str, Any] | None = None) -> list[str]:
    cfg = cfg or load_config()
    dictionary: dict[str, str] = cfg.get("synonyms_ko_en") or {}
    stop = {s.lower() for s in cfg.get("stopwords") or []}
    intent_words = _intent_words(cfg, dictionary)
    tokens: list[str] = []
    for raw in _TOKEN_SPLIT.split(keyword.strip().lower()):
        raw = raw.strip("\"'()[]{}?!.")
        if not raw:
            continue
        for part in _split_compound(raw, dictionary):
            if part and part not in stop and part not in tokens:
                tokens.append(part)
    topical = [t for t in tokens if t not in intent_words]
    return topical or tokens


def _variants(token: str, en: str) -> list[str]:
    out = [token]
    if en and en.lower() != token:
        low = en.lower()
        out.extend([low, low.replace("-", " "), low.replace(" ", "")])
        head = low.split(" ")[0]
        if "-" in head:
            out.append(head)
    return list(dict.fromkeys(v for v in out if v))


def _detect_domain(text: str, cfg: dict[str, Any]) -> tuple[str, list[str]]:
    scores: list[tuple[int, int, str]] = []
    for order, (name, spec) in enumerate((cfg.get("domains") or {}).items()):
        hits = sum(1 for term in spec.get("terms") or [] if _contains(text, term.lower()))
        if hits:
            scores.append((hits, -order, name))
    if not scores:
        return cfg.get("default_domain", "general_marketing"), []
    scores.sort(reverse=True)
    ranked = [name for _, _, name in scores]
    if ranked[0] == "ai_tech" and len(ranked) > 1:
        ranked = ranked[1:] + ["ai_tech"]
    return ranked[0], ranked[1:]


def _detect_intent(text: str, cfg: dict[str, Any]) -> str:
    for name, terms in (cfg.get("intents") or {}).items():
        if any(_contains(text, t.lower()) for t in terms):
            return name
    return cfg.get("default_intent", "trend")


def _contains(text: str, term: str) -> bool:
    if _ASCII.match(term.replace(" ", "")) and len(term) <= 4:
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
    return term in text


def make_slug(tokens: list[str], en_tokens: list[str], acronyms: dict[str, str] | None = None) -> str:
    acronyms = acronyms or {}
    parts = [tok if tok in acronyms else (en or tok) for tok, en in zip(tokens, en_tokens)]
    slug = _SLUG_STRIP.sub("-", "-".join(parts).lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)[:48].rstrip("-")
    if slug:
        return slug
    return "topic-" + hashlib.sha1("".join(tokens).encode("utf-8")).hexdigest()[:8]


def _en_query(keyword: str, tokens: list[str], en_tokens: list[str], acronyms: dict[str, str]) -> str:
    if re.fullmatch(r"[a-z0-9 .\-+]+", keyword.lower()):
        base = keyword
    else:
        parts = [tok if tok in acronyms else en for tok, en in zip(tokens, en_tokens) if en]
        base = " ".join(parts) or keyword
    words = base.lower().split()
    if words and all(w in acronyms for w in words):
        base = " ".join([base, *(acronyms[w] for w in words)])
    return base


def _ko_query(keyword: str, cfg: dict[str, Any]) -> str:
    stop = {s.lower() for s in cfg.get("stopwords") or []}
    words = [w for w in keyword.split() if w.lower() not in stop]
    return " ".join(words) or keyword


def build_topic_spec(keyword: str, stamp: str, cfg: dict[str, Any] | None = None) -> TopicSpec:
    cfg = cfg or load_config()
    keyword = re.sub(r"\s+", " ", keyword).strip()
    if not keyword:
        raise ValueError("keyword is empty")
    dictionary: dict[str, str] = cfg.get("synonyms_ko_en") or {}
    acronyms: dict[str, str] = cfg.get("acronyms") or {}
    tokens = tokenize(keyword, cfg) or [keyword.lower()]
    en_tokens = [dictionary.get(t) or acronyms.get(t) or (t if _ASCII.match(t) else "") for t in tokens]
    en_query = _en_query(keyword, tokens, en_tokens, acronyms)
    groups = [_variants(tok, en) for tok, en in zip(tokens, en_tokens)]
    detect_text = f"{keyword.lower()} {en_query.lower()}"
    domain, secondary = _detect_domain(detect_text, cfg)
    intent = _detect_intent(keyword.lower(), cfg)
    domain_label = ((cfg.get("domains") or {}).get(domain) or {}).get("label") or (
        cfg.get("domain_labels") or {}
    ).get(domain, domain)
    return TopicSpec(
        keyword=keyword,
        slug=make_slug(tokens, en_tokens, acronyms),
        stamp=stamp,
        tokens=tokens,
        en_tokens=en_tokens,
        ko_query=_ko_query(keyword, cfg),
        en_query=en_query,
        core_groups=groups,
        domain=domain,
        domain_label=domain_label,
        secondary_domains=secondary,
        intent=intent,
        intent_label=(cfg.get("intent_labels") or {}).get(intent, intent),
        audience=cfg.get("audience_default", "마케팅 실무자·팀 리드·AX 의사결정자"),
    )


def relevance_score(spec: TopicSpec, text: str) -> float:
    """핵심어 그룹 중 본문에 등장한 그룹 비율 (0~1)."""
    if not spec.core_groups:
        return 0.0
    cfg = load_config()
    acronyms: dict[str, str] = cfg.get("acronyms") or {}
    low = text.lower()
    solid = 0
    bare_acronyms: list[str] = []
    for group in spec.core_groups:
        matched = [v for v in group if _contains(low, v)]
        if not matched:
            continue
        if matched == [group[0]] and group[0] in acronyms:
            bare_acronyms.append(group[0])
        else:
            solid += 1
    hit = solid
    if bare_acronyms:
        if solid:
            hit += len(bare_acronyms)
        else:
            domain_terms = ((cfg.get("domains") or {}).get(spec.domain) or {}).get("terms") or []
            context = [t.lower() for t in [*(cfg.get("ambiguity_context") or []), *domain_terms]]
            if any(_contains(low, t) for t in context if t not in bare_acronyms):
                hit += len(bare_acronyms)
    return round(hit / len(spec.core_groups), 3)
