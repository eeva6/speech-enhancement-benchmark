"""Round-6 tracker onset curve: fraction of 16-ms tracker steps within 10 deg of the reference azimuth as a function of
time since (a) the start of the item (target turn onset) and (b) the start of each overlap interval (interferer onset).
Reads the cached tracks (outputs/r5/r6_tracks/<mode>/<id>.npz); no audio processing.
python -m selab.onset_r6 -> results/r6/tracker_onset.csv, figs/tracker_onset.png
"""
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .common import MIX, OUT, RES, FS
from .analyze_r5 import boot, cluster_of
from . import r6

BINS = [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 1e9]
LAB = ["0-0.25", "0.25-0.5", "0.5-1", "1-1.5", "1.5-2", "2-3", "3-4", "4-6", ">6"]
NAMES = {"r5t": "R5 tracker", "rtn": "track+hyst.", "rt": "track+ECAPA"}


def main():
    rng = np.random.default_rng(0)
    meta = json.load(open(MIX / "r5" / "meta.json")); dref = json.load(open(MIX / "r5" / "doa_ref.json"))
    rows = []
    for m in meta:
        key = f'{m["session"]}_{m["ch"]}'
        if key not in dref:
            continue
        azr = dref[key]
        for mode in ("r5t", "rtn", "rt"):
            p = OUT / "r5" / "r6_tracks" / mode / f"{m['id']}.npz"
            if not p.exists():
                continue
            z = np.load(p); t = z["avail"] / FS; ok = (np.abs(r6.angdiff(z["az"], azr)) <= 10).astype(float)
            ib = np.digitize(t, BINS) - 1
            for b in range(len(LAB)):
                s = ib == b
                if s.any():
                    rows.append(dict(id=m["id"], cond=m["cond"], mode=mode, ref="item start", bin=b, n=int(s.sum()), acc=ok[s].mean()))
            # interferer onsets: time since the start of the overlap interval containing the step
            for b0, b1 in m.get("busy", []):
                s0 = (t >= b0) & (t <= b1)
                if not s0.any():
                    continue
                ib2 = np.digitize(t[s0] - b0, BINS) - 1
                for b in range(len(LAB)):
                    s = ib2 == b
                    if s.any():
                        rows.append(dict(id=m["id"], cond=m["cond"], mode=mode, ref="overlap start", bin=b, n=int(s.sum()), acc=ok[s0][s].mean()))
    d = pd.DataFrame(rows)
    # per item mean within bin (each item weighted once per bin), then cluster bootstrap over recordings
    g = d.groupby(["ref", "mode", "id", "cond", "bin"]).apply(lambda v: np.average(v.acc, weights=v.n)).rename("acc").reset_index()
    out = []
    for (ref, mode, b), s in g.groupby(["ref", "mode", "bin"]):
        for grp, f in (("overlapped", s.cond != "0S"), ("0S", s.cond == "0S")):
            ss = s[f].copy()
            if len(ss) < 3:
                continue
            ss["cl"] = ss.id.map(cluster_of)
            e, lo, hi = boot(ss, "acc", rng)
            out.append(dict(ref=ref, mode=mode, group=grp, bin=LAB[b], bin_idx=b, n_items=len(ss), acc=e, lo=lo, hi=hi))
    O = pd.DataFrame(out); O.to_csv(RES / "r6" / "tracker_onset.csv", index=False)
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, ref in zip(axs, ("item start", "overlap start")):
        for mode, c in (("r5t", "#888"), ("rtn", "#269"), ("rt", "#c44")):
            s = O[(O.ref == ref) & (O["mode"] == mode) & (O.group == "overlapped")].sort_values("bin_idx")
            ax.errorbar(s.bin_idx, s.acc, yerr=[s.acc - s.lo, s.hi - s.acc], fmt="o-", color=c, capsize=2, ms=3, label=NAMES[mode])
        ax.set_xticks(range(len(LAB))); ax.set_xticklabels(LAB, rotation=45, fontsize=7)
        ax.set_xlabel(f"time since {ref} (s)", fontsize=8); ax.set_ylim(0, 1); ax.grid(alpha=0.3)
    axs[0].set_ylabel("fraction of steps within 10°", fontsize=8); axs[0].legend(fontsize=7)
    fig.suptitle("Tracker accuracy vs time since onset (overlapped items, 95% cluster-bootstrap CI)", fontsize=9)
    fig.tight_layout(); fig.savefig(RES / "r6" / "figs" / "tracker_onset.png", dpi=150); plt.close(fig)
    print(O[O.group == "overlapped"].round(3).to_string())


if __name__ == "__main__":
    main()
