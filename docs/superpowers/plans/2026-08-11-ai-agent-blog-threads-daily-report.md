<p align="center">
  <img src="../../../assets/docs/plan-blog-threads.svg" width="100%" alt="Plan — AI Agent Blog + Threads implementation">
</p>

# AI Agent Daily Blog + Threads Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** M1 Brief를 AI Agent 렌즈로 전환하고, M2 블로그를 Velog형 일일 리포트(≤3,000자) + Threads 패키지 동반 산출로 교체한다 (LI/IG/NL 포맷 유지).

**Architecture:** `config/research-brief.yaml`로 수집 쿼리·pillars를 교체하고, 새 결정적 모듈 `scripts/lib/blog_daily_report.py`가 Brief insights → Velog MD/HTML + Threads MD를 조립한다. 기존 `build_blog_article_md` / `build_blog_html` / `build_notion_packages`는 이 모듈을 호출하도록 위임한다. validate 게이트는 FAQ/GEO blocking을 해제하고 신 스키마를 검사한다.

**Tech Stack:** Python 3, bash validate/eval, YAML config, deterministic assemble (no LLM required)

**Spec:** `docs/superpowers/specs/2026-08-11-ai-agent-blog-threads-daily-report-design.md`

## Global Constraints

- Brief SoT 유지: `content/research/{date}_brief.md`
- LinkedIn / Instagram / Newsletter **포맷·validate 변경 금지** (소재만 새 Brief)
- 결정적 조립 우선 — LLM으로 전체 재생성 금지
- 블로그 본문 공백 포함 ≤ 3,000자 (출처 URL 목록은 soft / 본문 카운트 제외)
- 톤: 블로그 `~습니다/합니다`; Threads는 숏폼 독립
- Threads는 `content/packages/{date}_threads.md`만 (정식 `content/threads/` 채널 승격은 비범위)
- Velog/Threads/ESP 자동 게시 금지 — Copy & Paste 산출물만
- Credentials / `~/.hermes/.env` 읽기·커밋 금지

## File Map

| File | Responsibility |
|------|----------------|
| `config/research-brief.yaml` | AI Agent pillars · search_queries · priority_queries |
| `config/content-quality.yaml` | blog longform · seo_aeo_geo blog flags |
| `config/content-orchestration.yaml` | threads package output path |
| `config/notion-archive.yaml` | optional threads glob |
| `scripts/lib/blog_daily_report.py` | **신규** DailyBlogReport + Threads 조립·본문 길이·헤더 상수 |
| `scripts/lib/content_quality.py` | `build_blog_article_md` / `build_blog_html` / `build_notion_packages` 위임 |
| `scripts/lib/longform_context.py` | 구 FAQ longform은 blog 경로에서 더 이상 호출하지 않음 (뉴스레터 helpers 유지) |
| `scripts/lib/blog_pipeline.py` | SEO/structure 체크리스트를 Velog형으로 갱신 |
| `scripts/lib/m4_coach.py` | blog coach traits를 신 게이트에 맞춤 |
| `templates/html/blog-post.html` | FAQ/GEO 강제 UI 완화, Article JSON-LD 중심 |
| `scripts/validate-output.sh` | blog / blog-article / threads-package 게이트 |
| `scripts/blog-daily-report-eval.sh` | **신규** 구조·분량·Threads soft 게이트 eval |
| `skills/channels/blog/SKILL.md` | 포맷 문서 |
| `.harness/progress.md` | 세션 진행 |

---

### Task 1: M1 Research lens → AI Agent

**Files:**
- Modify: `config/research-brief.yaml`
- Test: `python3 -c` pillar/query load + `scripts/research-keyword-eval.sh` (기존, 회귀 warn 허용)

**Interfaces:**
- Consumes: existing gather/`brief_quality.load_config` reading `search_queries` / `priority_queries` / `coverage.pillars`
- Produces: YAML with pillars `agent_news`, `agent_tech`, `agent_industry`, `agent_security_gov`; `insight_limit: 7` unchanged

- [ ] **Step 1: Write failing assertion for new pillar ids**

```bash
cd ~/hermes-content-studio
python3 - <<'PY'
import yaml
from pathlib import Path
cfg = yaml.safe_load(Path("config/research-brief.yaml").read_text(encoding="utf-8"))
ids = [p["id"] for p in cfg["coverage"]["pillars"]]
assert "agent_news" in ids, ids
assert "agent_tech" in ids, ids
assert "agent_industry" in ids, ids
assert "agent_security_gov" in ids, ids
print("OK pillars")
PY
```

Expected: FAIL (`AssertionError` — 구 pillars만 존재)

- [ ] **Step 2: Replace coverage + queries in `config/research-brief.yaml`**

`persona.focus` / `voice`를 AI Agent 동향·성장 전략가 시선으로 조정하고, `coverage.pillars`를 아래로 교체:

```yaml
coverage:
  daily_lens:
    - 글로벌 뉴스·데이터
    - 대한민국 뉴스·데이터
  pillars:
    - id: agent_news
      label: "AI Agent 최신 뉴스·제품"
      keywords: [AI agent, agentic AI, multi-agent, autonomous agent]
    - id: agent_tech
      label: "AI Agent 기술 트렌드"
      keywords: [tool use, agent runtime, agent budget, MCP, orchestration]
    - id: agent_industry
      label: "산업·엔터프라이즈 적용"
      keywords: [enterprise agent, workflow automation, adoption, use case]
    - id: agent_security_gov
      label: "보안·통제·거버넌스"
      keywords: [AI governance, EU AI Act, agent security, human-in-the-loop, stop button]
```

`search_queries` 예시 (전부 `{year}` 유지):

```yaml
search_queries:
  - "AI agent news {year}"
  - "agentic AI enterprise adoption {year}"
  - "multi-agent workflow orchestration {year}"
  - "AI agent security governance {year}"
  - "EU AI Act AI agent compliance {year}"
  - "AI agent budget payment protocol {year}"
  - "Korea enterprise AI agent adoption {year}"
  - "OpenAI agents update {year}"
  - "Anthropic Claude agent computer use {year}"
  - "Salesforce agentic enterprise {year}"
```

`priority_queries`:

```yaml
priority_queries:
  korea: "Korea enterprise AI agent adoption {year}"
  llm:
    - "AI agent news {year}"
    - "agentic AI security governance {year}"
    - "multi-agent workflow enterprise {year}"
    - "AI agent industry use case {year}"
```

`insight_limit: 7` · `freshness` · `schedule` 유지.

- [ ] **Step 3: Re-run Step 1 assertion**

Expected: `OK pillars`

- [ ] **Step 4: Commit**

```bash
git add config/research-brief.yaml
git commit -m "$(cat <<'EOF'
feat(research): retarget M1 brief lens to AI Agent trends

Replace AX/LLM-four-pillar queries with news, tech, industry,
and security/governance pillars for daily agent coverage.
EOF
)"
```

---

### Task 2: `blog_daily_report.py` — Velog MD assembler (TDD)

**Files:**
- Create: `scripts/lib/blog_daily_report.py`
- Create: `scripts/blog-daily-report-eval.sh` (초기: unit 섹션만)
- Test: `scripts/blog-daily-report-eval.sh --unit`

**Interfaces:**
- Consumes: `list[Insight]`, `stamp: str`, `summary: str` from `lib.content_quality`
- Produces:
  - `BODY_MAX_CHARS = 3000`
  - `body_char_count(md: str) -> int` — excludes `## 출처` / `🔗 출처` and everything after
  - `build_daily_blog_md(stamp, summary, insights) -> str`
  - `build_daily_blog_html(stamp, summary, insights) -> str`
  - `build_threads_md(stamp, summary, insights) -> str`
  - Section header constants matching spec

- [ ] **Step 1: Add failing unit eval**

Create `scripts/blog-daily-report-eval.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:---unit}"
export PYTHONPATH="$DIR${PYTHONPATH:+:$PYTHONPATH}"
pass=0; fail=0
ok(){ echo "PASS: $*"; pass=$((pass+1)); }
bad(){ echo "FAIL: $*"; fail=$((fail+1)); }

if [[ "$MODE" == "--unit" || "$MODE" == "--all" ]]; then
  python3 - <<'PY' && ok "unit build_daily_blog_md" || bad "unit build_daily_blog_md"
import sys
sys.path.insert(0, ".")
from lib.blog_daily_report import BODY_MAX_CHARS, body_char_count, build_daily_blog_md
from lib.content_quality import Insight

insights = [
    Insight(
        title="에이전트 통제권",
        summary="EU AI Act와 비상 정지 요구가 확산되고 있습니다.",
        marketer_view="권한 캡과 HITL을 먼저 설계해야 합니다.",
        channels="blog|linkedin",
        url="https://example.com/a",
        source_title="EU AI Act",
    ),
    Insight(
        title="에이전트 예산",
        summary="에이전트 전용 예산 한도가 주목받습니다.",
        marketer_view="최악의 손실액을 숫자로 고정하세요.",
        channels="blog|linkedin",
        url="https://example.com/b",
        source_title="Budget",
    ),
]
md = build_daily_blog_md("2026-08-11", "AI Agent 일일 요약입니다.", insights)
assert "[오늘의 AI 트렌드]" in md
assert "주요 트렌드" in md
assert "주목" in md and "기술" in md
assert "시사점" in md or "대책" in md
assert "한 줄 요약" in md
assert "https://example.com/a" in md
assert body_char_count(md) <= BODY_MAX_CHARS
assert BODY_MAX_CHARS == 3000
print("unit ok", body_char_count(md))
PY
fi

echo "pass=$pass fail=$fail"
[[ "$fail" -eq 0 ]]
```

`chmod +x scripts/blog-daily-report-eval.sh`

- [ ] **Step 2: Run unit eval — expect FAIL**

```bash
~/hermes-content-studio/scripts/blog-daily-report-eval.sh --unit
```

Expected: FAIL import `blog_daily_report`

- [ ] **Step 3: Implement `scripts/lib/blog_daily_report.py`**

Create the full module (imports at top — no inline imports except existing repo pattern for circular deps). Required API:

```python
BODY_MAX_CHARS = 3000
H2_TRENDS = "## 1. 주요 트렌드 및 개발 이슈"
H2_TECH = "## 2. 요즘 주목받는 핵심 기술"
H2_IMPLICATIONS = "## 3. 마케터 및 비즈니스 리더를 위한 향후 대책"

def body_char_count(md: str) -> int:
    """Return len of MD excluding sources/SEO tail."""

def build_daily_blog_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Velog-style daily report markdown."""

def build_daily_blog_html(stamp: str, summary: str, insights: list[Insight]) -> str:
    """HTML twin of daily report (Article JSON-LD, no FAQPage required)."""

def build_threads_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Package-companion Threads shortform."""
```

`body_char_count`: strip from first of `\n## 출처`, `\n🔗 출처`, `\n## SEO` onward; return `len(text)`.

`build_daily_blog_md` algorithm:

1. `theme = insights[0].korean_title` (fallback `"AI 에이전트 동향"`)
2. Title line: `# [오늘의 AI 트렌드] {theme}({MM/DD})` where MM/DD from stamp
3. Prologue: `## {YYYY}년 {M}월 {D}일 최신 동향과 실행 전략` is NOT required — use plain paragraphs under an optional date heading `# {YYYY}년 {M}월 {D}일 최신 동향과 실행 전략` only if it does not break single H1; prefer prose paragraphs after H1 (match Velog: second H1 in source is platform quirk — **our MD uses one H1 title only**)
4. 2–4 prologue paragraphs from `humanize(summary, genre="blog")` + first insight `context_blurb`
5. Append `H2_TRENDS` then for insights[:2] write `### ① {title}` / `### ② {title}` + 1–2 paragraphs each from `korean_summary` / `marketer_view`
6. Append `H2_TECH` + bullets (`- `) from insights[2:5] or marketer_view fallbacks
7. Append `H2_IMPLICATIONS` + numbered `1. 2. 3.` from marketer_view / utilization / guides_tips
8. Append `🔗 출처 :` then one line per insight `title — url` (use `ins.url`, skip empty)
9. Append `💡 한 줄 요약: {one sentence from theme + top marketer_view}`
10. While `body_char_count(md) > BODY_MAX_CHARS`: shorten longest paragraph with `lib.common.finish_at_sentence` / `compress_sentences` until ≤ cap or no further shrink (then hard slice at sentence boundary)

`build_daily_blog_html`:

1. Call shared internal `_build_report(...)` returning structured fields OR parse MD — prefer shared dataclass:

```python
@dataclass
class DailyBlogReport:
    stamp: str
    slug: str
    title: str
    meta_description: str
    prologue: list[str]
    trend_blocks: list[tuple[str, list[str]]]  # heading, paragraphs
    tech_bullets: list[str]
    implications: list[str]
    sources: list[tuple[str, str]]
    one_liner: str
```

2. Render via `read_template("templates/html/blog-post.html")` with:
   - `{{TITLE}}`, `{{META_DESCRIPTION}}`, `{{CANONICAL_URL}}`, `{{DATE_ISO}}`, `{{SECTIONS}}`
   - `{{DIRECT_ANSWER}}` = one_liner
   - `{{GEO_QUOTE}}` = one_liner (reuse callout)
   - `{{FAQ_ITEMS}}` = `""`
   - `{{FAQ_JSONLD}}` = `json.dumps({"@context":"https://schema.org","@type":"Article","headline": title})` **or** omit FAQ script in template (Task 5)
   - `{{ARTICLE_JSONLD}}` = Article schema
   - `{{SOURCES_LIST}}` = `<li><a href=...>`
   - `{{TAGS}}` = `AI Agent, Agentic AI, Governance, Marketing`
   - `{{READ_TIME}}` = `"4"`
   - `{{SUBTITLE}}` = f"{stamp} AI Agent 일일 트렌드"

`build_threads_md` in this task may return a minimal stub containing `[블로그 링크]` so Task 2 unit still focuses on blog; **or** fully implement here and let Task 3 only add eval — prefer **stub with required markers** in Task 2, complete copy in Task 3:

```python
def build_threads_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    theme = _theme_title(insights)
    return f"# Threads — {theme} ({stamp})\n\n(draft)\n\n[블로그 링크]\n\n궁금한 점 댓글?\n"
```


- [ ] **Step 4: Run unit eval — expect PASS**

```bash
~/hermes-content-studio/scripts/blog-daily-report-eval.sh --unit
```

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/blog_daily_report.py scripts/blog-daily-report-eval.sh
git commit -m "$(cat <<'EOF'
feat(blog): add Velog-style daily report assembler

Deterministic MD/HTML builder with ≤3000 body chars and
Threads companion draft helpers for AI Agent daily reports.
EOF
)"
```

---

### Task 3: Threads companion builder + unit coverage

**Files:**
- Modify: `scripts/lib/blog_daily_report.py` (`build_threads_md`)
- Modify: `scripts/blog-daily-report-eval.sh` (threads unit)

**Interfaces:**
- Produces: `build_threads_md(stamp, summary, insights) -> str` containing hook, 3–5 points, `[블로그 링크]`, question CTA

- [ ] **Step 1: Extend eval with threads assertions**

```python
from lib.blog_daily_report import build_threads_md
th = build_threads_md("2026-08-11", "요약", insights)
assert "[블로그 링크]" in th
assert "?" in th or "댓글" in th
assert len(th.splitlines()) >= 5
```

- [ ] **Step 2: Run eval — FAIL if stub empty**

- [ ] **Step 3: Implement `build_threads_md`**

```markdown
# Threads — {theme} ({stamp})

{훅 1–2줄}

핵심만 말하면:
→ {point1}
→ {point2}
→ {point3}

자세한 맥락은 블로그에 정리해 두었어요.
[블로그 링크]

오늘 팀에서 가장 먼저 손대고 싶은 건 통제권·예산·워크플로 중 어디인가요?
댓글로 한 가지만 남겨 주세요.
```

- [ ] **Step 4: Run eval PASS → Commit**

```bash
git add scripts/lib/blog_daily_report.py scripts/blog-daily-report-eval.sh
git commit -m "feat(threads): add package-companion Threads shortform builder"
```

---

### Task 4: Wire assemblers into content package path

**Files:**
- Modify: `scripts/lib/content_quality.py` — `build_blog_article_md`, `build_blog_html`, `build_notion_packages`
- Modify: `scripts/lib/blog_pipeline.py` — SEO/structure checklists
- Modify: `config/content-orchestration.yaml` — add threads output
- Test: unit eval + assemble against existing brief (if present)

**Interfaces:**
- `build_blog_article_md` → delegates to `build_daily_blog_md`
- `build_blog_html` → delegates to `build_daily_blog_html`
- `build_notion_packages` also writes `packages/{stamp}_threads.md`

- [ ] **Step 1: Change `build_blog_article_md` / `build_blog_html` to delegate**

In `content_quality.py`:

```python
def build_blog_article_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    from lib.blog_daily_report import build_daily_blog_md
    return build_daily_blog_md(stamp, summary, insights)


def build_blog_html(
    stamp: str,
    summary: str,
    insights: list[Insight],
    *,
    wiki_blurbs: list[str] | None = None,
) -> str:
    from lib.blog_daily_report import build_daily_blog_html
    return build_daily_blog_html(stamp, summary, insights)
```

(`wiki_blurbs` ignored for Velog format — YAGNI; keep param for call-site compatibility.)

- [ ] **Step 2: Extend `build_notion_packages`**

```python
from lib.blog_daily_report import build_threads_md
...
paths["threads"] = packages_dir / f"{stamp}_threads.md"
paths["threads"].write_text(build_threads_md(stamp, summary, insights), encoding="utf-8")
```

- [ ] **Step 3: Update orchestration YAML outputs**

Under M2 `outputs:` add:

```yaml
threads_package: content/packages/{date}_threads.md
```

- [ ] **Step 4: Update `blog_pipeline.py` SEO/structure strings**

Replace FAQ JSON-LD / GEO checklist items with Velog section checklist (`[오늘의 AI 트렌드]`, H2×3, sources, one-liner, ≤3000).

- [ ] **Step 5: Smoke assemble (no network if brief exists)**

```bash
# Prefer existing brief
STAMP=2026-08-11
python3 - <<PY
import sys
sys.path.insert(0, "scripts")
from pathlib import Path
from lib.content_quality import parse_brief, build_blog_article_md, build_notion_packages
from lib.common import WORKDIR  # or Path.home()/hermes-content-studio
stamp = "$STAMP"
text = Path.home().joinpath(f"hermes-content-studio/content/research/{stamp}_brief.md").read_text(encoding="utf-8")
summary, insights = parse_brief(text)
md = build_blog_article_md(stamp, summary, insights)
Path("/tmp/blog-smoke.md").write_text(md, encoding="utf-8")
print(len(md), md.splitlines()[0])
PY
```

Expected: title contains `[오늘의 AI 트렌드]`

- [ ] **Step 6: Commit**

```bash
git add scripts/lib/content_quality.py scripts/lib/blog_pipeline.py config/content-orchestration.yaml
git commit -m "$(cat <<'EOF'
feat(m2): wire Velog blog and Threads into content package

Delegate blog MD/HTML to daily report assembler and write
threads package companion alongside Notion packages.
EOF
)"
```

---

### Task 5: HTML template + validate gates

**Files:**
- Modify: `templates/html/blog-post.html`
- Modify: `scripts/validate-output.sh`
- Modify: `config/content-quality.yaml`
- Modify: `scripts/lib/m4_coach.py` (blog traits)
- Test: `validate-output.sh blog-article` / `blog` on smoke files

- [ ] **Step 1: Soften HTML template**

- Keep `{{ARTICLE_JSONLD}}`
- Make FAQ block optional: if `{{FAQ_ITEMS}}` empty, hide section via empty string
- Replace FAQPage requirement path: `{{FAQ_JSONLD}}` may be Article-only or `{"@context":"https://schema.org","@type":"Article"}` duplicate avoided — prefer empty `<script>` removal by rendering only Article JSON-LD from Python
- Remove hard dependency on `.geo-quote` for layout (keep optional callout for one-liner)

- [ ] **Step 2: Rewrite `blog-article` case in `validate-output.sh`**

```bash
blog-article)
  grep -q "\[오늘의 AI 트렌드\]" "$FILE" || fail "오늘의 AI 트렌드 제목 없음"
  grep -qE "주요 트렌드" "$FILE" || fail "트렌드 섹션 없음"
  grep -qE "주목.*기술|핵심 기술" "$FILE" || fail "기술 섹션 없음"
  grep -qE "시사점|향후 대책" "$FILE" || fail "시사점 섹션 없음"
  grep -qE "한 줄 요약" "$FILE" || fail "한 줄 요약 없음"
  grep -qE "https?://" "$FILE" || fail "출처 URL 없음"
  python3 - <<PY || fail "본문 3000자 초과"
from pathlib import Path
import sys
sys.path.insert(0, "$WORKDIR/scripts")
from lib.blog_daily_report import body_char_count, BODY_MAX_CHARS
n = body_char_count(Path("$FILE").read_text(encoding="utf-8"))
if n > BODY_MAX_CHARS:
    raise SystemExit(f"body {n} > {BODY_MAX_CHARS}")
print(n)
PY
  python3 - <<PY || fail "blog-article naturalness 게이트"
import sys
sys.path.insert(0, "$WORKDIR/scripts")
from pathlib import Path
from lib.naturalness_audit import audit_blog_article_md_naturalness
issues = audit_blog_article_md_naturalness(Path("$FILE"))
if issues:
    raise SystemExit("; ".join(issues))
PY
  CHARS=$(python3 -c "print(len(open('$FILE', encoding='utf-8').read()))")
  pass "blog article OK: $FILE (${CHARS} chars)"
  ;;
```

- [ ] **Step 3: Rewrite `blog` HTML case**

- Keep title, meta description, H1, canonical
- **Remove** hard fail on `FAQPage`
- Require Article JSON-LD (`"@type": "Article"`) OR any `application/ld+json`
- H2 ≥ 3 warn or fail per new structure
- Remove GEO block hard requirement (warn only or drop)

- [ ] **Step 4: Add `threads-package` type**

```bash
threads-package)
  grep -q "\[블로그 링크\]" "$FILE" || fail "[블로그 링크] 없음"
  grep -qE "\?|댓글" "$FILE" || fail "CTA 없음"
  (( SIZE > 120 )) || fail "threads 너무 짧음"
  pass "threads package OK: $FILE"
  ;;
```

Update usage string at top of `validate-output.sh`.

- [ ] **Step 5: Update `content-quality.yaml`**

```yaml
longform:
  blog:
    title_max_chars: 70
    body_max_chars: 3000
    format: velog_daily_trend
    min_h2_sections: 3
    require_faq_jsonld: false
    require_geo_block: false
    require_direct_answer_first: false
seo_aeo_geo:
  require_faq_jsonld: false   # blog path; keep true only if other channels need — if global, set blog override in code
  require_source_urls: true
  require_geo_block: false
  require_direct_answer_first: false
```

If `seo_aeo_geo` is shared globally and newsletter/other rely on it, **prefer blog-local flags** under `longform.blog` and leave global keys unchanged — document which path `blog_daily_report` reads.

- [ ] **Step 6: Update `m4_coach.py` blog traits**

Replace `faq_jsonld` / `geo_block` scoring for blog with `trend_title`, `h2_count`, `source_url`, `body_cap`.

- [ ] **Step 7: Validate smoke files**

```bash
~/hermes-content-studio/scripts/validate-output.sh blog-article /tmp/blog-smoke.md
STAMP=2026-08-11
HTML=$(ls ~/hermes-content-studio/content/blog/${STAMP}_blog_*.html 2>/dev/null | head -1)
if [[ -n "${HTML:-}" ]]; then
  ~/hermes-content-studio/scripts/validate-output.sh blog "$HTML"
fi
```

- [ ] **Step 8: Commit**

```bash
git add templates/html/blog-post.html scripts/validate-output.sh config/content-quality.yaml scripts/lib/m4_coach.py
git commit -m "$(cat <<'EOF'
feat(validate): switch blog gates to Velog daily report schema

Drop FAQ/GEO hard fails, enforce title/sections/3000-char body,
and add soft threads-package validation.
EOF
)"
```

---

### Task 6: Eval harness + Notion optional + docs/skills

**Files:**
- Modify: `scripts/blog-daily-report-eval.sh` — add `--live [DATE]` using packages
- Modify: `config/notion-archive.yaml` — threads glob (optional)
- Modify: `skills/channels/blog/SKILL.md`
- Modify: `.harness/progress.md`
- Test: `blog-daily-report-eval.sh --all`

- [ ] **Step 1: Add `--live` mode**

For `DATE=${2:-today}`:

1. Require `content/packages/{DATE}_blog-article.md` and `_threads.md`
2. Run `validate-output.sh blog-article` and `threads-package`
3. Assert body ≤ 3000 via Python

- [ ] **Step 2: Notion archive glob (optional)**

```yaml
threads:
  label: Threads
  glob: "content/packages/*_threads.md"
```

- [ ] **Step 3: Update blog skill STABLE section**

Document Velog sections, ≤3000, Threads package path, AI Agent lens. Do **not** edit LEARNED.

- [ ] **Step 4: Update `.harness/progress.md`** with change summary + DoD checklist pointers

- [ ] **Step 5: Run**

```bash
~/hermes-content-studio/scripts/blog-daily-report-eval.sh --unit
```

- [ ] **Step 6: Commit**

```bash
git add scripts/blog-daily-report-eval.sh config/notion-archive.yaml skills/channels/blog/SKILL.md .harness/progress.md
git commit -m "docs: document Velog blog+Threads daily report and eval"
```

---

### Task 7: End-to-end smoke (Definition of Done)

**Files:** none new (run scripts)

- [ ] **Step 1: Research brief (network)**

```bash
~/hermes-content-studio/scripts/run-research-brief.sh
```

Expected: `content/research/{today}_brief.md` with Top 7; validate research PASS

- [ ] **Step 2: Content package**

```bash
SKIP_NEWSLETTER=0 ~/hermes-content-studio/scripts/run-content-package.sh
# or full:
# ~/hermes-content-studio/scripts/run-pipeline.sh
```

Expected artifacts:

- `content/packages/{date}_blog-article.md` — Velog schema
- `content/blog/{date}_blog_*.html`
- `content/packages/{date}_threads.md`
- linkedin / instagram unchanged formats
- newsletter if not skipped

- [ ] **Step 3: Validate**

```bash
DATE=$(date +%Y-%m-%d)
~/hermes-content-studio/scripts/validate-output.sh blog-article ~/hermes-content-studio/content/packages/${DATE}_blog-article.md
~/hermes-content-studio/scripts/validate-output.sh threads-package ~/hermes-content-studio/content/packages/${DATE}_threads.md
~/hermes-content-studio/scripts/validate-output.sh linkedin ~/hermes-content-studio/content/linkedin/${DATE}_linkedin_*.md
~/hermes-content-studio/scripts/blog-daily-report-eval.sh --all
```

- [ ] **Step 4: Fix any gate failures (tight loop) — no “done” without PASS**

- [ ] **Step 5: Final progress note + commit only if code fixes were needed**

---

## Spec coverage checklist (self-review)

| Spec section | Task |
|--------------|------|
| D1 M1 AI Agent lens | Task 1 |
| D2 Threads package companion | Task 3, 4 |
| D3 Velog blog + HTML | Task 2, 4, 5 |
| D4 Config + assembler | Tasks 1–5 |
| ≤3000 body / sections / tone | Task 2, 5 |
| validate gates | Task 5 |
| LI/IG/NL format unchanged | Global constraint; Task 4 does not touch their builders |
| DoD smoke | Task 7 |
| Rollback | git revert task commits; documented in spec §11 |

## Out of scope (do not implement)

- `content/threads/` formal channel
- Auto-post Velog/Threads
- Newsletter/LinkedIn/Instagram format changes
- LLM full rewrite of brief/blog
