"""Round 7 phase 2 analysis (EasyCom): paired deltas, cluster bootstrap over (session, minute), Holm.

python -m selab.analyze_r7 [--split test]
Writes results/r7/asr_<split>.csv (word-correct / WER per method x group, deltas vs unproc_front and vs r5ds with
95% CIs, bootstrap p and Holm-adjusted p across the new methods within each group and comparison),
results/r7/obj_<split>.csv (SI-SDR / ESTOI, align_suspect items excluded), results/r7/steer_<split>.csv
(steering error vs word-correct gain), and prints the main tables.
Groups: all (ASR keeps align_suspect items), all_noSuspect, target wearer/group/other/none, overlap / no overlap,
time since turn onset <0.5 / 0.5-2 / >2 s.
"""
import argparse, json
import numpy as np, pandas as pd
from .common import RES, MIX
from . import analyze_r5 as A5
from .run_r7 import load_wer, FINAL

R7 = RES / "r7"
A5.B = 2000
BASES = ["unproc_front", "unproc_ear", "r5ds"]
NEW = [m for m in FINAL if m not in BASES]
LABEL = {"unproc_front": "Unprocessed frame mic (frozen best of ch1-4)", "unproc_ear": "Ear-canal mics mean ch5/6 (reference only)",
         "r5ds": "R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline)",
         "hs_ds_td": "Head-steered DS, time-domain (ATF delays)", "hs_sd8": "Head-steered superdirective 8 ms",
         "hs_sd4": "Head-steered superdirective 4 ms", "trk_ds_td": "Tracked DS time-domain", "trk_sd8": "Tracked SD 8 ms",
         "trk_sd4": "Tracked SD 4 ms", "hyb_ds_td": "Head-prior hybrid DS time-domain", "hyb_sd8": "Head-prior hybrid SD 8 ms",
         "hyb_sd4": "Head-prior hybrid SD 4 ms", "ref_sd8": "REF-DOA SD 8 ms (oracle)", "ref_ds_td": "REF-DOA DS time-domain (oracle)"}


def groups(meta, ids_ok):
    M = pd.DataFrame(meta); M = M[M.id.isin(ids_ok)]
    g = {"all": M.id, "all_noSuspect": M[~M.align_suspect].id}
    for t in ("wearer", "group", "other", "none"):
        g[f"to_{t}"] = M[M.target == t].id
    g["overlap"] = M[M.overlap].id; g["no_overlap"] = M[~M.overlap].id
    g["onset<0.5s"] = M[M.t_since_turn_onset < 0.5].id
    g["onset0.5-2s"] = M[(M.t_since_turn_onset >= 0.5) & (M.t_since_turn_onset < 2)].id
    g["onset>2s"] = M[M.t_since_turn_onset >= 2].id
    return {k: set(v) for k, v in g.items()}


def paired(w, a, b, col, ids):
    x = w[(w.method == a) & w.id.isin(ids)].set_index("id")[col]; y = w[(w.method == b) & w.id.isin(ids)].set_index("id")[col]
    j = x.index.intersection(y.index)
    return pd.DataFrame(dict(d=(x[j] - y[j]).values, cl=[A5.cluster_of(i) for i in j]))


def table(w, G, col, rng, methods):
    rows = []
    for g, ids in G.items():
        for me in methods:
            s = w[(w.method == me) & w.id.isin(ids)]
            if s.empty:
                continue
            r = dict(group=g, method=me, label=LABEL.get(me, me), n=len(s), n_clusters=s.id.map(A5.cluster_of).nunique(), mean=s[col].mean())
            for base, tag in (("unproc_front", "front"), ("r5ds", "r5ds")):
                if me == base:
                    continue
                d = paired(w, me, base, col, ids)
                if d.empty:
                    continue
                r[f"d_{tag}"], r[f"d_{tag}_lo"], r[f"d_{tag}_hi"] = A5.boot(d, "d", rng)
                r[f"p_{tag}"] = A5.boot_p(d, "d", rng)
            rows.append(r)
    T = pd.DataFrame(rows)
    for tag in ("front", "r5ds"):
        T[f"p_{tag}_holm"] = np.nan
        for g in T.group.unique():
            k = T[(T.group == g) & T.method.isin(NEW) & T[f"p_{tag}"].notna()].index
            if len(k):
                T.loc[k, f"p_{tag}_holm"] = A5.holm(T.loc[k, f"p_{tag}"].values)
    return T


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--split", default="test"); a = ap.parse_args()
    sp = a.split; rng = np.random.default_rng(7)
    meta = json.load(open(MIX / "r7" / sp / "meta.json"))["items"]
    w = load_wer(sp); w = w[w.method.isin(FINAL)]
    present = set(w[w.method == "unproc_front"].id)
    G = groups(meta, present)
    T = table(w, G, "word_correct", rng, [m for m in FINAL if m in set(w.method)])
    T.to_csv(R7 / f"asr_{sp}.csv", index=False)
    Tw = table(w, {k: G[k] for k in ("all", "all_noSuspect")}, "wer", rng, [m for m in FINAL if m in set(w.method)])
    Tw.to_csv(R7 / f"asr_wer_{sp}.csv", index=False)
    # objective (align_suspect excluded)
    import glob
    ps = sorted(glob.glob(str(R7 / f"metrics_{sp}.csv")) + glob.glob(str(R7 / f"metrics_{sp}.part*.csv")))
    if ps:
        o = pd.concat([pd.read_csv(p) for p in ps]).drop_duplicates(["method", "id"], keep="last")
        o = o[~o.align_suspect.astype(bool) & o.method.isin(FINAL)]
        Gm = groups(meta, set(o[o.method == "unproc_front"].id))
        Gm = {k: Gm[k] for k in ("all", "to_wearer", "overlap", "no_overlap")}
        O = pd.concat([table(o, Gm, c, rng, [m for m in FINAL if m in set(o.method)]).assign(metric=c) for c in ("si_sdr", "estoi")])
        O.to_csv(R7 / f"obj_{sp}.csv", index=False)
    # steering error vs gain
    pfs = sorted(glob.glob(str(R7 / "proc" / f"{sp}_*.csv")))
    pr = pd.concat([pd.read_csv(p) for p in pfs]) if pfs else pd.DataFrame(columns=["method", "id", "steer_err_med", "head_angle"])
    pr = pr[pr.method.isin(FINAL)].drop_duplicates(["method", "id"], keep="last")
    S = []
    wc = w.pivot(index="id", columns="method", values="word_correct")
    for me in [m for m in NEW if m.startswith(("trk", "hyb", "hs"))]:
        filt = me.split("_", 1)[1]
        p = pr[pr.method == me].set_index("id")
        j = p.index.intersection(wc.index)
        if not len(j) or me not in wc:
            continue
        gain_f = wc.loc[j, me] - wc.loc[j, "unproc_front"]
        gain_hs = wc.loc[j, me] - wc.loc[j, f"hs_{filt}"] if f"hs_{filt}" in wc else np.nan
        e = p.loc[j, "steer_err_med"]
        for lo, hi in ((0, 10), (10, 20), (20, 45), (45, 90), (90, 181)):
            k = (e >= lo) & (e < hi)
            S.append(dict(method=me, err_bin=f"{lo}-{hi}", n=int(k.sum()), gain_vs_front=float(gain_f[k].mean()) if k.any() else np.nan,
                          gain_vs_hs=float(gain_hs[k].mean()) if k.any() and not np.isscalar(gain_hs) else np.nan,
                          head_angle_med=float(p.loc[j, "head_angle"][k].median()) if k.any() else np.nan))
        from scipy.stats import spearmanr
        S.append(dict(method=me, err_bin="spearman(err, gain_vs_front)", n=len(j), gain_vs_front=float(spearmanr(e, gain_f, nan_policy="omit")[0])))
    pd.DataFrame(S).to_csv(R7 / f"steer_{sp}.csv", index=False)
    show = T[T.group.isin(["all", "all_noSuspect", "overlap", "to_wearer"])]
    pd.set_option("display.width", 250)
    print(show[["group", "method", "n", "mean", "d_front", "d_front_lo", "d_front_hi", "p_front_holm", "d_r5ds", "d_r5ds_lo", "d_r5ds_hi", "p_r5ds_holm"]].round(3).to_string())


if __name__ == "__main__":
    main()
