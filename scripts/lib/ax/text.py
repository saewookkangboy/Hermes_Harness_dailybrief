"""텍스트 정리 — 생략부호 절단·AI-tell 제거·문장 단위 자르기."""
from __future__ import annotations

import re

_ELLIPSIS = re.compile(r"\s*(\.{3,}|…)\s*")
_WS = re.compile(r"\s+")
_TELL_REPLACEMENTS = {
    "혁신적인": "새로운",
    "획기적인": "큰",
    "결론적으로": "",
    "요약하면": "",
    "정리하면": "",
    "시사하는 바": "의미",
    "본질적으로": "",
    "핵심적으로": "",
}
_SENTENCE_END = re.compile(r"[.!?。](?=\s|$)")
_REL_DATE_PREFIX = re.compile(
    r"^(\d+\s+(seconds?|minutes?|hours?|days?|weeks?|months?)\s+ago"
    r"|\d+\s*(분|시간|일|주|개월)\s*전"
    r"|[A-Z][a-z]{2,8}\.? \d{1,2}, \d{4}"
    r"|\d{4}[.\-/]\s?\d{1,2}[.\-/]\s?\d{1,2}\.?)\s*[·\-—]\s*"
)


def sanitize(text: str) -> str:
    out = _REL_DATE_PREFIX.sub("", _ELLIPSIS.sub(" ", text or "").lstrip())
    for tell, repl in _TELL_REPLACEMENTS.items():
        out = out.replace(tell, repl)
    out = out.replace("|", "/")
    return _WS.sub(" ", out).strip()


def clip(text: str, max_chars: int) -> str:
    """max_chars 안에서 마지막 문장 끝(없으면 단어 경계)까지 자르고 마침표로 닫는다."""
    body = sanitize(text)
    if len(body) <= max_chars:
        return _close(body)
    window = body[:max_chars]
    ends = list(_SENTENCE_END.finditer(window))
    if ends and ends[-1].end() >= max_chars * 0.5:
        return window[: ends[-1].end()].strip()
    cut = window.rsplit(" ", 1)[0] if " " in window else window
    return _close(cut.rstrip(",;:-— "))


def has_batchim(word: str) -> bool:
    for ch in reversed(word.strip()):
        if "가" <= ch <= "힣":
            return (ord(ch) - 0xAC00) % 28 != 0
        if ch.isalnum():
            return False
    return False


def ieyo(word: str) -> str:
    """'정의·개념' → '정의·개념이에요', '뉴스' → '뉴스예요'."""
    return f"{word}{'이에요' if has_batchim(word) else '예요'}"


def euro(word: str) -> str:
    """'대량 생성' → '대량 생성으로', '탐지' → '탐지로', '파일' → '파일로'."""
    for ch in reversed(word.strip()):
        if "가" <= ch <= "힣":
            jong = (ord(ch) - 0xAC00) % 28
            return f"{word}{'으로' if jong not in (0, 8) else '로'}"
        if ch.isalnum():
            break
    return f"{word}로"


def eulreul(word: str) -> str:
    return f"{word}{'을' if has_batchim(word) else '를'}"


def eunneun(word: str) -> str:
    """'규제 환경' → '규제 환경은', '보급' → '보급은', '속도' → '속도는'."""
    return f"{word}{'은' if has_batchim(word) else '는'}"


def _close(text: str) -> str:
    text = text.strip().rstrip(",;:-— ")
    if not text:
        return text
    if text[-1] in ".!?。":
        return text
    return text + "."
