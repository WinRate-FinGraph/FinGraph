#!/usr/bin/env sh
set -eu

python - <<'PY'
import os
import time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
deadline = time.monotonic() + int(os.getenv("DATABASE_WAIT_TIMEOUT", "60"))
last_error = None
while time.monotonic() < deadline:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("PostgreSQL ready for migration.")
        break
    except Exception as exc:
        last_error = type(exc).__name__
        time.sleep(2)
else:
    raise SystemExit(f"PostgreSQL unavailable before migration: {last_error}")
PY

alembic upgrade head
echo "Migration complete."
