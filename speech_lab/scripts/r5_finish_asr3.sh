#!/usr/bin/env bash
# Round-5 lane A (Whisper ASR), final: priority sweeps on the sub48 panel until the sensitivity runs are done.
cd "$(dirname "$0")/.."; . .venv/bin/activate
a() { echo "== $(date -u +%T) $*"; python -u -m selab.score_r5 --asr "$@" 2>&1 | grep -E 'ASR:|Error' | tr '\n' ' '; echo; }
sweep() {
  a --tag r5 --methods noisy,mvdr_online_est,deepfilternet3,tse,ds_est,mvdr_online_est_dfn3,mvdr_online_est_tse --items sub48
  a --tag r5sim --methods noisy,ds_est,mvdr_online_est,deepfilternet3,tse --items sub48
  a --tag r5 --methods mvdr_online_ref --items sub48
  a --tag r5ctx --methods noisy,noisy_cut,mvdr_online_est,mvdr_online_est_cut,tse,tse_cut
  a --tag r5 --methods tse_dryenrol,rnnoise --items sub48
}
while [ ! -f logs/r5_proc_sens.done ]; do sweep; sleep 45; done
sweep
a --tag r5 --methods mvdr_online_dir_est,mvdr_online_dir_ref,deepfilternet3_rawlevel --items sub48
touch logs/r5_asr_all.done; echo "== $(date -u +%T) DONE"
