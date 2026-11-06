#!/bin/bash
# Diarization track, resumable chain v2 (after the 05:29 UTC sandbox restart). Every stage caches or is idempotent.
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
source .venv/bin/activate
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=.
N="nice -n 19"
if ! grep -q spec_gate results/diar/frozen_diar.json || [ ! -f results/diar/test_rows_easycom_gate.csv ]; then
  echo "== $(date -u) EasyCom gated-DOA tune+test"; $N python -u -m selab.diar.score gate
fi
echo "== $(date -u) features ec_test lc_tune lc_test"; $N python -u -m selab.diar.features ec_test lc_tune lc_test --asr
grep -q '"libricss"' results/diar/frozen_diar.json || { echo "== $(date -u) tune libricss"; $N python -u -m selab.diar.score tune libricss; }
echo "== $(date -u) test (both)"; $N python -u -m selab.diar.score test
echo "== $(date -u) summarize"; $N python -u -m selab.diar.summarize && $N python -u -m selab.diar.report_tables > results/diar/tables.md
echo "== $(date -u) ALL DONE"
