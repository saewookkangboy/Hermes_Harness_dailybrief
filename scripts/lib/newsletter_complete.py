"""뉴스레터 완성도·잘림 감사 — validate · eval 게이트."""
from __future__ import annotations

import re

# 문장·단어 중간 생략 부호 (허용: 문장 끝 …)
_MID_ELLIPSIS = re.compile(r"[^\s.!?。…」』\"']\u2026")
_GARBAGE_TITLE = re.compile(
    r"(관련 AI·마케팅…|관련 AI·마케팅 신호입니다\.?$|will put ads in|OpenAI News OpenAI|—\s*실무\s*—)"
)


def _section(text: str, heading: str) -> str:
    """heading prefix 매칭 (예: ## 3분 읽기 — Top 3)."""
    lines = text.splitlines()
    start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith(heading):
            start = i
            break
    if start < 0:
        return ""
    out: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() == "---":
            break
        if line.startswith("## ") and not line.strip().startswith(heading):
            break
        out.append(line)
    return "\n".join(out)


def audit_newsletter_md(text: str) -> list[str]:
    """잘림·미완성 패턴 탐지. 빈 리스트 = PASS."""
    issues: list[str] = []

    for label, chunk in (
        ("프리헤더", _section(text, "**프리헤더")),
        ("TLDR", _section(text, "## 30초 TLDR")),
        ("Hero", _section(text, "## 오늘의 1가지")),
        ("모듈", _section(text, "## 3분 읽기")),
        ("CTA", _section(text, "## 이번 주 실습")),
    ):
        if not chunk:
            continue
        if _MID_ELLIPSIS.search(chunk):
            issues.append(f"{label}: 문장 중간 '…' 생략")
        if "+…" in chunk or " +…" in chunk:
            issues.append(f"{label}: 불완전 접미사 '+…'")

    tldr = _section(text, "## 30초 TLDR")
    bullets = [ln for ln in tldr.splitlines() if ln.strip().startswith("- ")]
    if len(bullets) < 3:
        issues.append(f"TLDR 불릿 부족: {len(bullets)}/3")

    mod_body = _section(text, "## 3분 읽기")
    modules = re.findall(r"^### \d+\.", mod_body, re.M)
    if len(modules) < 3:
        issues.append(f"Insight 모듈 부족: {len(modules)}/3")

    for i, block in enumerate(re.split(r"^### \d+\.", mod_body, flags=re.M)[1:], 1):
        if "https://" not in block and "http://" not in block:
            issues.append(f"모듈 {i}: 출처 URL 없음")
        apply_m = re.search(r"\*\*현장 적용:\*\*\s*(.+)", block)
        if apply_m:
            apply = apply_m.group(1).strip()
            if len(apply) < 24:
                issues.append(f"모듈 {i}: 현장 적용 너무 짧음 ({len(apply)}자)")
            if apply.endswith("…") or apply.endswith("..."):
                issues.append(f"모듈 {i}: 현장 적용 미완결 종료")

    for m in re.finditer(r"\*\*([^*]+)\*\*", tldr):
        title = m.group(1).strip()
        if _GARBAGE_TITLE.search(title) or title.endswith("…"):
            issues.append(f"TLDR 제목 품질: {title[:40]}")

    hero = _section(text, "## 오늘의 1가지")
    if hero and not re.search(r"[.!?。]$", hero.strip().splitlines()[-1].strip()):
        last = [ln for ln in hero.splitlines() if ln.strip() and not ln.startswith("*")]
        if last and not re.search(r"[.!?。]$", last[-1].strip()):
            issues.append("Hero: 마지막 문장 미완결")

    return issues
