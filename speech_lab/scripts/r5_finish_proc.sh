#!/usr/bin/env bash
# Round-5 finishing lane P (processing), one heavy job at a time; resumable.
cd "$(dirname "$0")/.."; . .venv/bin/activate
r() { echo "== $(date -u +%T) $*"; python -m selab.run_r5 --resume "$@" 2>&1 | grep -E '^\{|FAIL|Error'; }
r --method mvdr_online_est_dfn3 --tag r5
r --method noisy --tag r5sim
r --method ds_est --tag r5sim
r --method mvdr_online_est --tag r5sim
r --method deepfilternet3 --tag r5sim
r --method mvdr_online_est_tse --tag r5 --items sub48
r --method tse --tag r5sim --items sub48
echo "== $(date -u +%T) objective"; python -m selab.score_r5 --tag r5 2>&1 | tail -n 3; python -m selab.score_r5 --tag r5sim 2>&1 | tail -n 3
touch logs/r5_proc_core.done
r --method mvdr_online_est_tse --tag r5
r --method tse --tag r5sim
python -m selab.score_r5 --tag r5 2>&1 | tail -n 3; python -m selab.score_r5 --tag r5sim 2>&1 | tail -n 3
touch logs/r5_proc_all.done; echo "== $(date -u +%T) DONE"
