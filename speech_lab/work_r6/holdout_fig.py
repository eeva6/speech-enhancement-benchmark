"""Held-out test (sessions 3-5, overlapped) forest plot from results/r6/asr_holdout_test.csv."""
import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
t = pd.read_csv("results/r6/asr_holdout_test.csv"); t = t[(t.group == "OV10-40 (overlap)") & (t.method != "noisy")]
lab = {"ds_est": "R5 delay-and-sum, blind dir., 32 ms", "ds_td_rt": "TD delay-and-sum, tracked, 0.62 ms",
       "sd4_rt__w6": "Superdirective 4 ms (+6 dB WNG), tracked", "sd8_rt": "Superdirective 8 ms, tracked",
       "ds_td_ref": "TD delay-and-sum, REF dir., 0.62 ms", "sd4_ref__w6": "Superdirective 4 ms (+6 dB WNG), REF dir.",
       "sd8_ref": "Superdirective 8 ms, REF dir."}
fig, ax = plt.subplots(figsize=(7, 3.2)); y = np.arange(len(t))[::-1]
for yi, (_, r) in zip(y, t.iterrows()):
    c = "#888" if r.method == "ds_est" else ("#c44" if "_ref" in r.method else "#269")
    ax.errorbar([r.dwc_noisy], [yi], xerr=[[r.dwc_noisy - r.dwc_noisy_lo], [r.dwc_noisy_hi - r.dwc_noisy]], fmt="o", color=c, capsize=2, ms=4)
ax.axvline(0, color="k", lw=0.8); ax.axvline(float(t[t.method == "ds_est"].dwc_noisy.iloc[0]), color="#888", ls="--", lw=0.8)
ax.set_yticks(y); ax.set_yticklabels([lab[m] for m in t.method], fontsize=7)
ax.set_xlabel("Δ word-correct vs unprocessed, held-out overlapped items\n(n = 54, 9 recordings; 95% cluster-bootstrap CI)", fontsize=8)
fig.tight_layout(); fig.savefig("results/r6/figs/holdout_forest.png", dpi=150, bbox_inches="tight")
