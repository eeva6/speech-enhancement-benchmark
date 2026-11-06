#!/bin/bash
# resumable: every stage is cached in results/diar/cache; rerun this script after a sandbox restart
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
source .venv/bin/activate
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec nice -n 19 python -u -m selab.diar.features ec_tune lc_tune lc_test ec_test --asr
