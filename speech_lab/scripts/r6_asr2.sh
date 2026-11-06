#!/usr/bin/env bash
cd "$(dirname "$0")/.."; . .venv/bin/activate
R="sd8_rt__r1000,sd4_rt__r1000,sd8_rt__r500,sd8_rt__r2000,sd4_rt__r2000"
python -m selab.score_r6 --tag r5 --items sub48 --asr --methods $R
python -m selab.score_r6 --tag r5 --items s012 --asr --methods $R,sd8_rt
python -m selab.score_r6 --tag r5 --items sub48 --asr --methods sd4_rt__warm,ds_td_rt__warm
