#!/usr/bin/env bash
# after r6_test.sh (pid 1263): objective metrics (indicative) then idle timing benchmark, one at a time
cd "$(dirname "$0")/.."; . .venv/bin/activate
while kill -0 1263 2>/dev/null; do sleep 20; done
python -m selab.score_r6 --tag r5 --items sub48 --methods ds_td_rt,sd4_rt,sd8_rt,sd4_ref,sd8_ref,gm4_rt,gm4_ref,rtf4_rt,rtf4_ref,sd4_rt__v15m,sd8_rt__v15m --workers 2
echo OBJ_DONE
python -m selab.timing_r6
echo TIMING_DONE
