"""M1d Evidence Pack — 정규화·dedupe·렌즈 태깅·relevance·신뢰도·교차확인."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from lib.ax.config import load_config
from lib.ax.text import clip
from lib.ax.topic_spec import TopicSpec, relevance_score

_WORD = re.compile(r"[a-z][a-z0-9\-]{3,}|[가-힣]{2,}")
_TRACKING = re.compile(r"^(utm_|fbclid|gclid|ref$|mc_)")
_GENERIC = {
    "with", "from", "that", "this", "your", "what", "will", "have", "into", "about", "more", "news",
    "says", "said", "their", "they", "than", "over", "after", "using", "guide", "best", "top", "2025",
    "2026", "2027", "today", "year", "new", "how", "why", "the", "and", "for", "are", "can",
}
API_LENS = {"github": "tech_tools", "arxiv": "future_signals"}


@dataclass
class Evidence:
    id: str
    lens: str
    lenses: list[str]
    source_type: str
    query: str
    title: str
    url: str
    domain: str
    snippet: str
    published: str
    relevance: float
    freshness: float
    corroboration: int = 0
    confidence: float = 0.0
    is_new: bool = True
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_label(self) -> str:
        if self.confidence >= 0.7:
            return "높음"
        if self.confidence >= 0.5:
            return "보통"
        return "낮음"


@dataclass
class EvidencePack:
    topic: str
    stamp: str
    items: list[Evidence]
    raw_count: int
    relevant_count: int
    query_count: int
    errors: list[str] = field(default_factory=list)

    @property
    def raw_ratio(self) -> float:
        return round(self.relevant_count / self.raw_count, 3) if self.raw_count else 0.0

    def lens_counts(self) -> dict[str, int]:
        c: Counter[str] = Counter()
        for ev in self.items:
            for lens in ev.lenses:
                c[lens] += 1
        return dict(c)

    def source_type_counts(self) -> dict[str, int]:
        return dict(Counter(ev.source_type for ev in self.items))

    def domains(self) -> set[str]:
        return {ev.domain for ev in self.items}

    def by_lens(self, lens: str) -> list[Evidence]:
        return [ev for ev in self.items if lens in ev.lenses]

    def by_source(self, source: str) -> list[Evidence]:
        return [ev for ev in self.items if ev.source_type == source]

    def new_count(self) -> int:
        return sum(1 for ev in self.items if ev.is_new)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "stamp": self.stamp,
            "raw_count": self.raw_count,
            "relevant_count": self.relevant_count,
            "raw_ratio": self.raw_ratio,
            "query_count": self.query_count,
            "lens_counts": self.lens_counts(),
            "source_type_counts": self.source_type_counts(),
            "domain_count": len(self.domains()),
            "new_count": self.new_count(),
            "errors": self.errors,
            "items": [asdict(ev) for ev in self.items],
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidencePack":
        return cls(
            topic=data["topic"],
            stamp=data["stamp"],
            items=[Evidence(**ev) for ev in data.get("items") or []],
            raw_count=int(data.get("raw_count") or 0),
            relevant_count=int(data.get("relevant_count") or 0),
            query_count=int(data.get("query_count") or 0),
            errors=list(data.get("errors") or []),
        )


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING.match(k)])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), path, query, ""))


def url_domain(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def parse_date(value: str) -> date | None:
    if not value:
        return None
    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text).date()
    except (TypeError, ValueError):
        pass
    m = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def freshness_score(published: str, today: date, full_days: int = 30, zero_days: int = 365) -> float:
    d = parse_date(published)
    if d is None:
        return 0.5
    age = max(0, (today - d).days)
    if age <= full_days:
        return 1.0
    if age >= zero_days:
        return 0.0
    return round(1 - (age - full_days) / (zero_days - full_days), 3)


def term_hits(terms: list[str], low: str) -> int:
    hits = 0
    for term in terms:
        t = term.lower()
        if t.isascii():
            hits += bool(re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", low))
        else:
            hits += t in low
    return hits


def tag_lenses(primary: str, source_type: str, text: str, cfg: dict[str, Any]) -> list[str]:
    """첫 원소가 대표 렌즈. 쿼리 렌즈 용어가 본문에 없으면 가장 많이 맞는 렌즈로 재지정."""
    low = text.lower()
    hits = {name: term_hits(lcfg.get("tag_terms") or [], low) for name, lcfg in (cfg.get("lenses") or {}).items()}
    api_lens = API_LENS.get(source_type)
    if api_lens:
        primary = api_lens if source_type == "github" else primary
    elif hits.get(primary, 0) == 0 and hits:
        best = max(hits, key=lambda k: (hits[k], k == primary))
        if hits[best] > 0:
            primary = best
    lenses = [primary]
    if api_lens and api_lens not in lenses:
        lenses.append(api_lens)
    lenses.extend(name for name, n in hits.items() if n > 0 and name not in lenses)
    return lenses


def significant_terms(text: str, spec: TopicSpec) -> set[str]:
    topic_words = {w for group in spec.core_groups for v in group for w in v.lower().split()}
    return {w for w in _WORD.findall(text.lower()) if w not in _GENERIC and w not in topic_words}


def _evidence_id(url: str) -> str:
    return "ev-" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def build_evidence_pack(
    spec: TopicSpec,
    rows: list[dict[str, Any]],
    *,
    query_count: int,
    errors: list[str] | None = None,
    seen_urls: set[str] | None = None,
    cfg: dict[str, Any] | None = None,
) -> EvidencePack:
    cfg = cfg or load_config()
    ecfg = cfg.get("evidence") or {}
    threshold = float(ecfg.get("relevance_threshold", 0.5))
    weights = cfg.get("source_weights") or {}
    today = date.fromisoformat(spec.stamp)
    seen_urls = seen_urls or set()

    unique: dict[str, dict[str, Any]] = {}
    title_keys: set[str] = set()
    for row in rows:
        url = row.get("url") or ""
        if not url.startswith("http"):
            continue
        key = normalize_url(url)
        title_key = re.sub(r"[^a-z0-9가-힣]", "", (row.get("title") or "").lower())[:80]
        if key in unique or (title_key and title_key in title_keys):
            continue
        unique[key] = dict(row, url=key)
        if title_key:
            title_keys.add(title_key)

    items: list[Evidence] = []
    for url, row in unique.items():
        meta = row.get("meta") or {}
        blob = " ".join(
            [row.get("title") or "", row.get("snippet") or "", " ".join(meta.get("topics") or [])]
        )
        rel = relevance_score(spec, blob)
        if rel < threshold:
            continue
        pub = parse_date(row.get("published") or "")
        lenses = tag_lenses(row.get("lens") or "definition", row.get("source_type") or "web", blob, cfg)
        items.append(
            Evidence(
                id=_evidence_id(url),
                lens=lenses[0],
                lenses=lenses,
                source_type=row.get("source_type") or "web",
                query=row.get("query") or "",
                title=clip(row.get("title") or "(제목 없음)", 140).rstrip("."),
                url=url,
                domain=url_domain(url),
                snippet=clip(row.get("snippet") or "", 280),
                published=pub.isoformat() if pub else "",
                relevance=rel,
                freshness=freshness_score(
                    row.get("published") or "",
                    today,
                    int(ecfg.get("freshness_days_full", 30)),
                    int(ecfg.get("freshness_days_zero", 365)),
                ),
                is_new=url not in seen_urls,
                meta=meta,
            )
        )

    terms = {ev.id: significant_terms(f"{ev.title} {ev.snippet}", spec) for ev in items}
    for ev in items:
        peers = {
            other.domain
            for other in items
            if other.id != ev.id and other.domain != ev.domain and len(terms[ev.id] & terms[other.id]) >= 2
        }
        ev.corroboration = len(peers)
        ev.confidence = round(
            0.45 * float(weights.get(ev.source_type, 0.6))
            + 0.25 * ev.freshness
            + 0.2 * ev.relevance
            + 0.1 * min(1.0, ev.corroboration / 2),
            3,
        )

    items.sort(key=lambda e: (e.confidence, e.is_new, e.relevance), reverse=True)
    items = items[: int(ecfg.get("max_items", 40))]
    return EvidencePack(
        topic=spec.keyword,
        stamp=spec.stamp,
        items=items,
        raw_count=len(unique),
        relevant_count=len(items),
        query_count=query_count,
        errors=list(errors or []),
    )


def select_top(pack: EvidencePack, n: int = 7) -> list[Evidence]:
    """렌즈 라운드로빈으로 다양성 확보 (렌즈 내부는 신뢰도 순)."""
    buckets: dict[str, list[Evidence]] = {}
    for ev in pack.items:
        buckets.setdefault(ev.lens, []).append(ev)
    order = sorted(buckets, key=lambda k: buckets[k][0].confidence, reverse=True)
    picked: list[Evidence] = []
    while len(picked) < n and any(buckets.values()):
        for lens in order:
            if buckets[lens] and len(picked) < n:
                picked.append(buckets[lens].pop(0))
    return picked
