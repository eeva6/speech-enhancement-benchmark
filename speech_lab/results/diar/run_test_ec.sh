#!/bin/bash
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
source .venv/bin/activate
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=.
nice -n 19 python -u -m selab.diar.score test
cp results/diar/test_rows.csv results/diar/test_rows_easycom.csv
kill -CONT 3470 2>/dev/null
