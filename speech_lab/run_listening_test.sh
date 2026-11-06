#!/usr/bin/env bash
# One-command launch of the blinded listening test.
#   ./run_listening_test.sh            # round-5 set: real meeting-room recordings (15 trials, ~10 min)
#   ./run_listening_test.sh r3         # round-3 set: recorded noise (48 trials, ~25 min)
#   ./run_listening_test.sh r5 --share # also print a temporary public link (only if you want remote friends)
# Then open the printed URL. Give every listener a different participant number (0, 1, 2, ...).
# After the session:  ./run_listening_test.sh r5 --analyze
set -eu
cd "$(dirname "$0")"
SET=${1:-r5}; shift || true
if [ ! -f .venv/bin/activate ]; then echo "No .venv here. Run: bash scripts/setup_env.sh"; exit 1; fi
. .venv/bin/activate
if [ "${1:-}" = "--analyze" ]; then python listening_test.py --set "$SET" --analyze; exit; fi
DIR=results/listening_test; [ "$SET" = r5 ] && DIR=results/listening_test_r5
[ -f $DIR/plan.json ] || python listening_test.py --set "$SET" --build
PORT=7861; [ "$SET" = r5 ] && PORT=7862
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "Listening test ($SET) starting."
echo "  On this computer:          http://127.0.0.1:$PORT"
[ -n "${IP:-}" ] && echo "  Other devices on your Wi-Fi: http://$IP:$PORT"
echo "  Stop with Ctrl+C. Responses: $DIR/responses.csv"
exec python listening_test.py --set "$SET" --port $PORT "$@"
