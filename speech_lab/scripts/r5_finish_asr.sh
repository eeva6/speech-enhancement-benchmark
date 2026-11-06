#!/usr/bin/env bash
# Round-5 finishing lane A (Whisper ASR), single process; resumable (skips scored (method,item) pairs).
cd "$(dirname "$0")/.."; . .venv/bin/activate
a() { echo "== $(date -u +%T) $*"; python -u -m selab.score_r5 --asr "$@" 2>&1 | grep -E 'ASR:|Error'; }
a --tag r5 --methods noisy,mvdr_online_est,deepfilternet3,tse,ds_est,mvdr_online_est_dfn3 --items sub48
a --tag r5sim --methods noisy,ds_est,mvdr_online_est --items sub48
a --tag r5 --methods ref_image --items sub48
a --tag r5sim --methods deepfilternet3,ref_image --items sub48
until [ -f logs/r5_proc_core.done ]; do
  a --tag r5 --methods mvdr_online_est_tse --items sub48; a --tag r5sim --methods tse,deepfilternet3,mvdr_online_est,ds_est,noisy --items sub48; sleep 60; done
a --tag r5 --methods mvdr_online_est_tse --items sub48; a --tag r5sim --methods tse --items sub48
touch logs/r5_asr_core.done
a --tag r5 --methods rnnoise,mvdr_online_ref,mvdr_online_dir_est --items sub48
a --tag r5 --methods noisy,mvdr_online_est,deepfilternet3,tse
a --tag r5 --methods ds_est,mvdr_online_est_dfn3,mvdr_online_est_tse
touch logs/r5_asr_all.done; echo "== $(date -u +%T) DONE"
