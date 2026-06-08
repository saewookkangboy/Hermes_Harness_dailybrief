#!/usr/bin/env bash
# [비활성] ESP 발송 — Notion 붙여넣기 팩 워크플로로 대체됨
# Usage: ./newsletter-send.sh → 안내 메시지
set -euo pipefail

echo "ℹ️  ESP/API 자동 발송은 사용하지 않습니다." >&2
echo "   Notion 붙여넣기 팩: content/packages/*_newsletter-paste.md" >&2
echo "   생성: scripts/run-newsletter.sh YYYY-MM-DD --validate" >&2
echo "   동기화: scripts/archive-to-notion.sh YYYY-MM-DD --force" >&2
exit 0
