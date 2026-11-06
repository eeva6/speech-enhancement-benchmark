#!/usr/bin/env bash
# Round-5 lane P, final part: critique sensitivity runs, then the DFN3 Rust build + frame timing (lowest priority).
# Full-144 runs of DFN3 and the two cascades were CUT (CPU/time budget); those methods have n = 48 (sub48).
cd "$(dirname "$0")/.."; . .venv/bin/activate
while kill -0 3326 2>/dev/null; do sleep 15; done
r() { echo "== $(date -u +%T) $*"; python -m selab.run_r5 --resume "$@" 2>&1 | grep -E '^\{|FAIL|Error'; }
r --method mvdr_online_est --tag r5ctx; python -m selab.sens_r5 cut mvdr_online_est
r --method tse_dryenrol --tag r5 --items sub48
echo "== $(date -u +%T) sens_ref"; python -m selab.sens_ref_r5 2>&1 | tail -n 8
r --method tse --tag r5ctx; python -m selab.sens_r5 cut tse
r --method rnnoise --tag r5 --items sub48
echo "== $(date -u +%T) rtf_cpu"; python -m selab.rtf_cpu_r5 3 2>&1 | grep -v -i warn | tail -n 6
python -m selab.score_r5 --tag r5 2>&1 | tail -n 1
touch logs/r5_proc_sens.done
echo "== $(date -u +%T) dfn rust build"; timeout 3000 ./scripts/build_dfn_rust.sh > logs/r5_dfn_build8.log 2>&1; tail -n 5 logs/r5_dfn_build8.log
echo "== $(date -u +%T) dfn timing"; python -m selab.dfn_timing 2>&1 | tail -n 20
touch logs/r5_proc_all.done; echo "== $(date -u +%T) DONE"
