#!/bin/sh
echo "=== START.SH RUNNING ==="
echo "PORT env var: '$PORT'"
echo "Computed port: '${PORT:-8000}'"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
