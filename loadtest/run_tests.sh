#!/usr/bin/env bash
# run the Lab 2 JMeter tests and save one .jtl file per run.
#
#   ./run_tests.sh smoke  [host] [port] [protocol]     1 user for 15 s per plan: checks the plans work
#   ./run_tests.sh local  [host] [port] [protocol]     the real runs against your laptop (defaults 127.0.0.1 9160 http)
#   ./run_tests.sh aws    <elb-hostname> 80 http       the real runs against the deployed gateway
#
# real runs: login, job search and application submission at 100/200/300/400/500 users, then the
# assistant at 5/10/20/50 users. Results land in results/<label>/<plan>_<users>.jtl.
# make it shorter while testing, for example:  DURATION=60 RAMP=15 ./run_tests.sh local
# only some plans or user levels:              PLANS=assistant A_USERS="20 50" ./run_tests.sh local
# also make JMeter's own HTML report:           REPORT=1 ./run_tests.sh local
set -euo pipefail
cd "$(dirname "$0")"

LABEL="${1:?usage: ./run_tests.sh <smoke|local|aws> [host] [port] [protocol]}"
HOST="${2:-127.0.0.1}"
PORT="${3:-9160}"
PROTOCOL="${4:-http}"
DURATION="${DURATION:-120}"        # seconds each CRUD run lasts (including the ramp-up)
RAMP="${RAMP:-30}"                 # seconds to bring all users in
A_DURATION="${A_DURATION:-300}"    # the assistant is slow (a local model), so its runs are longer
A_RAMP="${A_RAMP:-20}"
PLANS="${PLANS:-login job_search apply assistant}"
USERS="${USERS:-100 200 300 400 500}"        # user levels for login, job search and apply
A_USERS="${A_USERS:-5 10 20 50}"              # user levels for the assistant
JMETER="${JMETER:-jmeter}"

command -v "$JMETER" >/dev/null || { echo "jmeter not found. Install it (brew install jmeter) or set JMETER=/path/to/jmeter"; exit 1; }
mkdir -p "results/$LABEL"

run() {  # run <plan> <users> <duration> <ramp> <think_ms> <timeout_ms>
  local plan="$1" users="$2" duration="$3" ramp="$4" think="$5" timeout="$6"
  local out="results/$LABEL/${plan}_${users}"
  rm -rf "$out.jtl" "${out}_report"
  echo "=== $plan: $users users, ${duration}s (ramp ${ramp}s) -> $HOST:$PORT"
  local extra=()
  [[ "${REPORT:-0}" == "1" ]] && extra=(-e -o "${out}_report")
  "$JMETER" -n -t "$plan.jmx" -l "$out.jtl" \
    -Jhost="$HOST" -Jport="$PORT" -Jprotocol="$PROTOCOL" \
    -Jusers="$users" -Jduration="$duration" -Jramp="$ramp" -Jthink_ms="$think" -Jtimeout_ms="$timeout" \
    -Jjmeter.save.saveservice.output_format=csv ${extra[@]+"${extra[@]}"} >"$out.log" 2>&1 \
    || { echo "jmeter failed; see $out.log"; exit 1; }
  grep -E "summary =" "$out.log" | tail -1 || true
}

for plan in $PLANS; do
  case "$LABEL:$plan" in
    smoke:assistant) run "$plan" 1 40 1 1000 180000 ;;
    smoke:*)         run "$plan" 1 15 1 500 60000 ;;
    *:assistant)     for u in $A_USERS;            do run "$plan" "$u" "$A_DURATION" "$A_RAMP" 3000 180000; done ;;
    *)               for u in $USERS;               do run "$plan" "$u" "$DURATION" "$RAMP" 500 60000; done ;;
  esac
done
echo "done. next: python summarize.py $LABEL"
