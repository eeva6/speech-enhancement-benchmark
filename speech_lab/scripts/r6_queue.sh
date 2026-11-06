#!/usr/bin/env bash
# round-6 job queue used during the run (two lanes; each lane is sequential and resumable)
cd "$(dirname "$0")/.."; . .venv/bin/activate
lane=$1
if [ "$lane" = A ]; then   # processing lane
  python -m selab.holdout_r6 proc tune
  python -m selab.run_r6 --tag r5sim --items sub48 --methods ds_td_rt,ds_td_ref,sd4_rt,sd4_ref,sd8_rt,sd8_ref,gm4_rt,gm4_ref,rtf4_rt,rtf4_ref
fi
if [ "$lane" = B ]; then   # ASR lane
  python -m selab.score_r6 --tag r5 --items sub48 --asr --methods ds_td_rt,ds_td_rtn,sd4_rt,sd8_rt,gm4_rt,rtf4_rt,gm8_rt,rtf8_rt
  python -m selab.score_r6 --tag r5 --items sub48 --methods ds_td_r5t,ds_td_rtn,ds_td_rt,ds_td_ref,ds_td_blind,sd4_rt,sd4_ref,sd8_rt,sd8_ref,gm4_rt,gm4_ref,gm8_rt,gm8_ref,rtf4_rt,rtf4_ref,rtf8_rt,rtf8_ref
  python -m selab.holdout_r6 asr tune 0 1
fi
