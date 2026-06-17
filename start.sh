#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  ResumeIntel — one-command dev launcher
#  Usage: ./start.sh
#
#  Starts:  Redis  →  FastAPI backend (port 8000)  →  Vite frontend (port 5173)
#  Checks GitHub for a newer commit and asks if you want to pull first.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

CYAN='\033[0;36m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${CYAN}▶  $*${NC}"; }
ok()    { echo -e "${GREEN}✓  $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠  $*${NC}"; }
err()   { echo -e "${RED}✗  $*${NC}"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          ResumeIntel  Dev Launcher           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── 0. Check for .env ────────────────────────────────────────────────────────
if [ ! -f "$ROOT/.env" ]; then
  warn ".env not found — copying from .env.example"
  cp "$ROOT/.env.example" "$ROOT/.env"
  warn "Open .env and add your OPENAI_API_KEY before the backend can call the LLM."
fi

# ── 1. GitHub latest-commit check ────────────────────────────────────────────
info "Checking GitHub for new commits…"
if git -C "$ROOT" fetch origin main --quiet 2>/dev/null; then
  LOCAL=$(git -C "$ROOT" rev-parse HEAD)
  REMOTE=$(git -C "$ROOT" rev-parse origin/main)

  if [ "$LOCAL" != "$REMOTE" ]; then
    COMMIT_MSG=$(git -C "$ROOT" log origin/main -1 --format="%s  (%cr)")
    COMMIT_AUTHOR=$(git -C "$ROOT" log origin/main -1 --format="%an")
    echo ""
    echo -e "${YELLOW}┌─────────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│  New commit found on GitHub main            │${NC}"
    echo -e "${YELLOW}│                                             │${NC}"
    echo -e "${YELLOW}│  📝  $COMMIT_MSG${NC}"
    echo -e "${YELLOW}│  👤  $COMMIT_AUTHOR${NC}"
    echo -e "${YELLOW}└─────────────────────────────────────────────┘${NC}"
    echo ""
    read -r -p "  Pull this commit before starting? [y/N] " PULL_ANSWER
    if [[ "$PULL_ANSWER" =~ ^[Yy]$ ]]; then
      git -C "$ROOT" pull origin main
      ok "Pulled latest from GitHub"
    else
      warn "Skipping pull — running with local code"
    fi
  else
    ok "Already up to date with GitHub ($(git -C "$ROOT" log -1 --format='%h %s'))"
  fi
else
  warn "Could not reach GitHub — skipping remote check"
fi
echo ""

# ── 2. Redis ─────────────────────────────────────────────────────────────────
info "Starting Redis…"

if command -v redis-server &>/dev/null; then
  # Check if Redis is already running
  if redis-cli ping &>/dev/null; then
    ok "Redis already running"
  else
    redis-server --daemonize yes --logfile /tmp/redis-resumeintel.log
    sleep 0.5
    if redis-cli ping &>/dev/null; then
      ok "Redis started (native)"
    else
      err "Redis failed to start — check /tmp/redis-resumeintel.log"; exit 1
    fi
  fi
elif command -v docker &>/dev/null; then
  if docker ps --filter "name=resumeintel-redis" --format "{{.Names}}" | grep -q "resumeintel-redis"; then
    ok "Redis container already running"
  else
    docker run -d --name resumeintel-redis --rm -p 6379:6379 redis:7-alpine &>/dev/null
    sleep 1
    ok "Redis started (Docker)"
  fi
else
  err "Redis not found — install via 'brew install redis' or start Docker"
  echo "  Alternatively run: docker-compose up redis -d"
  exit 1
fi

# ── 3. Backend ────────────────────────────────────────────────────────────────
info "Starting FastAPI backend on :8000…"

VENV="$ROOT/.venv"
if [ ! -f "$VENV/bin/uvicorn" ]; then
  warn "No .venv found — creating and installing dependencies…"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -e ".[dev]" 2>/dev/null || "$VENV/bin/pip" install -q -r requirements.txt 2>/dev/null || "$VENV/bin/pip" install -q $(python3 -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(' '.join(d['project']['dependencies']))" 2>/dev/null || cat pyproject.toml | grep '"' | grep -v '#' | grep -v '\[' | tr -d '",' | xargs)
fi

# Kill any existing backend
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

LOG_BACKEND="/tmp/resumeintel-backend.log"
"$VENV/bin/uvicorn" src.api:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir src \
  --log-level info \
  > "$LOG_BACKEND" 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready (up to 20s)
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/docs &>/dev/null; then
    ok "Backend ready — http://localhost:8000  (pid $BACKEND_PID)"
    break
  fi
  if [ $i -eq 20 ]; then
    err "Backend didn't start in 20s — check $LOG_BACKEND"
    cat "$LOG_BACKEND" | tail -20
    exit 1
  fi
  sleep 1
done

# ── 4. Frontend ───────────────────────────────────────────────────────────────
info "Starting Vite frontend on :5173…"

FRONTEND="$ROOT/frontend"
if [ ! -d "$FRONTEND/node_modules" ]; then
  warn "node_modules missing — installing…"
  if command -v npm &>/dev/null; then
    (cd "$FRONTEND" && npm install)
  elif command -v pnpm &>/dev/null; then
    (cd "$FRONTEND" && pnpm install)
  else
    err "Node/npm not found — install via 'brew install node' first"; exit 1
  fi
fi

# Kill any existing frontend
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

LOG_FRONTEND="/tmp/resumeintel-frontend.log"

if command -v npm &>/dev/null; then
  (cd "$FRONTEND" && npm run dev > "$LOG_FRONTEND" 2>&1) &
elif command -v pnpm &>/dev/null; then
  (cd "$FRONTEND" && pnpm dev > "$LOG_FRONTEND" 2>&1) &
else
  err "Node/npm not found — install via: brew install node"; exit 1
fi
FRONTEND_PID=$!

# Wait for frontend (up to 15s)
for i in $(seq 1 15); do
  if curl -sf http://localhost:5173 &>/dev/null; then
    ok "Frontend ready — http://localhost:5173  (pid $FRONTEND_PID)"
    break
  fi
  if [ $i -eq 15 ]; then
    err "Frontend didn't start in 15s — check $LOG_FRONTEND"
    cat "$LOG_FRONTEND" | tail -20
    exit 1
  fi
  sleep 1
done

# ── 5. Done ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            All services running ✓            ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  🖥   Frontend  →  http://localhost:5173      ║${NC}"
echo -e "${GREEN}║  ⚙   Backend   →  http://localhost:8000      ║${NC}"
echo -e "${GREEN}║  📖  API docs  →  http://localhost:8000/docs ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Backend log:  ${CYAN}tail -f $LOG_BACKEND${NC}"
echo -e "  Frontend log: ${CYAN}tail -f $LOG_FRONTEND${NC}"
echo ""
echo -e "  Press ${RED}Ctrl+C${NC} to stop all services"
echo ""

# ── 6. Ctrl+C cleanup ────────────────────────────────────────────────────────
cleanup() {
  echo ""
  warn "Shutting down…"
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  # Stop Docker Redis if we started it
  docker stop resumeintel-redis 2>/dev/null || true
  ok "Done"
}
trap cleanup INT TERM

# Keep script alive (log output from both services)
tail -f "$LOG_BACKEND" "$LOG_FRONTEND" &
wait $BACKEND_PID $FRONTEND_PID
