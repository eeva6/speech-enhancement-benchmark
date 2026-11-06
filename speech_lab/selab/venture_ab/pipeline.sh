#!/bin/bash
# Full resumable venture A/B pipeline, strictly sequential (one heavy job at a time). Retries stages killed by OOM.
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
source .venv/bin/activate
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
W=/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS/ab_set_work
run(){ echo "== $(date) $*" >> $W/pipeline.log; nice -n 19 python -u -m "$@" >> $W/pipeline.log 2>&1; echo "== exit $?" >> $W/pipeline.log; sync; }
n_items(){ ls $W/items/*/done.json 2>/dev/null | wc -l; }
n_groups(){ ls $W/groups/*/done.json 2>/dev/null | wc -l; }
for i in $(seq 1 20); do [ $(n_items) -ge 21 ] && break; run selab.venture_ab.build proc; sleep 5; done
for i in 1 2 3 4 5; do [ -f $W/group_selection.json ] && break; run selab.venture_ab.group select; done
NG=$(python -c "import json;print(len(json.load(open('$W/group_selection.json'))['selected']))")
for i in $(seq 1 20); do [ $(n_groups) -ge $NG ] && break; run selab.venture_ab.group proc; sleep 5; done
for i in 1 2 3; do [ -f $W/obj.csv ] && break; run selab.venture_ab.score obj; done
for i in 1 2 3 4 5 6; do run selab.venture_ab.score asr; L=$(wc -l < $W/asr.csv 2>/dev/null || echo 0); [ "$L" -ge 148 ] && break; done
run selab.venture_ab.score summary
for i in 1 2 3; do [ -f $W/group_metrics_raw.csv ] && break; run selab.venture_ab.group score; done
echo "== $(date) PIPELINE_DONE" >> $W/pipeline.log
