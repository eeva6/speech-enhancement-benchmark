#!/bin/bash
# Resumable background runner for the venture A/B set (one heavy job at a time).
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
source .venv/bin/activate
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
W=/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS/ab_set_work
exec nice -n 19 python -u -m selab.venture_ab.build "$@" >> $W/run_$1.log 2>&1
