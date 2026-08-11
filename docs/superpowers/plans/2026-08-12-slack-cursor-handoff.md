# Slack Cursor Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slack `/cursor <설명>`으로 Telegram automate와 동일하게 HANDOFF 생성 → Cursor CLI 백그라운드 실행 → Slack 알림을 제공한다.

**Architecture:** 얇은 `cursor-handoff.sh`가 `telegram-custom.sh` automate 경로를 재사용하고, `run-cursor-handoff.sh`의 `notify()`를 Slack 듀얼로 확장한다. `/automate`(personal)와 `/handoff`(session)는 변경하지 않는다.

**Tech Stack:** bash, Slack Web API (`slack-notify.sh`), existing Codex/`hermes-run.sh`, `cursor-agent`

**Spec:** `docs/superpowers/specs/2026-08-12-slack-cursor-handoff-design.md`

## Global Constraints

- `/cursor` 신설; `/automate` personal 유지; `/handoff` 세션 핸드오프 유지
- HANDOFF SoT: `content/drafts/cursor-handoff/*_HANDOFF.md`
- Codex 로직 대규모 복제 금지 — 엔트리/알림만 확장
- `HERMES_CURSOR_AUTO=0`이면 CLI 스킵
- 기본 Slack 채널: `SLACK_HOME_CHANNEL` / `C0B8CN2EA05`
- Telegram notify 공존 (TELEGRAM_CHAT_ID 있으면)
- Credentials / `~/.hermes/.env` 커밋 금지
- New Slack App / OAuth 재발급 금지

## File Map

| File | Responsibility |
|------|----------------|
| `scripts/run-cursor-handoff.sh` | Dual notify (Telegram + Slack) |
| `scripts/cursor-handoff.sh` | Slack/공통 엔트리 → automate + cursor auto |
| `config/slack-routing.yaml` | `/cursor` quick_command + channel_prompt |
| `scripts/slack-cursor-handoff-eval.sh` | 라우팅·dry-run·notify helper smoke |
| `.harness/progress.md` | 진행 기록 |

---

### Task 1: Dual notify in `run-cursor-handoff.sh`

**Files:**
- Modify: `scripts/run-cursor-handoff.sh`
- Test: `scripts/slack-cursor-handoff-eval.sh` (notify unit section)

**Interfaces:**
- Produces: `load_slack_channel()` → channel id or empty
- Produces: `notify(msg)` posts Telegram (existing) and Slack when channel available / `HERMES_NOTIFY_SLACK=1`

- [ ] **Step 1: Write failing eval for notify helpers**

Create `scripts/slack-cursor-handoff-eval.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
pass=0; fail=0
ok(){ echo "PASS: $*"; pass=$((pass+1)); }
bad(){ echo "FAIL: $*"; fail=$((fail+1)); }

# Source-check: load_slack_channel + slack call present in run-cursor-handoff.sh
if grep -q 'load_slack_channel' "$DIR/run-cursor-handoff.sh" \
  && grep -q 'slack-notify.sh' "$DIR/run-cursor-handoff.sh"; then
  ok "run-cursor-handoff dual notify hooks"
else
  bad "run-cursor-handoff dual notify hooks"
fi

echo "pass=$pass fail=$fail"
[[ "$fail" -eq 0 ]]
```

`chmod +x` and run — expect FAIL.

- [ ] **Step 2: Implement dual notify**

In `run-cursor-handoff.sh`, after `load_chat_id`:

```bash
load_slack_channel() {
  if [[ -n "${SLACK_HOME_CHANNEL:-}" ]]; then
    echo "$SLACK_HOME_CHANNEL"; return
  fi
  local env_file="$HOME/.hermes/.env"
  if [[ -f "$env_file" ]]; then
    local v
    v=$(grep -E '^SLACK_HOME_CHANNEL=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    [[ -n "$v" ]] && { echo "$v"; return; }
  fi
  # fallback studio default
  echo "C0B8CN2EA05"
}

notify() {
  local msg="$1"
  local chat_id slack_ch
  chat_id=$(load_chat_id)
  [[ -n "$chat_id" ]] && "$DIR/telegram-notify.sh" "$chat_id" "$msg" 2>/dev/null || true

  # Slack: always attempt when HERMES_NOTIFY_SLACK=1, or when SLACK_HOME_CHANNEL set,
  # or default home channel if HERMES_NOTIFY_SLACK is unset but caller is Slack entry
  # Spec: Slack notify when HERMES_NOTIFY_SLACK=1 OR channel resolvable for Slack-triggered runs.
  # Practical rule: if HERMES_NOTIFY_SLACK=0 skip Slack; else try load_slack_channel.
  if [[ "${HERMES_NOTIFY_SLACK:-1}" != "0" ]]; then
    slack_ch=$(load_slack_channel)
    [[ -n "$slack_ch" ]] && "$DIR/slack-notify.sh" "$slack_ch" "$msg" 2>/dev/null || true
  fi
}
```

Note: Defaulting Slack notify to on may spam Telegram-only users. Prefer:

```bash
# Slack only if HERMES_NOTIFY_SLACK=1 OR SLACK_HOME_CHANNEL explicitly set in env for this process
if [[ "${HERMES_NOTIFY_SLACK:-0}" == "1" ]] || [[ -n "${SLACK_HOME_CHANNEL:-}" ]]; then
  slack_ch=$(load_slack_channel)
  [[ -n "$slack_ch" ]] && "$DIR/slack-notify.sh" "$slack_ch" "$msg" 2>/dev/null || true
fi
```

Cursor-handoff Slack entry must `export HERMES_NOTIFY_SLACK=1` and/or `SLACK_HOME_CHANNEL`.

- [ ] **Step 3: Re-run eval PASS → Commit**

```bash
git commit -m "feat(cursor): dual Slack+Telegram notify for handoff runner"
```

---

### Task 2: `scripts/cursor-handoff.sh` thin entry

**Files:**
- Create: `scripts/cursor-handoff.sh`
- Modify: `scripts/slack-cursor-handoff-eval.sh` (entry checks)
- Test: `bash -n` + eval

**Interfaces:**
- CLI: `cursor-handoff.sh qc "<message>"` | `cursor-handoff.sh auto "<message>"`
- Forces task type automate; exports `HERMES_NOTIFY_SLACK=1`; delegates to `telegram-custom.sh`

- [ ] **Step 1: Failing eval — script exists and is executable**

- [ ] **Step 2: Implement**

```bash
#!/usr/bin/env bash
# Slack /cursor → Cursor HANDOFF (shared automate path)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"

# Prefer Slack notify for this entry
export HERMES_NOTIFY_SLACK=1
if [[ -z "${SLACK_HOME_CHANNEL:-}" && -f "$HOME/.hermes/.env" ]]; then
  # shellcheck disable=SC1091
  SLACK_HOME_CHANNEL=$(grep -E '^SLACK_HOME_CHANNEL=' "$HOME/.hermes/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
  export SLACK_HOME_CHANNEL
fi
if [[ -z "${SLACK_HOME_CHANNEL:-}" ]]; then
  export SLACK_HOME_CHANNEL=C0B8CN2EA05
fi

usage() {
  echo "Usage: $0 {qc|auto} <message>"
  echo "  Slack /cursor handoff — Codex HANDOFF + run-cursor-handoff"
}

cmd="${1:-}"
shift || true
msg="${*:-}"

case "$cmd" in
  qc|auto)
    [[ -z "$msg" ]] && { echo "❌ message required"; usage; exit 1; }
    # Force automate path regardless of keyword detect
    exec "$DIR/telegram-custom.sh" qc automate "$msg"
    ;;
  -h|--help|help) usage; exit 0 ;;
  *) usage; exit 1 ;;
esac
```

**Important:** Verify `telegram-custom.sh qc automate` accepts that form. If `qc` only takes `mail|automate|ask` as first arg after qc, match existing:

From `telegram-custom.sh` end — check `qc` handler. If `qc automate "msg"` works, use it. If only `qc mail` style with message as rest, align.

If `qc automate` is not supported, use:

```bash
exec "$DIR/telegram-custom.sh" auto "자동화 구현: $msg"
```

(keyword detect maps 구현/자동화 → automate)

Or extend `telegram-custom.sh` minimally:

```bash
# in qc case
automate|cursor)
  submit_job automate "$2"  # or run path matching existing automate
```

Prefer minimal extension to `telegram-custom.sh` if `qc automate` missing.

- [ ] **Step 3: chmod +x, bash -n, eval PASS, commit**

```bash
git commit -m "feat(slack): add cursor-handoff.sh entry for /cursor"
```

---

### Task 3: Slack routing + setup

**Files:**
- Modify: `config/slack-routing.yaml`
- Modify: `scripts/slack-cursor-handoff-eval.sh`
- Optional: `AGENTS.md` one-liner under Slack section (only if already documenting slash commands)

- [ ] **Step 1: Add quick_command + prompt lines**

```yaml
cursor:
  type: exec
  command: ~/hermes-content-studio/scripts/cursor-handoff.sh qc
```

Note: Hermes quick_commands often append message — match how other `qc` commands receive args. Looking at `mail`:

```yaml
mail:
  type: exec
  command: ~/hermes-content-studio/scripts/telegram-custom.sh qc mail
```

So for cursor, either:

```yaml
cursor:
  type: exec
  command: ~/hermes-content-studio/scripts/cursor-handoff.sh qc
```

(if gateway appends the rest of the message as args) — mirror `ask`/`automate` patterns in telegram routing if any.

Also update `channel_prompt`:

```
Slash: ... /cursor (Cursor HANDOFF) ...
# clarify /automate = personal, /handoff = session, /cursor = Cursor CLI
```

- [ ] **Step 2: Eval asserts yaml contains cursor command path**

- [ ] **Step 3: Run `setup-slack-routing.sh`** (updates `~/.hermes/config.yaml` — do not commit that file)

- [ ] **Step 4: Commit studio yaml only**

```bash
git commit -m "feat(slack): route /cursor to cursor-handoff"
```

---

### Task 4: Eval completeness + progress + dry-run smoke

**Files:**
- Modify: `scripts/slack-cursor-handoff-eval.sh`
- Modify: `.harness/progress.md`

- [ ] **Step 1: Expand eval**

Checks:

1. Dual notify hooks in `run-cursor-handoff.sh`
2. `cursor-handoff.sh` exists + `bash -n`
3. `slack-routing.yaml` has `cursor:` with `cursor-handoff.sh`
4. `run-cursor-handoff.sh --dry-run --latest` exits 0 **or** exits 1 with HANDOFF 없음 (both acceptable — document); if HANDOFF exists, dry-run must print handoff path
5. `/automate` still aliases personal in yaml; `/handoff` still `qc handoff`

- [ ] **Step 2: Run eval PASS**

- [ ] **Step 3: Update `.harness/progress.md`**

- [ ] **Step 4: Commit**

```bash
git commit -m "test: add slack cursor handoff eval and progress note"
```

---

### Task 5: Optional live smoke (DoD)

- [ ] **Step 1:** With Slack token available, `HERMES_NOTIFY_SLACK=1 SLACK_HOME_CHANNEL=C0B8CN2EA05 ./scripts/slack-notify.sh "$SLACK_HOME_CHANNEL" "cursor-handoff smoke"`

- [ ] **Step 2:** If Codex/cursor available, optional `./scripts/cursor-handoff.sh qc "dry smoke handoff"` with `HERMES_CURSOR_AUTO=0` to only generate HANDOFF (or skip if Codex cost)

- [ ] **Step 3:** Report permalinks/channel confirm in progress — no commit of secrets

---

## Spec coverage

| Spec | Task |
|------|------|
| D1 parity | 1–2 |
| D2 /cursor | 3 |
| D3 Codex same path | 2 |
| Dual notify | 1 |
| DoD / eval | 4–5 |
| Non-goals automate/handoff | 3, 4 asserts |

## Out of scope

- New Slack app, personal `/automate` remap, session `/handoff` change, Cloud Agents
