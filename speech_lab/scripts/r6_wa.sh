#!/usr/bin/env bash
# wait for the warm panel processing, then: warm ASR; tracker warm eval (panel); sim extras
cd "$(dirname "$0")/.."; . .venv/bin/activate
while [ "$(ls outputs/r5/rtf4_ref__warm 2>/dev/null | wc -l)" -lt 48 ]; do sleep 15; done
sleep 20
python -m selab.score_r6 --tag r5 --items sub48 --asr --methods sd8_rt__warm,sd4_rt__warm,ds_td_rt__warm,ds_td_r5t__warm,gm4_rt__warm,rtf4_rt__warm,gm8_rt__warm,rtf8_rt__warm,sd8_r5t__warm,gm4_ref__warm,rtf4_ref__warm
