#!/usr/bin/env bash
# Run on the deployment server. No deletion, no off-host transfer, no secret output.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
umask 077
docker compose --env-file deploy/production.env -f deploy/compose.production.yaml \
  --profile maintenance run --rm --no-deps backup
echo 'Verified SQLite and scraper backup created. Copy it to private off-host storage.'
