#!/bin/sh
# Redis (in-memory only) in the background, then the API on the port Spaces expects.
redis-server --save "" --appendonly no --dir /tmp --daemonize yes >/dev/null
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-7860}"
