#!/usr/bin/env bash
# Gate D — CTOR 학습 강화(시드 제외·패턴 가중치·보조 지표) + E2E
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

echo "=== Newsletter Gate D — $STAMP ==="
export HERMES_ENHANCE=0

METRICS="$WORKDIR/.harness/newsletter-ctor-metrics.json"
FEEDBACK="$WORKDIR/.harness/newsletter-ctor-feedback.json"
CHANNELS="$WORKDIR/.harness/channel-metrics.json"
BACKUP_DIR=$(mktemp -d)
restore_metrics() {
  for f in newsletter-ctor-metrics.json newsletter-ctor-feedback.json channel-metrics.json; do
    if [[ -f "$BACKUP_DIR/$f" ]]; then
      cp "$BACKUP_DIR/$f" "$WORKDIR/.harness/$f"
    else
      rm -f "$WORKDIR/.harness/$f"
    fi
  done
}
trap 'restore_metrics; rm -rf "$BACKUP_DIR"' EXIT
for f in "$METRICS" "$FEEDBACK" "$CHANNELS"; do
  [[ -f "$f" ]] && cp "$f" "$BACKUP_DIR/$(basename "$f")"
done

python3 - "$DIR" "$WORKDIR" "$STAMP" <<'PY'
import json
import sys
from pathlib import Path

DIR, WORKDIR, stamp = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, DIR)

from lib.newsletter_ctor import (
    METRICS_PATH,
    is_seed_record,
    real_records,
    record_campaign,
    save_metrics,
)
from lib.newsletter_ctor_feedback import (
    FEEDBACK_PATH,
    apply_ctor_feedback_bonus,
    compute_ctor_feedback,
    pattern_bonus,
    preferred_pattern_ids,
)
from lib.newsletter_quality import load_newsletter_config
from lib.newsletter_select import _pick_pattern_id

pass_n = fail_n = 0


def check(name, ok, detail=""):
    global pass_n, fail_n
    print(("PASS " if ok else "FAIL ") + name + (f" {detail}" if detail else ""))
    if ok:
        pass_n += 1
    else:
        fail_n += 1


cfg = load_newsletter_config()

# --- AE8: 시드만 있을 때 학습 금지 -------------------------------------------
seed_only = {
    "version": 1,
    "records": [
        {
            "stamp": "2026-06-09",
            "subject": "한국 AX 전환 — 지금 손댈 곳은?",
            "pattern_id": "question",
            "delivered": 500,
            "unique_opens": 112,
            "unique_clicks": 14,
            "open_rate_pct": 22.4,
            "ctor_pct": 12.5,
            "ctor_health": "healthy",
            "notes": "p4-eval-seed",
        },
        {
            "stamp": "2026-06-08",
            "subject": "한국 AX 전환, 3분이면 돼요",
            "pattern_id": "number",
            "delivered": 500,
            "unique_opens": 112,
            "unique_clicks": 14,
            "open_rate_pct": 22.4,
            "ctor_pct": 12.5,
            "ctor_health": "healthy",
            "notes": "p4-eval-seed",
        },
    ],
}
save_metrics(seed_only)
FEEDBACK_PATH.unlink(missing_ok=True)
fb = compute_ctor_feedback()
check("seed_only_not_applied", fb.get("applied") is False, str(fb.get("reason")))
check("seed_only_no_weights", not fb.get("weights") and not fb.get("pattern_weights"))
check("seed_excluded_counted", fb.get("excluded_seed_count") == 2, str(fb.get("excluded_seed_count")))
check("seed_records_filtered", real_records() == [], f"real={len(real_records())}")
bonus, reasons = apply_ctor_feedback_bonus("AEO 실무 — 지금 손댈 곳은?", fb)
check("seed_static_weights_only", bonus == 0 and not reasons, f"bonus={bonus}")

# --- R24/R25: 보조 지표 기록 --------------------------------------------------
save_metrics({"version": 1, "records": []})
row = record_campaign(
    "2026-07-20",
    delivered=1000,
    unique_opens=250,
    unique_clicks=30,
    replies=12,
    unsubscribes=8,
    subject="AEO 실무 — 지금 손댈 곳은?",
    pattern_id="question",
    notes="gate-d-eval real check",
    seed=False,
)
check("ctr_computed", row["ctr_pct"] == 3.0, f"ctr={row['ctr_pct']}")
check("reply_rate_computed", row["reply_rate_pct"] == 1.2, f"reply={row['reply_rate_pct']}")
check("unsub_rate_computed", row["unsub_rate_pct"] == 0.8, f"unsub={row['unsub_rate_pct']}")
check("unsub_high_flagged", "unsub_high" in row["health_flags"], str(row["health_flags"]))
check("reply_ok_flagged", "reply_ok" in row["health_flags"])
check("pattern_id_persisted", row["pattern_id"] == "question")

# --- R26: 패턴별 가중치 -------------------------------------------------------
real_rows = []
for i, (st, pid, subj, clicks) in enumerate(
    [
        ("2026-07-20", "question", "AEO 실무 — 지금 손댈 곳은?", 34),
        ("2026-07-13", "question", "에이전트 도입 — 지금 손댈 곳은?", 33),
        ("2026-07-06", "question", "AX 예산 승인 — 지금 손댈 곳은?", 35),
        ("2026-06-29", "noun", "AEO 체크리스트", 15),
        ("2026-06-22", "noun", "에이전트 체크리스트", 14),
    ]
):
    real_rows.append(
        record_campaign(
            st,
            delivered=1000,
            unique_opens=250,
            unique_clicks=clicks,
            replies=12,
            unsubscribes=2,
            subject=subj,
            pattern_id=pid,
            notes="gate-d real",
            seed=False,
        )
    )
fb = compute_ctor_feedback()
check("real_records_learn", fb.get("applied") is True, str(fb.get("reason")))
check("pattern_weights_present", bool(fb.get("pattern_weights")), str(fb.get("pattern_weights")))
q_w, n_w = pattern_bonus("question", fb), pattern_bonus("noun", fb)
check("strong_pattern_outranks_weak", q_w > 0 > n_w, f"question={q_w} noun={n_w}")
check("preferred_pattern_top", (preferred_pattern_ids(fb) or [""])[0] == "question", str(preferred_pattern_ids(fb)))

# --- R26: 연속 사용 한도 유지 --------------------------------------------------
picked = _pick_pattern_id("2026-07-27", [{"pattern_id": "question"}], cfg)
check("pattern_streak_respected", picked != "question", f"picked={picked}")
picked2 = _pick_pattern_id("2026-07-27", [{"pattern_id": "noun"}], cfg)
check("preferred_pattern_used", picked2 == "question", f"picked={picked2}")

# --- 시드 혼합 시에도 실측만 학습 -----------------------------------------------
mixed = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
mixed["records"].extend(seed_only["records"])
save_metrics(mixed)
fb_mixed = compute_ctor_feedback()
check(
    "mixed_excludes_seed",
    fb_mixed.get("excluded_seed_count") == 2 and fb_mixed.get("sample_size") == 5,
    f"seeds={fb_mixed.get('excluded_seed_count')} sample={fb_mixed.get('sample_size')}",
)
check("seed_flag_detected", all(is_seed_record(r) for r in seed_only["records"]))

print(f"=== Gate D Learning PASS={pass_n} FAIL={fail_n} ===")
raise SystemExit(0 if fail_n == 0 else 1)
PY

echo ""
# 시험 원장이 산출물에 새어 들어가지 않도록 E2E 전에 실제 상태로 복원
restore_metrics
python3 -c "import sys; sys.path.insert(0, '$DIR'); from lib.newsletter_ctor_feedback import compute_ctor_feedback; compute_ctor_feedback()"

echo "--- Gate D E2E ---"
E2E_FAIL=0
"$DIR/run-newsletter.sh" "$STAMP" --validate >/dev/null 2>&1 && echo "PASS e2e_run_newsletter" || { echo "FAIL e2e_run_newsletter"; E2E_FAIL=1; }
"$DIR/newsletter-freshness-eval.sh" "$STAMP" >/dev/null 2>&1 && echo "PASS e2e_gate_a" || { echo "FAIL e2e_gate_a"; E2E_FAIL=1; }
"$DIR/newsletter-gate-b-eval.sh" "$STAMP" >/dev/null 2>&1 && echo "PASS e2e_gate_b" || { echo "FAIL e2e_gate_b"; E2E_FAIL=1; }
"$DIR/newsletter-gate-c-eval.sh" "$STAMP" >/dev/null 2>&1 && echo "PASS e2e_gate_c" || { echo "FAIL e2e_gate_c"; E2E_FAIL=1; }
"$DIR/newsletter-eval.sh" "$STAMP" >/dev/null 2>&1 && echo "PASS e2e_newsletter_eval" || { echo "FAIL e2e_newsletter_eval"; E2E_FAIL=1; }

if [[ "$E2E_FAIL" -eq 0 ]]; then
  echo "=== Gate D Result PASS ==="
else
  echo "=== Gate D Result FAIL ==="
  exit 1
fi
