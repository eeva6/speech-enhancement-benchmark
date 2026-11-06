#!/usr/bin/env bash
# Round-5 finishing lane P (processing, revised order incl. critique sensitivity runs); one heavy job at a time; resumable.
cd "$(dirname "$0")/.."; . .venv/bin/activate
while kill -0 18667 2>/dev/null; do sleep 20; done
r() { echo "== $(date -u +%T) $*"; python -m selab.run_r5 --resume "$@" 2>&1 | grep -E '^\{|FAIL|Error'; }
r --method mvdr_online_est --tag r5sim
r --method deepfilternet3 --tag r5sim
r --method mvdr_online_est_tse --tag r5 --items sub48
r --method tse --tag r5sim --items sub48
echo "== $(date -u +%T) objective"; python -m selab.score_r5 --tag r5 2>&1 | tail -n 2; python -m selab.score_r5 --tag r5sim 2>&1 | tail -n 2
touch logs/r5_proc_core.done
# critique sensitivity runs
for m in noisy mvdr_online_est; do r --method $m --tag r5ctx; python -m selab.sens_r5 cut $m; done
r --method tse_dryenrol --tag r5 --items sub48
echo "== $(date -u +%T) sens_ref"; python -m selab.sens_ref_r5 2>&1 | tail -n 8
r --method tse --tag r5ctx; python -m selab.sens_r5 cut tse
echo "== $(date -u +%T) rtf_cpu"; python -m selab.rtf_cpu_r5 3 2>&1 | tail -n 6
touch logs/r5_proc_sens.done
r --method mvdr_online_est_tse --tag r5
python -m selab.score_r5 --tag r5 2>&1 | tail -n 2
touch logs/r5_proc_all.done; echo "== $(date -u +%T) DONE"
