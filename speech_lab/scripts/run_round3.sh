#!/usr/bin/env bash
# Round 3: OUT-OF-DOMAIN test (CMU ARCTIC speech + recorded MS-SNSD noise) and two low-latency causal models
# (RNNoise, DeepFilterNet3) added to every round. Each step is short enough for a 20-minute job limit;
# re-running skips finished files (--resume).
set -u
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
STEP=${1:-all}
run() { python -m selab.run --method $1 --tag $2 --resume 2>&1 | grep -E '^\{|FAIL'; }
if [ $STEP = all ] || [ $STEP = build ]; then
  [ -f mixtures/r3/meta.json ] || python -c "from selab.mixtures import build_ood; build_ood()"
fi
if [ $STEP = all ] || [ $STEP = fast ]; then
  for m in noisy wiener_dd mmse_lsa metricgan_plus rnnoise deepfilternet3 demucs_dns64; do echo "== r3 $m"; run $m r3; done
fi
if [ $STEP = all ] || [ $STEP = tse ]; then
  for m in tse_convtasnet_ecapa tse_convtasnet_oracle; do echo "== r3 $m"; run $m r3; done
fi
if [ $STEP = all ] || [ $STEP = backfill ]; then  # new causal models on the earlier rounds
  for t in r1 r2; do for m in rnnoise deepfilternet3; do echo "== $t $m"; run $m $t; done; done
fi
if [ $STEP = all ] || [ $STEP = score ]; then
  for t in r1 r2 r3; do python -m selab.evaluate --tag $t 2>&1 | tail -1; done
fi
if [ $STEP = all ] || [ $STEP = asr ]; then
  python -m selab.evaluate --tag r3 --asr --asr_max_per_cell 4 2>&1 | grep -v -i warn | tail -1
  python -m selab.evaluate --tag r1 --asr --asr_max_per_cell 3 --methods rnnoise,deepfilternet3 2>&1 | grep -v -i warn | tail -1
  python -m selab.evaluate --tag r2 --asr --asr_max_per_cell 4 --methods rnnoise,deepfilternet3 2>&1 | grep -v -i warn | tail -1
fi
