#!/bin/bash
# After pipeline.sh: complete Whisper scoring for the selected clips (+best case) and group clips, then summary + export.
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
source .venv/bin/activate
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
W=/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS/ab_set_work
while pgrep -f "^/bin/bash selab/venture_ab/(pipeline|watchdog).sh" > /dev/null; do sleep 20; done
run(){ echo "== $(date) $*" >> $W/finish.log; nice -n 19 python -u -m "$@" >> $W/finish.log 2>&1; echo "== exit $?" >> $W/finish.log; sync; }
need(){ python - <<'PY'
import json, pandas as pd
W="/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS/ab_set_work"
sel=json.load(open(W+"/selection.json"))["selected"]; a=pd.read_csv(W+"/asr.csv")
o=pd.read_csv(W+"/obj.csv"); b=o[o["mode"]=="raw"].set_index("id")["snr"]; q=o[o["mode"]=="causal_trk_sd8"].set_index("id")["snr"]
ids=set(sel)|{(q-b.loc[q.index]).idxmax()}
print(sum(7-len(a[a.id==i]) for i in ids))
PY
}
for i in $(seq 1 30); do [ "$(need)" = "0" ] && break; run selab.venture_ab.score asr; sleep 3; done
run selab.venture_ab.score summary
for i in $(seq 1 30); do [ -f $W/group_metrics_raw.csv ] && break; run selab.venture_ab.group score; sleep 3; done
run selab.venture_ab.export
run selab.venture_ab.tables
echo "== $(date) FINISH_DONE" >> $W/finish.log
