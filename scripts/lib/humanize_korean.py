"""Deterministic Korean humanization — im-not-ai AI-tell removal + casual 해요체.

Reference: https://github.com/epoko77-ai/im-not-ai
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class HumanizeResult:
    text: str
    change_count: int = 0
    patterns: list[str] = field(default_factory=list)


# AI-tell removal only (no formalization)
_AI_TELL_REPLACEMENTS: list[tuple[str, str, str]] = [
    (r"결론적으로[,，]?\s*", "", "D-1"),
    (r"요약하면[,，]?\s*", "", "D-1"),
    (r"정리하면[,，]?\s*", "", "D-1"),
    (r"시사하는 바가 크다\.?", "의미가 커요.", "D-2"),
    (r"주목할 만하다\.?", "", "D-2"),
    (r"본질적으로[,，]?\s*", "", "D-3"),
    (r"핵심적으로[,，]?\s*", "", "D-3"),
    (r"혁신적인", "새로운", "D-4"),
    (r"획기적인", "", "D-4"),
    (r"파격적인", "", "D-4"),
    (r"를 통해\s", "로 ", "A-2"),
    (r"을 통해\s", "로 ", "A-2"),
    (r"에 있어서\s", "에서 ", "A-3"),
    (r"에 있어\s", "에서 ", "A-3"),
    (r"에 의해\s", "가 ", "A-9"),
    (r"에 의하여\s", "가 ", "A-9"),
    (r"에 대해서\s", "에 대해 ", "A-1"),
    (r"와 관련하여\s", "와 관련해 ", "A-5"),
    (r"에 기반하여\s", "을 바탕으로 ", "A-6"),
    (r"가지고 있다", "있어요", "A-7"),
    (r"가지고 있습니다", "있어요", "A-7"),
    (r"되어진다", "돼요", "A-8"),
    (r"되어집니다", "돼요", "A-8"),
    (r"^또한[,，]?\s*", "", "H-1"),
    (r"^따라서[,，]?\s*", "", "H-1"),
    (r"^나아가[,，]?\s*", "", "H-1"),
    (r"^아울러[,，]?\s*", "", "H-1"),
    (r"^게다가[,，]?\s*", "", "H-1"),
    (r"^더욱이[,，]?\s*", "", "H-1"),
    (r"^즉[,，]?\s*", "", "H-4"),
    (r"이 점에서[,，]?\s*", "", "H-3"),
    (r"이 관점에서[,，]?\s*", "", "H-3"),
    (r"라는 점에서", " 측면에서", "I-2"),
    (r"다음과 같(?:아요|습니다|다)\.?", "", "C-struct"),
    (r"첫째[,，]", "우선", "C-struct"),
    (r"둘째[,，]", "그다음", "C-struct"),
    (r"셋째[,，]", "마지막으로", "C-struct"),
    (r"할 수 있을 것으로 보인다", " 가능성이 있어요", "G-2"),
    (r"인 듯하다", " 같아요", "G-2"),
]

# Formal/plain → casual 해요체
_HAEYO_REPLACEMENTS: list[tuple[str, str]] = [
    (r"활용하라\.?", "활용해 보세요."),
    (r"확장하면 된다\.?", "확장하면 돼요."),
    (r"수요에 맞는다\.?", "수요에 잘 맞아요."),
    (r"필수입니다\.?", "꼭 필요해요."),
    (r"강화하세요\.?", "강화해 보세요."),
    (r"이어지고 있다\.?", "이어지고 있어요."),
    (r"진화 중이다\.?", "빠르게 바뀌고 있어요."),
    (r"재편한다\.?", "재편하고 있어요."),
    (r"차별점이 된다\.?", "차별점이 돼요."),
    (r"신호다\.?", "신호예요."),
    (r"과제다\.?", "과제예요."),
    (r"좋다\.?", "좋아요."),
    (r"읽힌다\.?", "읽혀요."),
    (r"정리했다\.?", "정리했어요."),
    (r"요구된다\.?", "요구돼요."),
    (r"갈린다\.?", "갈려요."),
    (r"달라진다\.?", "달라져요."),
    (r"올라온다\.?", "올라와요."),
    (r"의미 있다\.?", "의미 있어요."),
    (r"적어 보라\.?", "적어 보세요."),
    (r"있는가\?", "있으세요?"),
    (r"구조화한다\.?", "구조화해요."),
    (r"재가공한다\.?", "재가공해요."),
    (r"확보한다\.?", "확보해요."),
    (r"연결한다\.?", "연결해요."),
    (r"수집", "모아요"),
    (r"입니다\.?", "이에요."),
    (r"습니다\.?", "어요."),
    (r"됩니다\.?", "돼요."),
    (r"합니다\.?", "해요."),
    (r"이다\.?", "이에요."),
    (r"한다\.?", "해요."),
    (r"된다\.?", "돼요."),
    (r"있다\.?", "있어요."),
    (r"했다\.?", "했어요."),
    (r"(\?)($)", r"\1"),  # no-op anchor for question marks
]

_URL_RE = re.compile(r"https?://[^\s\)]+")


def _protect_urls(text: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}

    def repl(m: re.Match[str]) -> str:
        key = f"__URL_{len(placeholders)}__"
        placeholders[key] = m.group(0)
        return key

    return _URL_RE.sub(repl, text), placeholders


def _restore_urls(text: str, placeholders: dict[str, str]) -> str:
    for key, url in placeholders.items():
        text = text.replace(key, url)
    return text


def apply_formal(text: str) -> HumanizeResult:
    """Convert casual/plain endings to formal ~합니다 / ~입니다."""
    protected, urls = _protect_urls(text)
    formal_rules: list[tuple[str, str]] = [
        (r"해 보세요\.?", "하십시오."),
        (r"해보세요\.?", "하십시오."),
        (r"적어 보세요\.?", "적어 보십시오."),
        (r"확장해 보세요\.?", "확장해 보십시오."),
        (r"강화해 보세요\.?", "강화해 보십시오."),
        (r"있으세요\?", "있습니까?"),
        (r"해요\.?", "합니다."),
        (r"돼요\.?", "됩니다."),
        (r"있어요\.?", "있습니다."),
        (r"이에요\.?", "입니다."),
        (r"예요\.?", "입니다."),
        (r"같아요\.?", "같습니다."),
        (r"읽혀요\.?", "읽힙니다."),
        (r"요구돼요\.?", "요구됩니다."),
        (r"달라져요\.?", "달라집니다."),
        (r"올라와요\.?", "올라옵니다."),
        (r"바뀌고 있어요\.?", "바뀌고 있습니다."),
        (r"이어지고 있어요\.?", "이어지고 있습니다."),
        (r"재편하고 있어요\.?", "재편하고 있습니다."),
        (r"모아요", "수집합니다"),
    ]
    change_count = 0
    result = protected
    for pattern, repl in formal_rules:
        new_result, n = re.subn(pattern, repl, result)
        if n:
            change_count += n
            result = new_result
    result = _restore_urls(result, urls)
    return HumanizeResult(text=result.strip(), change_count=change_count, patterns=["formal"])


def apply_haeyo(text: str) -> HumanizeResult:
    """Convert formal/plain endings to casual 해요체."""
    protected, urls = _protect_urls(text)
    change_count = 0
    result = protected
    for pattern, repl in _HAEYO_REPLACEMENTS:
        if pattern == r"(\?)($)":
            continue
        new_result, n = re.subn(pattern, repl, result)
        if n:
            change_count += n
            result = new_result
    result = _restore_urls(result, urls)
    return HumanizeResult(text=result.strip(), change_count=change_count, patterns=["haeyo"])


def humanize(text: str, *, genre: str = "blog") -> HumanizeResult:
    """Remove AI tells, then apply casual 해요체 for blog/linkedin."""
    if not text or not text.strip():
        return HumanizeResult(text=text)

    protected, urls = _protect_urls(text)
    change_count = 0
    patterns: list[str] = []
    result = protected

    for pattern, repl, rule_id in _AI_TELL_REPLACEMENTS:
        new_result, n = re.subn(pattern, repl, result, flags=re.MULTILINE)
        if n:
            change_count += n
            if rule_id not in patterns:
                patterns.append(rule_id)
            result = new_result

    result, n = re.subn(r"([가-힣]+(?:고|며|지만|면서|아서|어서)),\s", r"\1 ", result)
    if n:
        change_count += n
        patterns.append("C-11")

    result = re.sub(r"  +", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = _restore_urls(result, urls)

    if genre == "blog":
        formal = apply_formal(result)
        result = formal.text
        change_count += formal.change_count
        if formal.change_count and "formal" not in patterns:
            patterns.append("formal")
    elif genre in ("linkedin", "instagram"):
        haeyo = apply_haeyo(result)
        result = haeyo.text
        change_count += haeyo.change_count
        if haeyo.change_count and "haeyo" not in patterns:
            patterns.append("haeyo")

    return HumanizeResult(text=result.strip(), change_count=change_count, patterns=patterns)


def humanize_linkedin_post(text: str) -> HumanizeResult:
    """LinkedIn: casual 해요체 + 1인칭."""
    r = humanize(text, genre="linkedin")
    r.text = r.text.replace("공유해 주세요.", "공유해 주실 수 있을까요?")
    r.text = r.text.replace("주간 리서치를 돌리며", "주간 리서치 돌려보니")
    return r
