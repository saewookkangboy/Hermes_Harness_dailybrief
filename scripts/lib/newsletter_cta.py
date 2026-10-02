"""뉴스레터 CTA — 실제 HTTPS 단일 링크 (결정적)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lib.content_quality import Insight
from lib.newsletter_select import display_title_for

WORKDIR = Path(__file__).resolve().parents[2]
PLACEHOLDER_RE = re.compile(
    r"통합 컨텍스트|전문을 확인|블로그·Notion|href=['\"]?#['\"]?|^#$",
    re.I,
)


@dataclass
class Cta:
    label: str
    url: str
    reason: str

    @property
    def ok(self) -> bool:
        return bool(self.url.startswith("https://")) and not PLACEHOLDER_RE.search(self.url)


def _blog_candidate_url(stamp: str, cfg: dict | None = None) -> str:
    """설정된 공개 베이스가 있으면 블로그 permalink, 없으면 빈 문자열."""
    c = cfg or {}
    delivery = c.get("delivery") or {}
    base = str(delivery.get("public_blog_base") or "").rstrip("/")
    if not base.startswith("https://"):
        return ""
    blogs = sorted((WORKDIR / "content" / "blog").glob(f"{stamp}_blog_*.html"))
    if not blogs:
        return ""
    return f"{base}/{blogs[-1].name}"


def resolve_cta_url(ins: Insight | None, stamp: str, cfg: dict | None = None) -> tuple[str, str]:
    """우선순위: public blog → insight https → (실패 시 빈 값)."""
    blog = _blog_candidate_url(stamp, cfg)
    if blog:
        return blog, "public_blog"
    if ins and (ins.url or "").startswith("https://"):
        return ins.url.strip(), "insight_source"
    return "", "missing"


def build_cta(ins: Insight | None, stamp: str, cfg: dict | None = None) -> Cta:
    topic = display_title_for(ins, cfg) if ins else "이번 주 실무"
    url, reason = resolve_cta_url(ins, stamp, cfg)
    label = f"{topic} 원문·근거 보기"
    return Cta(label=label, url=url, reason=reason)


def render_cta_markdown(cta: Cta, topic: str) -> str:
    if not cta.ok:
        return "\n".join(
            [
                "## 이번 주 실습 1가지 (CTA)",
                "",
                f"팀 반복 업무 3개를 적고, 그중 1개만 **{topic}** 관점으로 자동화 후보를 골라보세요.",
                "",
                "→ 댓글/회신으로 공유해 주시면 다음 호에 사례를 반영할게요.",
                "",
                "**링크는 여기 1곳만:** 발행 전 블로그·Notion permalink(https)를 연결하세요.",
            ]
        )
    return "\n".join(
        [
            "## 이번 주 실습 1가지 (CTA)",
            "",
            f"팀 반복 업무 3개를 적고, 그중 1개만 **{topic}** 관점으로 자동화 후보를 골라보세요.",
            "",
            "→ 댓글/회신으로 공유해 주시면 다음 호에 사례를 반영할게요.",
            "",
            f"**링크는 여기 1곳만:** [{cta.label}]({cta.url})",
        ]
    )


def render_cta_html(cta: Cta, topic: str) -> str:
    import html as html_lib

    t = html_lib.escape(topic)
    if not cta.ok:
        return (
            f"<p style='margin:0 0 12px;'>팀 반복 업무 3개를 적고, 그중 1개만 "
            f"<strong>{t}</strong> 관점으로 자동화 후보를 골라보세요.</p>"
            "<p style='margin:0;color:#B00020;'>CTA URL 미확정 — 발행 전 https 링크 필요</p>"
        )
    return (
        f"<p style='margin:0 0 12px;'>팀 반복 업무 3개를 적고, 그중 1개만 "
        f"<strong>{t}</strong> 관점으로 자동화 후보를 골라보세요.</p>"
        f"<p style='margin:0;'><a href='{html_lib.escape(cta.url)}' "
        f"style='color:#E60012;font-weight:600;'>→ {html_lib.escape(cta.label)}</a></p>"
    )


def cta_failures(text: str) -> list[str]:
    fails: list[str] = []
    zone = text
    if "## 이번 주 실습 1가지" in text:
        zone = text.split("## 이번 주 실습 1가지", 1)[1].split("## 다음 호", 1)[0]
    if PLACEHOLDER_RE.search(zone):
        fails.append("cta_placeholder")
    if "href='#'" in zone or 'href="#"' in zone:
        fails.append("cta_hash_link")
    if "https://" not in zone and "발행 전" not in zone:
        fails.append("cta_missing_https")
    return fails
