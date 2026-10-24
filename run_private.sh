#!/usr/bin/env bash
# ResumeIntel, private mode: the whole product (API + built UI) on this machine, reachable from
# anywhere through a free Cloudflare quick tunnel. Free, no accounts, and with Ollama your
# resume never leaves this laptop. It is only reachable while this script is running.
#
#   ./run_private.sh            # start
#   Ctrl+C                      # stop everything
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT"
PORT="${PORT:-8010}"
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
ok(){ echo -e "${G}✓ $*${N}"; }; warn(){ echo -e "${Y}⚠ $*${N}"; }; die(){ echo -e "${R}✗ $*${N}"; exit 1; }

command -v docker >/dev/null || die "Docker is needed for Redis (or run redis-server yourself)."
command -v cloudflared >/dev/null || die "Install the tunnel first:  brew install cloudflared"
command -v uv >/dev/null || die "Install uv first:  brew install uv"
lsof -ti:"$PORT" >/dev/null 2>&1 && die "Port $PORT is in use. Free it or run: PORT=8020 ./run_private.sh"

# ── .env: access key + local-model defaults (kept out of git) ──────────────
touch .env
setenv(){ grep -q "^$1=" .env || echo "$1=$2" >> .env; }
setenv API_SECRET_KEY "$(openssl rand -hex 24)"
setenv LLM_PROVIDER ollama
setenv OLLAMA_MODEL qwen2.5:3b
setenv REDIS_TTL_SECONDS 604800
if grep -q "^LLM_PROVIDER=ollama" .env; then
  curl -s localhost:11434/api/tags >/dev/null || warn "Ollama is not running — start it (ollama serve) or set OPENAI_API_KEY and LLM_PROVIDER=openai in .env"
fi

# ── frontend (same-origin API, so the tunnel URL can change freely) ────────
if [ ! -d frontend/node_modules ]; then (cd frontend && npm install --silent); fi
(cd frontend && VITE_API_URL=/api/v1 npm run build --silent) && ok "UI built"

# ── redis ───────────────────────────────────────────────────────────────────
docker rm -f resumeintel-redis >/dev/null 2>&1 || true
docker run -d --name resumeintel-redis -p 127.0.0.1:6379:6379 redis:7-alpine >/dev/null && ok "Redis up"

# ── app ─────────────────────────────────────────────────────────────────────
set -a; . ./.env; set +a
export FRONTEND_DIST="$ROOT/frontend/dist" CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:$PORT}"
uv run uvicorn src.main:app --host 127.0.0.1 --port "$PORT" > /tmp/resumeintel-app.log 2>&1 &
APP=$!
for _ in $(seq 1 60); do curl -sf "localhost:$PORT/health" >/dev/null && break; sleep 1; done
curl -sf "localhost:$PORT/health" >/dev/null || { tail -20 /tmp/resumeintel-app.log; die "App did not start"; }
ok "App on http://localhost:$PORT"

# ── tunnel ──────────────────────────────────────────────────────────────────
cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" > /tmp/resumeintel-tunnel.log 2>&1 &
TUN=$!
URL=""
for _ in $(seq 1 40); do
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/resumeintel-tunnel.log | head -1 || true)
  [ -n "$URL" ] && break; sleep 1
done
[ -n "$URL" ] || { tail -10 /tmp/resumeintel-tunnel.log; die "Tunnel did not come up"; }

echo
echo -e "${G}════════════════════════════════════════════════${N}"
echo -e "${G}  Open from anywhere:  $URL${N}"
echo -e "${G}  On this machine:     http://localhost:$PORT${N}"
echo -e "${G}  Access key:          grep API_SECRET_KEY .env${N}"
echo -e "${G}════════════════════════════════════════════════${N}"
echo "  The link changes each time you start this. Ctrl+C stops everything."

cleanup(){ kill $APP $TUN 2>/dev/null || true; docker rm -f resumeintel-redis >/dev/null 2>&1 || true; echo "stopped"; }
trap cleanup INT TERM EXIT
wait $APP
