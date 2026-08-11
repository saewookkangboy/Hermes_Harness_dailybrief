# Design: Slack Cursor Handoff (Telegram parity)

**Date:** 2026-08-12  
**Status:** Approved (conversation)  
**Approach:** Shared automate/Codex flow + dual-channel notify (방식 1)  
**Related:** `scripts/run-cursor-handoff.sh`, `scripts/telegram-custom.sh`, `config/slack-routing.yaml`

## 1. Goal

Slack에서도 Telegram `/automate` → Cursor CLI 핸드오프와 동일한 파이프라인을 제공한다.

1. Slack `/cursor <설명>`으로 HANDOFF 생성 (Codex / vibe-coding-cursor 경로)
2. `run-cursor-handoff.sh --background`로 Cursor Agent 실행
3. 진행·완료·실패를 **Slack**으로 알림 (Telegram 알림은 기존처럼 유지 가능)

## 2. Decisions (locked)

| ID | 결정 | 선택 |
|----|------|------|
| D1 | 기능 범위 | **A** — Telegram 패리티: HANDOFF 생성 → Cursor CLI → Slack 알림 |
| D2 | 슬래시 커맨드 | **A** — `/cursor` 신설; `/automate`는 personal 유지; `/handoff`는 세션 핸드오프 유지 |
| D3 | HANDOFF 생성 백엔드 | **A** — Telegram automate와 동일 (Codex / custom automate 경로) |
| D4 | 구현 방식 | **방식 1** — 공유 플로우 + `run-cursor-handoff` 듀얼 notify |

## 3. Architecture / Data flow

```
Slack home channel (#일반데이터 / SLACK_HOME_CHANNEL)
  /cursor <구현 설명>
        ↓
  slack-routing quick_commands.cursor
        ↓
  cursor-handoff entry (thin wrapper or telegram-custom automate reuse)
        ↓
  Codex / vibe-coding-cursor → content/drafts/cursor-handoff/{stamp}_*_HANDOFF.md
        ↓
  run-cursor-handoff.sh --background --handoff PATH
  (HERMES_CURSOR_AUTO=0 이면 CLI 스킵)
        ↓
  notify:
    - Slack chat.postMessage (primary for Slack-triggered runs)
    - Telegram (if TELEGRAM_CHAT_ID present — existing behavior)
```

원칙:

- HANDOFF SoT: `content/drafts/cursor-handoff/*_HANDOFF.md`
- 대상 레포: HANDOFF의 `**대상 레포:**` 절대경로 (기존 파서 유지)
- 대규모 Codex 로직 복제 금지 — 엔트리/알림만 확장

## 4. Slack routing

### 4.1 `config/slack-routing.yaml`

Add:

```yaml
cursor:
  type: exec
  command: ~/hermes-content-studio/scripts/cursor-handoff.sh qc "<message>"
  # or equivalent that invokes shared automate + cursor auto
```

Update `channel_prompt` to document `/cursor` under Cursor handoff (separate from `/automate` personal and `/handoff` session).

### 4.2 Apply

`scripts/setup-slack-routing.sh` merges into `~/.hermes/config.yaml`.

### 4.3 Non-goals for routing

- Do not remap `/automate` away from personal-assistant
- Do not change `/handoff` → `telegram-pipeline.sh qc handoff`

## 5. Scripts

### 5.1 `scripts/cursor-handoff.sh` (new thin entry)

- Accepts `qc|auto` + message (Slack slash payload)
- Invokes shared automate path used by Telegram for HANDOFF generation
- Sets notify preference for Slack (e.g. `HERMES_NOTIFY_SLACK=1`, `SLACK_HOME_CHANNEL`)
- With `HERMES_CURSOR_AUTO` default `1`, calls `run-cursor-handoff.sh --background`

Exact flags may reuse `telegram-custom.sh automate` with env overrides rather than duplicating Codex invocation.

### 5.2 `scripts/run-cursor-handoff.sh`

Extend `notify()`:

1. Existing Telegram path unchanged when chat id available
2. Additionally call `scripts/slack-notify.sh` / `lib.slack_notify.send_message` when:
   - `HERMES_NOTIFY_SLACK=1`, or
   - `SLACK_HOME_CHANNEL` / routing default is set and Slack-triggered run

Message stages (keep current tone):

- 시작 (실행 중)
- 백그라운드 (pid)
- 완료 / 실패 (+ elapsed, log hint)

### 5.3 `scripts/telegram-custom.sh`

Minimal changes only if needed to accept Slack-origin env (notify channel). Prefer not to break Telegram callers.

## 6. Configuration / env

| Var | Role |
|-----|------|
| `SLACK_BOT_TOKEN` | Existing Slack Web API |
| `SLACK_HOME_CHANNEL` | Default notify + free-response channel |
| `HERMES_CURSOR_AUTO` | `1` run CLI after HANDOFF; `0` skip CLI |
| `HERMES_NOTIFY_SLACK` | Prefer Slack notify from handoff runner |
| `TELEGRAM_CHAT_ID` | Existing Telegram notify (optional coexistence) |

No new OAuth app in this design.

## 7. Validation / DoD

1. `setup-slack-routing.sh` → `quick_commands` contains `cursor`
2. `cursor-handoff.sh` / routing points at HANDOFF-producing path
3. `run-cursor-handoff.sh --dry-run --latest` succeeds (or clear skip if no HANDOFF)
4. Slack notify dry: token missing → warn/skip without hard fail in dry-run; live smoke optional
5. `/automate` and `/handoff` semantics unchanged
6. `.harness/progress.md` updated

## 8. Out of scope

- New Slack App creation / token rotation
- Changing personal `/automate`
- Changing session `/handoff`
- Cursor Cloud Agents / auto-PR
- Removing Telegram handoff path

## 9. Rollback

- Remove `cursor` from `slack-routing.yaml` and re-run `setup-slack-routing.sh`
- Revert dual notify in `run-cursor-handoff.sh` to Telegram-only

## 10. Risks / mitigations

| Risk | Mitigation |
|------|------------|
| Codex unavailable → no HANDOFF | Same as Telegram: notify “HANDOFF 없음”; CLI skip |
| Slack token missing | Warn; do not break Telegram path |
| Name collision `/handoff` vs `/cursor` | Prompt docs clarify session vs Cursor |
| Duplicate Codex logic | Thin wrapper only |

## 11. Implementation note

After this spec is reviewed, create an implementation plan via `writing-plans`, then execute (subagent-driven or inline per user choice).
