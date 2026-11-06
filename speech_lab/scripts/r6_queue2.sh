#!/usr/bin/env bash
# round-6 second queue: warm-start (2 s history) runs.  Resumable.
cd "$(dirname "$0")/.."; . .venv/bin/activate
lane=$1
if [ "$lane" = W ]; then
  python -m selab.run_r6 --tag r5 --items sub48 --warm --methods sd8_rt,sd4_rt,ds_td_rt,ds_td_r5t,gm4_rt,rtf4_rt,gm8_rt,rtf8_rt,sd8_r5t,gm4_ref,rtf4_ref
  python -m selab.trk_eval_r6 --tag r5 --warm --items sub48 --modes r5t,rtn,rt
  python -m selab.run_r6 --tag r5sim --items sub48 --methods gm8_rt,rtf8_rt
fi
if [ "$lane" = S ]; then
  python -m selab.score_r6 --tag r5 --items sub48 --asr --methods sd8_rt__warm,sd4_rt__warm,ds_td_rt__warm,ds_td_r5t__warm,gm4_rt__warm,rtf4_rt__warm,gm8_rt__warm,rtf8_rt__warm,sd8_r5t__warm,gm4_ref__warm,rtf4_ref__warm
fi
if [ "$lane" = T ]; then   # ASR: holdout tuning set, then warm panel
  python -m selab.holdout_r6 asr tune 1 2
  python -m selab.holdout_r6 asr tune 0 2
  python -m selab.score_r6 --tag r5 --items sub48 --asr --methods sd8_rt__warm,sd4_rt__warm,ds_td_rt__warm,ds_td_r5t__warm,gm4_rt__warm,rtf4_rt__warm,gm8_rt__warm,rtf8_rt__warm,sd8_r5t__warm,gm4_ref__warm,rtf4_ref__warm
fi
