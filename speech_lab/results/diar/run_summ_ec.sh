#!/bin/bash
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
source .venv/bin/activate
export OMP_NUM_THREADS=1 PYTHONPATH=.
nice -n 19 python -u -m selab.diar.summarize > logs/diar_summ_ec.log 2>&1
nice -n 19 python -u -m selab.diar.report_tables > results/diar/tables_easycom.md 2>>logs/diar_summ_ec.log
kill -CONT 1124
