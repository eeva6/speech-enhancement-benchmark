#!/usr/bin/env bash
cd "$(dirname "$0")/.."; . .venv/bin/activate
python -m selab.score_r6 --tag r5 --items sub48 --asr --methods sd8_rt__r1000m,sd8_rt__r1000,sd4_rt__r1000
while [ "$(ls outputs/r5/sd4_rt__v15m 2>/dev/null | wc -l)" -lt 144 ]; do sleep 15; done; sleep 10
python -m selab.score_r6 --tag r5 --items sub48 --asr --methods sd8_rt__v15m,sd4_rt__v15m
