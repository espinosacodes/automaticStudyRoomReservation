#!/usr/bin/env bash
# Deploy the status page without wiping the live reservation history.
#
# A plain `wrangler deploy` uploads whatever snapshot sits in
# apps/web/public/status.json, which is the empty committed placeholder. That
# silently erases every published run. This script pulls the current status from
# the live site first (it is auth gated, so it needs STATUS_READ_TOKEN from the
# local .env), builds with it, deploys, then restores the placeholder.
#
# Usage: tools/deploy_web.sh
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
SITE="${SITE_URL:-https://reservation.getcuria.us}"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  . ./.env
  set +a
fi

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "CLOUDFLARE_API_TOKEN is not set (expected in .env)" >&2
  exit 1
fi

echo "Fetching current status from $SITE"
printf '{\n  "generated_at": null,\n  "runs": []\n}\n' > status.live.json
if [ -n "${STATUS_READ_TOKEN:-}" ]; then
  if curl -fsS --max-time 30 -H "Authorization: Bearer $STATUS_READ_TOKEN" \
    "$SITE/status.json" -o status.live.json; then
    echo "  fetched live snapshot"
  else
    echo "  no live status yet"
  fi
else
  echo "  STATUS_READ_TOKEN missing"
fi

# Merge rather than replace: local history stays, and the live snapshot can
# only add to it. Replacing is what silently erased earlier runs.
if [ -f status.json ]; then
  .venv/bin/python -m tools.merge_status status.json status.live.json -o status.json
else
  cp status.live.json status.json
fi
rm -f status.live.json

if [ -f status.json ]; then
  cp status.json apps/web/public/status.json
fi
if ls bookings/*.pdf >/dev/null 2>&1; then
  mkdir -p apps/web/public/bookings
  cp bookings/*.pdf apps/web/public/bookings/
fi

pnpm --filter web build
pnpm exec wrangler deploy

# Restore the committed placeholder so the repo stays clean.
git checkout -- apps/web/public/status.json 2>/dev/null || \
  printf '{\n  "generated_at": null,\n  "runs": []\n}\n' > apps/web/public/status.json
rm -rf apps/web/public/bookings
rm -f status.live.json
echo "Done. Live history preserved."
