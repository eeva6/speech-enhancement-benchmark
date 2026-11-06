#!/usr/bin/env bash
# Round 5: REAL 7-mic recordings (LibriCSS) + simulated twin + DFN3 frame timing + listening pack.
# Every step is resumable (re-running skips finished files) and short enough for a 20-minute job limit;
# if a step is cut off, just run it again.
#   ./scripts/run_round5.sh get        # LibriCSS subset via HTTP range reads (24 recordings, ~2.2 GB)
#   ./scripts/run_round5.sh build      # 144 real test items -> mixtures/r5 (+ sysid references)
#   ./scripts/run_round5.sh doa        # reference DOA table + DOA-error csv
#   ./scripts/run_round5.sh twin       # simulated twin of every item -> mixtures/r5sim
#   ./scripts/run_round5.sh proc [r5|r5sim]   # all methods
#   ./scripts/run_round5.sh score [r5|r5sim]  # SI-SDR/ESTOI vs estimated reference + Whisper WER
#   ./scripts/run_round5.sh analyze    # results/r5/summary_r5.md, figs
#   ./scripts/run_round5.sh dfn_timing # DeepFilterNet3 frame-by-frame timing (Rust deep-filter / Python streaming)
#   ./scripts/run_round5.sh listening  # listening/r5 mp3 pairs + zip, listening-test stimuli
set -u
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
STEP=${1:-all}; TAG=${2:-r5}
METHODS="noisy rnnoise deepfilternet3 tse ds_est mvdr_online_est mvdr_online_dir_est mvdr_online_ref mvdr_online_dir_ref mvdr_mask_demucs mvdr_mask_tse mvdr_online_est_dfn3 mvdr_online_est_tse"
if [ $STEP = all ] || [ $STEP = get ]; then
  python selab/libricss_get.py OV40,OV20,0S,OV10 0,1,2,3,4,5
fi
if [ $STEP = all ] || [ $STEP = build ]; then python -m selab.libricss r5; fi
if [ $STEP = all ] || [ $STEP = doa ]; then python -m selab.doa_r5 --tag r5; fi
if [ $STEP = all ] || [ $STEP = twin ]; then python -m selab.twin_r5; python -m selab.doa_r5 --tag r5sim --pra_n 0; fi
# the simulated twin runs the subset that the sim-vs-real comparison needs (CPU budget)
[ "$TAG" = r5sim ] && METHODS="noisy deepfilternet3 tse ds_est mvdr_online_est mvdr_online_dir_est mvdr_online_ref mvdr_mask_tse mvdr_online_est_tse"
PRIMARY="noisy,mvdr_online_est,deepfilternet3,ds_est,mvdr_online_ref,mvdr_online_dir_est,tse,mvdr_online_est_tse,mvdr_mask_tse"
SECONDARY="rnnoise,mvdr_online_dir_ref,mvdr_mask_demucs,mvdr_online_est_dfn3"
if [ $STEP = all ] || [ $STEP = proc ]; then
  for m in $METHODS; do echo "== $TAG $m"; python -m selab.run_r5 --method $m --tag $TAG --resume 2>&1 | grep -E '^\{|FAIL'; done
fi
if [ $STEP = all ] || [ $STEP = score ]; then
  python -m selab.score_r5 --tag $TAG
  # ASR in 2 shards: primary methods on all 144 items, secondary methods (real set) on 48 items (2 per recording)
  ./scripts/r5_asr_queue.sh   # priority-ordered ASR (both tags); see that script for which items each method gets
fi
if [ $STEP = all ] || [ $STEP = analyze ]; then python -m selab.analyze_r5; fi
if [ $STEP = all ] || [ $STEP = dfn_timing ]; then python -m selab.dfn_timing; fi
if [ $STEP = all ] || [ $STEP = listening ]; then python -m selab.listening_r5; fi
