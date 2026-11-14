#!/usr/bin/env bash
# restart the local backend so every load-test run starts on a clean server.
#
# used through run_tests.sh:   RESTART_CMD=./restart_backend.sh ./run_tests.sh local
# why: an overloaded server keeps working through requests the client already gave up on, so one
# overloaded run (for example 300 users logging in at once) would otherwise spoil the runs after it.
# stops whatever listens on port 9160, starts uvicorn again with a high open-files limit and
# waits until /health answers. logs are appended to loadtest/backend.log.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-9160}"

pids="$(lsof -ti "tcp:$PORT" -sTCP:LISTEN || true)"
if [[ -n "$pids" ]]; then
  kill $pids || true
  for _ in $(seq 1 20); do lsof -ti "tcp:$PORT" -sTCP:LISTEN >/dev/null || break; sleep 0.5; done
fi

ulimit -n 10240
nohup backend/venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port "$PORT" \
  >> loadtest/backend.log 2>&1 &

for _ in $(seq 1 60); do
  if curl -fs -m 2 "http://127.0.0.1:$PORT/health" >/dev/null; then echo "backend restarted"; exit 0; fi
  sleep 1
done
echo "backend did not come up; see loadtest/backend.log" >&2
exit 1
