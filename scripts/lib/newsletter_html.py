"""뉴스레터 HTML 이메일 — 모바일 단일 컬럼 · 모듈형."""
from __future__ import annotations

import html
import re
from pathlib import Path

from lib.common import read_template, truncate
from lib.content_quality import Insight
from lib.newsletter_subject import SubjectScore

WORKDIR = Path.home() / "hermes-content-studio"
TEMPLATE_PATH = WORKDIR / "templates" / "email" / "newsletter.html"


def _md_inline(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return t


def _section_block(title: str, body_html: str) -> str:
    return f"""
<tr><td style="padding:24px 20px 8px;font-family:Pretendard,-apple-system,sans-serif;">
  <h2 style="margin:0;font-size:18px;color:#111111;">{html.escape(title)}</h2>
</td></tr>
<tr><td style="padding:0 20px 16px;font-family:Pretendard,-apple-system,sans-serif;font-size:15px;line-height:1.6;color:#333333;">
  {body_html}
</td></tr>"""


def build_newsletter_html(
    stamp: str,
    *,
    preheader: str,
    winner: SubjectScore | None,
    tldr: list[str],
    hero: str,
    insights: list[Insight],
    grab_bag: str,
    cta_html: str,
    teaser: str,
) -> str:
    tpl = read_template(str(TEMPLATE_PATH.relative_to(WORKDIR)))
    subject = winner.text if winner else f"B2B AI 주간 — {stamp}"
    pre = truncate(preheader, 40)

    tldr_li = "".join(f"<li style='margin-bottom:8px;'>{_md_inline(b)}</li>" for b in tldr)
    tldr_html = f"<ul style='margin:0;padding-left:20px;'>{tldr_li}</ul>"

    modules_html = ""
    for i, ins in enumerate(insights[:3], 1):
        mod = (
            f"<p style='margin:0 0 8px;'><strong>{html.escape(ins.korean_title)}</strong></p>"
            f"<p style='margin:0 0 8px;'>{html.escape(truncate(ins.korean_summary, 160))}</p>"
            f"<p style='margin:0;font-size:13px;color:#666;'>현장 적용: {html.escape(truncate(ins.marketer_view or '', 90))}</p>"
        )
        modules_html += _section_block(f"{i}. Top 인사이트", mod)

    body = (
        _section_block("30초 TLDR", tldr_html)
        + _section_block("오늘의 1가지", f"<p style='margin:0;'>{_md_inline(hero)}</p>")
        + modules_html
        + _section_block("한 줄 데이터", f"<p style='margin:0;'>{_md_inline(grab_bag)}</p>")
        + _section_block("이번 주 실습", cta_html)
        + _section_block("다음 호", f"<p style='margin:0;'>{_md_inline(teaser)}</p>")
    )

    score_note = ""
    if winner:
        score_note = f"권장 제목 score {winner.score} · {', '.join(winner.reasons[:2])}"

    return (
        tpl.replace("{{PREHEADER}}", html.escape(pre))
        .replace("{{SUBJECT}}", html.escape(subject))
        .replace("{{STAMP}}", html.escape(stamp))
        .replace("{{SCORE_NOTE}}", html.escape(score_note))
        .replace("{{BODY_MODULES}}", body)
    )
