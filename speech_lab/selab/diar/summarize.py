"""Tables + failure analysis for results/diar/results.md (python -m selab.diar.summarize)."""
import json
import numpy as np, pandas as pd
from scipy.optimize import linear_sum_assignment
from . import core, data, metrics, score
from ..common import RES

OUT = RES / "diar"
FR = core.FR


def rtf_table():
    rows = []
    for p in sorted((data.CACHE).glob("*.timing.json")):
        d = json.load(open(p)); u = p.name.split(".")[0]
        for st, v in d.items():
            rows.append(dict(uri=u, ds="libricss" if u.startswith("lc_") else "easycom", stage=st, sec=v["sec"], dur=v["dur"]))
    df = pd.DataFrame(rows)
    g = df.groupby(["ds", "stage"]).agg(sec=("sec", "sum"), dur=("dur", "sum")).reset_index()
    g["rtf"] = g.sec / g.dur
    return g


def frame_analysis(item, cfg, kind=None):
    """per-frame breakdown: overlap vs single-talker DER, short-turn accuracy, confusion between reference speakers."""
    f = score.feats(item)
    if kind == "platform":
        hyp = score.platform_labels(f, item, cfg)
    else:
        lab, _ = score.diarize(f, cfg, item); hyp = core.labels_to_segments(lab)
    T = f["T"] + 10
    R, rk = metrics._mat(f["ref"], T); H, hk = metrics._mat(hyp, T)
    ov = R.T.astype(float) @ H.astype(float)
    ri, hi = linear_sum_assignment(-ov)
    Hm = np.zeros_like(R)
    for i, j in zip(ri, hi):
        Hm[:, i] = H[:, j]
    nr = R.sum(1); nh = H.sum(1)
    corr = (R & Hm).sum(1)
    err = np.maximum(nr - nh, 0) + np.maximum(nh - nr, 0) + (np.minimum(nr, nh) - corr)
    out = {}
    for nm, m in (("single", nr == 1), ("overlap", nr >= 2)):
        out[f"der_{nm}"] = err[m].sum() / max(nr[m].sum(), 1)
        out[f"share_{nm}"] = nr[m].sum() / max(nr.sum(), 1)
    # turn-length buckets: fraction of a reference segment's frames whose speaker is in the mapped hyp
    buck = {"<1s": [0, 0], "1-3s": [0, 0], ">3s": [0, 0]}
    for a, b, s in f["ref"]:
        i = rk.index(s); i0, i1 = int(round(a / FR)), int(round(b / FR))
        d = b - a; key = "<1s" if d < 1 else ("1-3s" if d < 3 else ">3s")
        buck[key][0] += Hm[i0:i1, i].sum(); buck[key][1] += i1 - i0
    for k, (c, n) in buck.items():
        out[f"acc_turn{k}"] = c / max(n, 1)
    # confusion between reference speakers on single-talker frames: who gets the frames of ref speaker i
    single = nr == 1
    conf = np.zeros((len(rk), len(rk)))
    inv = {j: i for i, j in zip(ri, hi)}
    for j in range(H.shape[1]):
        if j not in inv:
            continue
        for i in range(len(rk)):
            conf[i, inv[j]] += (R[:, i] & H[:, j] & single).sum()
    return out, conf, rk


def speaker_similarity(item):
    """mean ECAPA embedding per reference speaker from single-talker windows -> cosine matrix."""
    f = score.feats(item)
    T = f["T"] + 10
    R, rk = metrics._mat(f["ref"], T)
    wins = f["wins"]; E = f["emb"]
    C = []
    for i in range(len(rk)):
        idx = [w for w, (a, b) in enumerate(wins) if R[int(a / FR):int(b / FR), i].mean() > 0.9 and
               R[int(a / FR):int(b / FR)].sum(1).max() == 1]
        C.append(E[idx].mean(0) if idx else np.zeros(E.shape[1]))
    C = np.array(C); C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-9
    return C @ C.T, rk


def main():
    df = pd.read_csv(OUT / "test_rows.csv")
    fz = json.load(open(OUT / "frozen_diar.json"))
    df["spk_err"] = (df.n_hyp - df.n_ref).abs()
    df["spk_signed"] = df.n_hyp - df.n_ref
    agg = df.groupby(["ds", "variant"]).agg(
        n=("uri", "count"), DER_c25=("der_c25", "mean"), DER_c0=("der_c0", "mean"), miss_c0=("miss_c0", "mean"),
        fa_c0=("fa_c0", "mean"), conf_c0=("conf_c0", "mean"), JER=("jer", "mean"), spk_abs_err=("spk_err", "mean"),
        spk_signed=("spk_signed", "mean"), cpWER=("cpwer", "mean"), WER_all=("wer_all", "mean")).reset_index()
    agg.to_csv(OUT / "test_summary.csv", index=False)
    lc = df[df.ds == "libricss"].copy()
    lc["cond"] = lc.uri.str.extract(r"lc_(\w+?)_s")[0]
    bycond = lc.pivot_table(index="variant", columns="cond", values="der_c0", aggfunc="mean")
    bycond.to_csv(OUT / "test_libricss_by_condition.csv")
    # failure analysis on the main single-channel and spatial variants
    fa_rows = []; conf_notes = []
    for ds, sp in (("libricss", "lc_test"), ("easycom", "ec_test")):
        if ds not in fz:
            continue
        for it in data.items(sp):
            for name, cfg, kind in (("A_spectral", fz[ds]["spec"], None), ("B_spatial_spectral", fz[ds]["spec_sp"], None),
                                    ("A_spectral_oracleVAD", dict(fz[ds]["spec"], vad="oracle"), None),
                                    ("platform", fz[ds]["platform"], "platform")):
                try:
                    o, conf, rk = frame_analysis(it, cfg, kind)
                except Exception as ex:
                    print("fa fail", it["uri"], name, ex); continue
                o.update(uri=it["uri"], ds=ds, variant=name); fa_rows.append(o)
                if name == "A_spectral":
                    S, rk2 = speaker_similarity(it)
                    tot = conf.sum(1, keepdims=True) + 1e-9
                    P = conf / tot
                    for i in range(len(rk)):
                        for j in range(len(rk)):
                            if i != j:
                                conf_notes.append(dict(uri=it["uri"], ds=ds, a=rk[i], b=rk[j], frac_a_to_b=P[i, j],
                                                       cos=S[rk2.index(rk[i]), rk2.index(rk[j])]))
    fa = pd.DataFrame(fa_rows); fa.to_csv(OUT / "test_failure_frames.csv", index=False)
    cn = pd.DataFrame(conf_notes); cn.to_csv(OUT / "test_confusion_pairs.csv", index=False)
    rt = rtf_table(); rt.to_csv(OUT / "rtf.csv", index=False)
    print(agg.round(3).to_string()); print(bycond.round(3).to_string())
    print(fa.groupby(["ds", "variant"]).mean(numeric_only=True).round(3).to_string()); print(rt.round(3).to_string())
    if len(cn):
        cn["bin"] = pd.cut(cn.cos, [-1, 0.3, 0.5, 0.7, 1.0])
        print(cn.groupby(["ds", "bin"], observed=True).frac_a_to_b.agg(["mean", "count"]).round(3).to_string())


if __name__ == "__main__":
    main()
    try:
        from . import enrol_eval
        enrol_eval.main()
    except Exception as ex:
        print("enrol_eval failed:", ex)
