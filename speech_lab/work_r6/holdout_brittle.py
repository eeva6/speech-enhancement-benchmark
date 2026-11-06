"""Whisper brittleness on the held-out test sessions (overlapped items) + cluster counts."""
import json, pandas as pd
from selab.analyze_r6 import load_wer, label
from selab.run_r6 import select
from selab.summary_r6 import brittleness
w = load_wer("r5"); meta = select(json.load(open("mixtures/r5/meta.json")), "s345")
ov = [m["id"] for m in meta if m["cond"] != "0S"]
ms = ["noisy","ds_est","ds_td_rt","sd4_rt__w6","sd8_rt","ds_td_ref","sd4_ref__w6","sd8_ref"]
B = brittleness(w, ov, ms); B.to_csv("results/r6/whisper_brittleness_holdout.csv", index=False)
print(B[["method","n","catastrophic_frac","median_d","n_better","n_same","n_worse"]].to_string())
t = pd.read_csv("results/r6/asr_holdout_test.csv"); print(t[["group","method","n","n_clusters"]].to_string())
