#!/bin/bash
# Diarization track, full resumable chain (every stage caches; safe to re-run after a sandbox restart).
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
source .venv/bin/activate
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=.
N="nice -n 19"
echo "== $(date -u) features ec_test"; $N python -u -m selab.diar.features ec_test --asr
echo "== $(date -u) test (easycom only if libricss not yet tuned)"; $N python -u -m selab.diar.score test
echo "== $(date -u) features lc_tune lc_test"; $N python -u -m selab.diar.features lc_tune lc_test --asr
grep -q '"libricss"' results/diar/frozen_diar.json || { echo "== $(date -u) tune libricss"; $N python -u -m selab.diar.score tune libricss; }
echo "== $(date -u) test (both)"; $N python -u -m selab.diar.score test
echo "== $(date -u) summarize"; $N python -u -m selab.diar.summarize && $N python -u -m selab.diar.report_tables > results/diar/tables.md
echo "== $(date -u) ALL DONE"
