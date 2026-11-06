"""Round 6 analysis: paired deltas with cluster bootstrap over recordings, Holm correction.

python -m selab.analyze_r6 [--items sub48|all|s345] [--tag r5] [--name panel]
Reads ASR from results/r6/wer_<tag>*.csv plus the round-5 baselines in results/r5/wer_<tag>*.csv.
Writes results/r6/asr_<name>_<tag>.csv and returns tables used by summary_r6.
"""
import argparse, glob, json
import numpy as np, pandas as pd
from .common import RES, MIX
from .analyze_r5 import boot, boot_p, holm, cluster_of
from .run_r6 import select

R6 = RES / "r6"
BASE = ["noisy", "ds_est", "mvdr_online_est", "mvdr_online_dir_est", "mvdr_online_ref", "mvdr_online_dir_ref", "ref_image"]
FILT = {"ds_td": "Delay-and-sum, time-domain FIR", "sd4": "Superdirective+WNG, 4 ms STFT", "sd8": "Superdirective+WNG, 8 ms STFT",
        "gm4": "Coherence-gated MVDR+WNG, 4 ms", "gm8": "Coherence-gated MVDR+WNG, 8 ms",
        "rtf4": "Online RTF(GEVD)-MVDR+WNG, 4 ms", "rtf8": "Online RTF(GEVD)-MVDR+WNG, 8 ms"}
STEER = {"r5t": "R5 tracker", "rtn": "track+hyst.", "rt": "track+ECAPA", "ref": "REF dir.", "blind": "blind whole-seg. dir."}
LAB5 = {"noisy": "Unprocessed mic 0", "ds_est": "R5 delay-and-sum, blind dir. (32 ms STFT)",
        "mvdr_online_est": "R5 online MVDR, est. dir. (32 ms)", "mvdr_online_dir_est": "R5 gated MVDR, est. dir. (32 ms)",
        "mvdr_online_ref": "R5 online MVDR, REF dir. (32 ms)", "mvdr_online_dir_ref": "R5 gated MVDR, REF dir. (32 ms)",
        "ref_image": "Target image alone (ceiling)"}


def label(m):
    if m in LAB5:
        return LAB5[m]
    base, _, suf = m.partition("__")
    f, s = base.rsplit("_", 1)
    SUF = {"warm": "warm start (2 s history)", "r1000": "1 s confidence ramp from DS", "r1000m": "1 s ramp from mic 0",
           "v15m": "ECAPA-verified gate (cos >= 0.15), else mic 0", "w-6": "WNG floor -6 dB", "w6": "WNG floor +6 dB",
           "c03": "coherence threshold 0.3"}
    return f"{FILT.get(f, f)}, {STEER.get(s, s)}" + (f" [{SUF.get(suf, suf)}]" if suf else "")


def load_wer(tag):
    # exact patterns: "wer_r5*.csv" would also match the twin's wer_r5sim*.csv and let sim rows overwrite real ones
    parts = [pd.read_csv(p) for p in sorted(glob.glob(str(R6 / f"wer_{tag}.csv")) + glob.glob(str(R6 / f"wer_{tag}.part*.csv")))]
    p5 = [pd.read_csv(p) for p in sorted(glob.glob(str(RES / "r5" / f"wer_{tag}.csv")) + glob.glob(str(RES / "r5" / f"wer_{tag}.part*.csv")))]
    w5 = pd.concat(p5) if p5 else pd.DataFrame(columns=["method", "id"])
    w5 = w5[w5.method.isin(BASE)]
    w = pd.concat([w5] + parts, ignore_index=True).drop_duplicates(["method", "id"], keep="last")
    w["cl"] = w.id.map(cluster_of)
    return w


def delta(w, meth, base, col, ids):
    a = w[(w.method == meth) & w.id.isin(ids)].set_index("id")[col]
    b = w[(w.method == base) & w.id.isin(ids)].set_index("id")[col]
    j = a.index.intersection(b.index)
    return pd.DataFrame(dict(d=(a[j] - b[j]).values, cl=[cluster_of(i) for i in j]))


def asr_table(w, ids_by_group, methods, rng, holm_set=None):
    rows = []
    for g, ids in ids_by_group.items():
        for me in methods:
            s = w[(w.method == me) & w.id.isin(ids)]
            if s.empty:
                continue
            r = dict(group=g, method=me, label=label(me), n=len(s), n_clusters=s.cl.nunique(),
                     wer=s.wer.mean(), word_correct=s.word_correct.mean(), ins_rate=s.ins_rate.mean())
            for base, tag in (("noisy", "noisy"), ("ds_est", "ds5")):
                if me == base:
                    continue
                d = delta(w, me, base, "word_correct", ids)
                if len(d) < len(s):     # paired comparison must cover the same items
                    r[f"n_pair_{tag}"] = len(d)
                if d.empty:
                    continue
                r[f"dwc_{tag}"], r[f"dwc_{tag}_lo"], r[f"dwc_{tag}_hi"] = boot(d, "d", rng)
                r[f"p_{tag}"] = boot_p(d, "d", rng)
                dw = delta(w, me, base, "wer", ids)
                r[f"dwer_{tag}"], r[f"dwer_{tag}_lo"], r[f"dwer_{tag}_hi"] = boot(dw, "d", rng)
            rows.append(r)
    T = pd.DataFrame(rows)
    hs = holm_set if holm_set is not None else [m for m in methods if m not in BASE]
    for tag in ("noisy", "ds5"):
        T[f"p_{tag}_holm"] = np.nan
        for g, idx in T.groupby("group").groups.items():
            sub = T.loc[idx]
            k = sub.index[sub.method.isin(hs) & sub[f"p_{tag}"].notna()] if f"p_{tag}" in sub else []
            if len(k):
                T.loc[k, f"p_{tag}_holm"] = holm(T.loc[k, f"p_{tag}"].to_numpy())
    return T


def groups_for(meta_sel):
    ov = [m["id"] for m in meta_sel if m["cond"] != "0S"]
    g = {"0S (no overlap)": [m["id"] for m in meta_sel if m["cond"] == "0S"], "OV10-40 (overlap)": ov}
    for c in ("OV10", "OV20", "OV40"):
        g[c] = [m["id"] for m in meta_sel if m["cond"] == c]
    return g


def fmt(e, lo, hi, p=3):
    if pd.isna(e):
        return "—"
    return f"{e:+.{p}f} [{lo:+.{p}f}, {hi:+.{p}f}]"


def md_asr(T, group, methods=None):
    S = T[T.group == group]
    if methods is not None:
        S = S.set_index("method").loc[[m for m in methods if m in set(S.method)]].reset_index()
    out = ["| Method | n | WER | word-correct | Δ wc vs unprocessed [95% CI] | Holm p | Δ wc vs R5 DS [95% CI] | Holm p | Δ WER vs unproc. |",
           "|---|---|---|---|---|---|---|---|---|"]
    for _, r in S.iterrows():
        hp = lambda k: "" if pd.isna(r.get(k, np.nan)) else f"{r[k]:.3f}"
        out.append(f"| {r.label} | {r.n} | {r.wer:.3f} | {r.word_correct:.3f} | {fmt(r.get('dwc_noisy'), r.get('dwc_noisy_lo'), r.get('dwc_noisy_hi'))} | "
                   f"{hp('p_noisy_holm')} | {fmt(r.get('dwc_ds5'), r.get('dwc_ds5_lo'), r.get('dwc_ds5_hi'))} | {hp('p_ds5_holm')} | "
                   f"{fmt(r.get('dwer_noisy'), r.get('dwer_noisy_lo'), r.get('dwer_noisy_hi'))} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--items", default="sub48"); ap.add_argument("--tag", default="r5")
    ap.add_argument("--name", default="panel"); ap.add_argument("--methods", default=None)
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    meta = select(json.load(open(MIX / a.tag / "meta.json")), a.items)
    w = load_wer(a.tag)
    methods = a.methods.split(",") if a.methods else [m for m in BASE if m in set(w.method)] + sorted(set(w.method) - set(BASE))
    T = asr_table(w, groups_for(meta), methods, rng)
    T.to_csv(R6 / f"asr_{a.name}_{a.tag}.csv", index=False)
    print(md_asr(T, "OV10-40 (overlap)"))


if __name__ == "__main__":
    main()
