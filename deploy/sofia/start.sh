#!/bin/sh
set -eu

mkdir -p /app/data /run/nginx
if [ ! -f /app/data/.migrated ]; then
  cd /app/backend
  alembic upgrade head
  touch /app/data/.migrated
fi

cd /app/backend
uvicorn src.main:app --host 127.0.0.1 --port 8000 --workers 2 &
backend_pid=$!

cd /app/frontend
npm start -- -p 3000 &
frontend_pid=$!

# tunnel: token lives in /app/data/.tunnel-token (mounted volume); no file, no tunnel
tunnel_pid=""
if [ -f /app/data/.tunnel-token ]; then
  (while true; do cloudflared tunnel --no-autoupdate run --token "$(cat /app/data/.tunnel-token)"; sleep 5; done) &
  tunnel_pid=$!
fi

cleanup() {
  kill "$backend_pid" "$frontend_pid" $tunnel_pid 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

nginx -g 'daemon off;'
