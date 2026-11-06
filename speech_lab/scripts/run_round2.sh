#!/usr/bin/env bash
# Round 2 (after reviewer critique): fresh held-out utterances (seed 1, none used in r1), wider SNR range
# (-10/0/+10 dB), 10 utts per cell, oracle-noise controls for classical methods, hybrid denoise->TSE.
set -u
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
T=r2
[ -f mixtures/$T/meta.json ] || python3 -m selab.mixtures --tag $T --seed 1 --n_per 10 --snrs -10 0 10 --no_array --exclude_tag r1
for m in noisy wiener_dd mmse_lsa metricgan_plus demucs_dns64 tse_convtasnet_ecapa tse_convtasnet_oracle demucs_then_tse; do
  echo "== $m $(date +%T)"; python3 -m selab.run --method $m --tag $T 2>&1 | grep -E '^\{|FAIL'
done
for m in specsub wiener_dd mmse_lsa; do
  echo "== $m oracle noise $(date +%T)"; python3 -m selab.run --method $m --tag $T --noise_psd oracle 2>&1 | grep -E '^\{|FAIL'
done
echo "== scoring $(date +%T)"; python3 -m selab.evaluate --tag $T 2>&1 | tail -1
echo "== ASR $(date +%T)"; python3 -m selab.evaluate --tag $T --asr --asr_max_per_cell 4 2>&1 | grep -v -i warn | tail -2
echo "== analyze"; python3 -m selab.analyze --tag $T --asr_k 4 > /dev/null 2>&1
echo "== done $(date +%T)"
