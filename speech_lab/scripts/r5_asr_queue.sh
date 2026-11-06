#!/usr/bin/env bash
# Round-5 ASR in priority order, 2 shards per job; resumable (skips (method,item) pairs already scored).
# CPU budget (2 shared vCPU): primary methods on all 144 real items; the rest on 48 items (2 per recording);
# the simulated twin on the same 48 items so sim-vs-real is paired.
cd "$(dirname "$0")/.."; . .venv/bin/activate
job() { for k in 0 1; do python -u -m selab.score_r5 --asr --shard $k --nshard 2 "$@" & done; wait; }
job --tag r5 --methods noisy,mvdr_online_est,deepfilternet3,tse,mvdr_online_est_tse
job --tag r5sim --methods noisy,mvdr_online_est,deepfilternet3,tse,mvdr_online_est_tse,mvdr_online_ref,ds_est,mvdr_mask_tse --items sub48
job --tag r5 --methods mvdr_online_ref,ds_est,mvdr_mask_tse,mvdr_online_dir_est,rnnoise,mvdr_mask_demucs,mvdr_online_est_dfn3,mvdr_online_dir_ref,ref_image --items sub48
job --tag r5sim --methods mvdr_online_dir_est,ref_image --items sub48
# if time allows: extend to all items
job --tag r5 --methods mvdr_online_ref,ds_est,mvdr_mask_tse
job --tag r5sim --methods noisy,mvdr_online_est,deepfilternet3,tse,mvdr_online_est_tse,mvdr_online_ref
