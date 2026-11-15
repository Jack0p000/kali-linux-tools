#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv 2>/dev/null || true
. .venv/bin/activate
if ! .venv/bin/python -c "import flask" >/dev/null 2>&1; then
  pip install -q -r requirements.txt
fi
PORT="${NETSCOPE_PORT:-5050}"
URL="http://127.0.0.1:${PORT}"
open_dashboard() {
  if command -v google-chrome >/dev/null 2>&1; then
    google-chrome --new-window "$URL" >/dev/null 2>&1 &
  elif command -v google-chrome-stable >/dev/null 2>&1; then
    google-chrome-stable --new-window "$URL" >/dev/null 2>&1 &
  else
    xdg-open "$URL" >/dev/null 2>&1 &
  fi
}
if curl -fsS --max-time 1 "$URL/" >/dev/null 2>&1; then
  echo "NetScope è già attivo sulla porta $PORT."
  open_dashboard
  exit 0
fi
PID=""
cleanup() {
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo
    echo "Chiusura NetScope (PID $PID)..."
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM HUP
.venv/bin/python webapp.py &
PID=$!
for _ in {1..30}; do
  if curl -fsS --max-time 1 "$URL/" >/dev/null 2>&1; then break; fi
  if ! kill -0 "$PID" 2>/dev/null; then wait "$PID"; exit $?; fi
  sleep 0.2
done
open_dashboard
wait "$PID"
