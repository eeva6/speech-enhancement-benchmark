#!/usr/bin/env bash
# Round 1: every method on the r1 set, then scoring + ASR. ~2 h on 2 vCPU.
set -u
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
T=${TAG:-r1}
for m in noisy specsub wiener_dd mmse_lsa noisereduce metricgan_plus demucs_dns64 tse_convtasnet_ecapa tse_convtasnet_oracle \
         bf_ds bf_mvdr_oracle bf_mvdr_ff bf_mvdr_mask bf_mvdr_mask_pf; do
  echo "== $m $(date +%T)"; python3 -m selab.run --method $m --tag $T 2>&1 | grep -E '^\{|FAIL' 
done
echo "== sepformer_enh (subset: 3 utts per cell, RTF~3 on this CPU) $(date +%T)"
python3 -m selab.run --method sepformer_enh --tag $T --max_per_cell 3 2>&1 | grep -E '^\{|FAIL'
echo "== scoring $(date +%T)"; python3 -m selab.evaluate --tag $T 2>&1 | tail -2
echo "== ASR $(date +%T)"; python3 -m selab.evaluate --tag $T --asr --asr_max_per_cell 3 2>&1 | grep -v -i warn | tail -3
echo "== done $(date +%T)"
