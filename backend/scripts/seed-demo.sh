#!/usr/bin/env sh
set -eu

if [ "${DEMO_MODE:-false}" != "true" ]; then
  echo "Refusing demo seed because DEMO_MODE is not true." >&2
  exit 2
fi
python -m app.db.seeds.seed
echo "Idempotent demo seed complete."
