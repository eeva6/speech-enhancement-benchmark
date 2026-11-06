#!/bin/bash
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
source .venv/bin/activate
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=.
nice -n 19 python -u -m selab.diar.score tune easycom
kill -CONT 1124 2>/dev/null   # resume the paused features job (same PID) when tuning ends
