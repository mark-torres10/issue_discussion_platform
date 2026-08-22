#!/usr/bin/env bash
# Operator smoke for a deployed Study API: /health and participant exchange + session read.
# Set SMOKE_BASE_URL and SMOKE_INVITATION_TOKEN when testing production postgres.
set -euo pipefail

BASE_URL="${SMOKE_BASE_URL:-https://api-production-198a.up.railway.app}"
BASE_URL="${BASE_URL%/}"
TOKEN="${SMOKE_INVITATION_TOKEN:-demo-campus-speech-001-invitation-token-for-contract-tests}"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

manual_hint() {
  cat <<'EOF'
Manual smoke (no secrets required for health):
  curl -s https://api-production-198a.up.railway.app/health

For participant exchange, set SMOKE_INVITATION_TOKEN to a valid invitation on that API.
See docs/runbooks/deploy/STUDY_API_ENV.md
EOF
}

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for smoke_study_api.sh"
  manual_hint
  exit 1
fi

if ! curl -sf "${BASE_URL}/health" >/dev/null; then
  echo "FAIL health (${BASE_URL}/health)"
  manual_hint
  exit 1
fi
echo "OK health"

exchange_status="$(
  curl -s -o /dev/null -w '%{http_code}' -c "$COOKIE_JAR" -X POST \
    "${BASE_URL}/v1/participant-access/exchange" \
    -H 'Content-Type: application/json' \
    -d "{\"invitation_token\":\"${TOKEN}\"}" || true
)"

if [ "$exchange_status" != "200" ]; then
  if [ -z "${SMOKE_INVITATION_TOKEN:-}" ]; then
    echo "SKIP exchange: set SMOKE_INVITATION_TOKEN for postgres-backed APIs (got HTTP ${exchange_status})"
    manual_hint
    exit 0
  fi
  echo "FAIL exchange (HTTP ${exchange_status})"
  exit 1
fi
echo "OK exchange"

if ! curl -sf -b "$COOKIE_JAR" "${BASE_URL}/v1/participant-session" >/dev/null; then
  echo "FAIL session read"
  exit 1
fi
echo "OK session read"
