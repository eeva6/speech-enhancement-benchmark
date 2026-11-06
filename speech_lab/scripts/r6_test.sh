#!/usr/bin/env bash
# held-out test (sessions 3-5): processing then ASR in two shards; afterwards the twin ASR
cd "$(dirname "$0")/.."; . .venv/bin/activate
python -m selab.holdout_r6 proc test
python -m selab.holdout_r6 asr test 1 2 &
python -m selab.holdout_r6 asr test 0 2
wait
python -m selab.score_r6 --tag r5sim --items sub48 --asr --methods sd8_rt,sd4_rt,ds_td_rt,sd8_ref,sd4_ref,gm4_rt --shard 1 --nshard 2 &
python -m selab.score_r6 --tag r5sim --items sub48 --asr --methods sd8_rt,sd4_rt,ds_td_rt,sd8_ref,sd4_ref,gm4_rt --shard 0 --nshard 2
wait
