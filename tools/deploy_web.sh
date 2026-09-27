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
if [ -n "${STATUS_READ_TOKEN:-}" ]; then
  if curl -fsS --max-time 30 -H "Authorization: Bearer $STATUS_READ_TOKEN" \
    "$SITE/status.json" -o status.json; then
    echo "  preserved $(python3 -c 'import json,sys;print(len(json.load(open("status.json"))["runs"]))' 2>/dev/null || echo '?') run(s)"
  else
    echo "  no live status yet, starting fresh"
    printf '{\n  "generated_at": null,\n  "runs": []\n}\n' > status.json
  fi
else
  echo "  STATUS_READ_TOKEN missing, leaving status.json as is"
fi

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
echo "Done. Live history preserved."
