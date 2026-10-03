#!/usr/bin/env sh
set -eu

echo "Starting FinGraph QRIS backend: APP_ENV=${APP_ENV:-unset} DEMO_MODE=${DEMO_MODE:-unset}"
exec "$@"
