"""Round 5 analysis: real LibriCSS vs simulated twin, paired deltas with CLUSTER bootstrap CIs.

Items from one 10-minute recording share room state, loudspeakers and talkers, so CIs resample recordings
(cond x session, 24 clusters), not items.  Paired deltas are method minus unprocessed mic 0 on the same item.
python -m selab.analyze_r5  ->  results/r5/summary_r5.md, *.csv, figs/
"""
import json
import numpy as np, pandas as pd
from .common import RES, MIX

R5 = RES / "r5"; FIG = R5 / "figs"
ORDER = ["noisy", "rnnoise", "deepfilternet3", "tse", "ds_est", "mvdr_online_est", "mvdr_online_dir_est",
         "mvdr_online_ref", "mvdr_online_dir_ref", "mvdr_mask_demucs", "mvdr_mask_tse", "mvdr_online_est_dfn3",
         "mvdr_online_est_tse", "mvdr_online_dir_est_tse", "tse_dryenrol", "ref_image"]
LABEL = {"noisy": "Unprocessed mic 0", "rnnoise": "RNNoise (1-ch)", "deepfilternet3": "DeepFilterNet3 (1-ch)",
         "tse": "TSE Conv-TasNet+ECAPA (1-ch)", "ds_est": "Delay-and-sum, est. DOA", "mvdr_online_est": "Online MVDR, est. DOA",
         "mvdr_online_dir_est": "Online MVDR dir-gated, est. DOA", "mvdr_online_ref": "Online MVDR, ref. DOA (oracle geom.)",
         "mvdr_online_dir_ref": "Online MVDR dir-gated, ref. DOA (oracle geom.)", "mvdr_mask_demucs": "Mask MVDR (Demucs mask, offline)",
         "mvdr_mask_tse": "Mask MVDR (TSE mask, offline)", "mvdr_online_est_dfn3": "Online MVDR est. -> DFN3",
         "mvdr_online_est_tse": "Online MVDR est. -> TSE", "mvdr_online_dir_est_tse": "Online MVDR dir est. -> TSE",
         "tse_dryenrol": "TSE, studio-clean enrolment (sensitivity)", "ref_image": "Target image alone (ceiling)"}
B = 2000


def cluster_of(i):
    c, s = i.split("_")[:2]
    return f"{c}_{s}"


def boot(df, col, rng, stat=np.mean):
    """cluster bootstrap of the mean of df[col] (rows carry 'cl')."""
    g = {k: v[col].to_numpy() for k, v in df.groupby("cl")}
    keys = list(g)
    if not keys:
        return np.nan, np.nan, np.nan
    est = stat(np.concatenate([g[k] for k in keys]))
    bs = []
    for _ in range(B):
        pick = rng.choice(len(keys), len(keys))
        bs.append(stat(np.concatenate([g[keys[j]] for j in pick])))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(est), float(lo), float(hi)


def boot_p(df, col, rng):
    """two-sided cluster-bootstrap p-value for mean(df[col]) == 0 (percentile method)."""
    g = {k: v[col].to_numpy() for k, v in df.groupby("cl")}
    keys = list(g)
    if len(keys) < 2:
        return np.nan
    bs = np.array([np.mean(np.concatenate([g[keys[j]] for j in rng.choice(len(keys), len(keys))])) for _ in range(B)])
    return float(min(1.0, 2 * min(np.mean(bs <= 0), np.mean(bs >= 0))))


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0
    for r, k in enumerate(o):
        run = max(run, min(1.0, (m - r) * ps[k])); adj[k] = run
    return adj


def paired(w, col, base="noisy"):
    b = w[w.method == base].set_index("id")[col]
    out = w.copy(); out["d"] = out[col] - out.id.map(b)
    return out.dropna(subset=["d"])


def fmt(e, lo, hi, p=2):
    return f"{e:+.{p}f} [{lo:+.{p}f}, {hi:+.{p}f}]"


def table(w, tag, rng, groups):
    rows = []
    for meth in [m for m in ORDER if m in set(w.method)]:
        for gname, conds in groups.items():
            s = w[(w.method == meth) & w.cond.isin(conds)]
            if s.empty:
                continue
            r = dict(tag=tag, method=meth, group=gname, n=len(s))
            for col in ("wer", "word_correct", "ins_rate"):
                r[col], r[col + "_lo"], r[col + "_hi"] = boot(s, col, rng)
            p = paired(w[w.cond.isin(conds)], "word_correct"); p = p[p.method == meth]
            r["d_wc"], r["d_wc_lo"], r["d_wc_hi"] = boot(p, "d", rng)
            r["n_paired"] = len(p); r["n_clusters"] = p.cl.nunique() if len(p) else 0
            r["p_wc"] = boot_p(p, "d", rng) if meth not in ("noisy",) and len(p) else np.nan
            p = paired(w[w.cond.isin(conds)], "wer"); p = p[p.method == meth]
            r["d_wer"], r["d_wer_lo"], r["d_wer_hi"] = boot(p, "d", rng)
            rows.append(r)
    T = pd.DataFrame(rows)
    if not T.empty:
        T["p_wc_holm"] = np.nan
        for g, idx in T.groupby("group").groups.items():
            sub = T.loc[idx]; k = sub.index[sub.p_wc.notna() & ~sub.method.isin(["ref_image"])]
            if len(k):
                T.loc[k, "p_wc_holm"] = holm(T.loc[k, "p_wc"].to_numpy())
    return T


def obj_table(mt, tag, rng, groups):
    rows = []
    for meth in [m for m in ORDER if m in set(mt.method)]:
        for gname, conds in groups.items():
            s = mt[mt.cond.isin(conds)]
            for col in ("si_sdr", "estoi"):
                p = paired(s, col); p = p[p.method == meth]
                if p.empty:
                    continue
                e, lo, hi = boot(p, "d", rng)
                rows.append(dict(tag=tag, method=meth, group=gname, metric=col, n=len(p), d=e, lo=lo, hi=hi,
                                 abs_mean=float(s[s.method == meth][col].mean())))
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(0)
    FIG.mkdir(parents=True, exist_ok=True)
    groups = {"0S (no overlap)": ["0S"], "OV10-40 (overlap)": ["OV10", "OV20", "OV40"], "OV10": ["OV10"], "OV20": ["OV20"], "OV40": ["OV40"]}
    W, M = {}, {}
    for tag in ("r5", "r5sim"):
        parts = sorted(R5.glob(f"wer_{tag}.csv")) + sorted(R5.glob(f"wer_{tag}.part*.csv"))
        if parts:
            w = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True).drop_duplicates(["method", "id"])
            w["cl"] = w.id.map(cluster_of); W[tag] = w
        p = R5 / f"metrics_{tag}.csv"
        if p.exists():
            m = pd.read_csv(p); m["cl"] = m.id.map(cluster_of); M[tag] = m
    T = pd.concat([table(W[t], t, rng, groups) for t in W], ignore_index=True)
    T.to_csv(R5 / "asr_summary.csv", index=False)
    O = pd.concat([obj_table(M[t], t, rng, groups) for t in M], ignore_index=True) if M else pd.DataFrame()
    O.to_csv(R5 / "objective_summary.csv", index=False)
    md = ["# Round 5 summary (generated by `python -m selab.analyze_r5`)", "",
          "Real = LibriCSS 7-mic recordings (24 recordings: 0S/OV10/OV20/OV40 x sessions 0-5; 6 target utterances each, n = 144).",
          "Sim = simulated twin of the same items (same dry feeds, timing, geometry, azimuths, levels and real room noise; shoebox room).",
          "CIs: 95% cluster bootstrap over recordings (24 clusters), 2000 resamples. d = method minus unprocessed mic 0 on the same item.", ""]
    for gname in ["0S (no overlap)", "OV10-40 (overlap)"]:
        md += [f"## ASR (Whisper base.en) — {gname}", "",
               "| Method | n | WER real | word-correct real | d word-correct real | d word-correct sim | insertions/ref word real |", "|---|---|---|---|---|---|---|"]
        for meth in [m for m in ORDER if m in set(T.method)]:
            rr = T[(T.tag == "r5") & (T.method == meth) & (T.group == gname)]
            rs = T[(T.tag == "r5sim") & (T.method == meth) & (T.group == gname)]
            if rr.empty:
                continue
            r = rr.iloc[0]
            sim = fmt(rs.iloc[0].d_wc, rs.iloc[0].d_wc_lo, rs.iloc[0].d_wc_hi) if not rs.empty else "not run"
            md.append(f"| {LABEL.get(meth, meth)} | {int(r.n)} | {r.wer:.3f} | {r.word_correct:.3f} | {fmt(r.d_wc, r.d_wc_lo, r.d_wc_hi)} | {sim} | {r.ins_rate:.3f} |")
        md.append("")
    md += ["## ASR by overlap condition (real): d word-correct vs unprocessed", "", "| Method | OV10 | OV20 | OV40 |", "|---|---|---|---|"]
    for meth in [m for m in ORDER if m in set(T.method) and m != "noisy"]:
        cells = []
        for g in ("OV10", "OV20", "OV40"):
            r = T[(T.tag == "r5") & (T.method == meth) & (T.group == g)]
            cells.append(fmt(r.iloc[0].d_wc, r.iloc[0].d_wc_lo, r.iloc[0].d_wc_hi) if not r.empty else "")
        md.append(f"| {LABEL.get(meth, meth)} | " + " | ".join(cells) + " |")
    md.append("")
    # sim-vs-real agreement
    if "r5" in W and "r5sim" in W:
        rows = []
        for gname in ["0S (no overlap)", "OV10-40 (overlap)"]:
            a = T[(T.tag == "r5") & (T.group == gname)].set_index("method").d_wc
            b = T[(T.tag == "r5sim") & (T.group == gname)].set_index("method").d_wc
            k = [m for m in a.index if m in b.index and m not in ("noisy", "ref_image")]
            from scipy.stats import spearmanr, pearsonr
            rho = spearmanr(a[k], b[k]).statistic if len(k) > 2 else np.nan
            # paired difference-in-differences per method (item-level, cluster bootstrap)
            for meth in k:
                pr = paired(W["r5"][W["r5"].cond.isin(groups[gname])], "word_correct"); pr = pr[pr.method == meth].set_index("id")
                ps = paired(W["r5sim"][W["r5sim"].cond.isin(groups[gname])], "word_correct"); ps = ps[ps.method == meth].set_index("id")
                j = pr.index.intersection(ps.index)
                dd = pd.DataFrame(dict(d=(pr.loc[j, "d"] - ps.loc[j, "d"]).values, cl=pr.loc[j, "cl"].values))
                e, lo, hi = boot(dd, "d", rng)
                rows.append(dict(group=gname, method=meth, real=a[meth], sim=b[meth], real_minus_sim=e, lo=lo, hi=hi, spearman_methods=rho))
        S = pd.DataFrame(rows); S.to_csv(R5 / "sim_vs_real.csv", index=False)
        md += ["## Sim vs real (paired by item): d word-correct real minus d word-correct sim", ""]
        for gname, g in S.groupby("group", sort=False):
            md += [f"**{gname}** — Spearman rank correlation of the method effects, real vs sim: {g.spearman_methods.iloc[0]:.2f} (over {len(g)} methods)", "",
                   "| Method | d real | d sim | real - sim [95% CI] |", "|---|---|---|---|"]
            for _, r in g.iterrows():
                md.append(f"| {LABEL.get(r.method, r.method)} | {r.real:+.3f} | {r.sim:+.3f} | {fmt(r.real_minus_sim, r.lo, r.hi, 3)} |")
            md.append("")
        base = T[(T.method == "noisy") & (T.group == "OV10-40 (overlap)")].set_index("tag")
        if len(base) == 2:
            md += [f"Unprocessed WER on overlapped items: real {base.loc['r5','wer']:.3f} [{base.loc['r5','wer_lo']:.3f}, {base.loc['r5','wer_hi']:.3f}], "
                   f"sim {base.loc['r5sim','wer']:.3f} [{base.loc['r5sim','wer_lo']:.3f}, {base.loc['r5sim','wer_hi']:.3f}].", ""]
    if not O.empty:
        md += ["## Objective metrics vs reference (real: ESTIMATED reverberant target image; sim: exact image)", "",
               "| Method | group | d SI-SDR real (dB) | d SI-SDR sim (dB) | d ESTOI real | d ESTOI sim |", "|---|---|---|---|---|---|"]
        for meth in [m for m in ORDER if m in set(O.method) and m != "noisy"]:
            for gname in ["0S (no overlap)", "OV10-40 (overlap)"]:
                c = []
                for met in ("si_sdr", "estoi"):
                    for tag in ("r5", "r5sim"):
                        r = O[(O.tag == tag) & (O.method == meth) & (O.group == gname) & (O.metric == met)]
                        c.append(fmt(r.iloc[0].d, r.iloc[0].lo, r.iloc[0].hi, 2 if met == "si_sdr" else 3) if not r.empty else "not run")
                md.append(f"| {LABEL.get(meth, meth)} | {gname} | {c[0]} | {c[1]} | {c[2]} | {c[3]} |")
        md.append("")
    # DOA
    for tag in ("r5", "r5sim"):
        p = R5 / f"doa_{tag}.csv"
        if not p.exists():
            continue
        d = pd.read_csv(p); d["cl"] = d.id.map(cluster_of)
        md += [f"## DOA error ({'real' if tag == 'r5' else 'sim twin'}), degrees vs system-identification reference (n = {len(d)} items with a valid reference)", "",
               "| Estimator | group | median abs error | % within 10 deg [95% CI] |", "|---|---|---|---|"]
        for col, name in (("err_blind", "SRP-PHAT, whole segment (blind)"), ("err_tonly", "SRP-PHAT, target-only frames (oracle timing)"),
                          ("err_causal_final", "causal running SRP, end of segment"), ("err_causal_median", "causal running SRP, median over hops"),
                          ("err_pra_srp", "pyroomacoustics SRP (first 24 items)"), ("err_pra_music", "pyroomacoustics MUSIC (first 24 items)")):
            if col not in d:
                continue
            for gname, conds in (("0S", ["0S"]), ("OV10-40", ["OV10", "OV20", "OV40"])):
                s = d[d.cond.isin(conds)].dropna(subset=[col]).copy()
                if s.empty:
                    continue
                s["w10"] = (s[col] <= 10).astype(float)
                e, lo, hi = boot(s, "w10", rng)
                md.append(f"| {name} | {gname} (n={len(s)}) | {s[col].median():.1f} | {100*e:.0f}% [{100*lo:.0f}, {100*hi:.0f}] |")
        if "causal_frac_within_10" in d:
            md += ["", f"Causal tracker: mean fraction of 16-ms hops within 10 deg of the reference = {d.causal_frac_within_10.mean():.2f}.", ""]
    ref = R5 / "doa_reference_by_loudspeaker.csv"
    if ref.exists():
        r = pd.read_csv(ref); multi = r[r.n_recordings > 1]
        md += [f"Reference self-consistency: {len(multi)} loudspeaker positions were identified in 2-4 independent recordings; "
               f"max deviation from their circular median: median {multi.max_dev.median():.1f} deg, worst {multi.max_dev.max():.1f} deg.", ""]
    # runtime
    rt = []
    for f in sorted(R5.glob("runtime_r5_*.json")):
        j = json.load(open(f)); rt.append((j["method"], j.get("rtf"), (j.get("streaming") or {}).get("per_hop_ms"), j.get("latency")))
    if rt:
        md += ["## Runtime on the real set (2 vCPU aarch64; NOTE: shared with unrelated jobs, RTFs are upper bounds)", "",
               "| Method | RTF | per-hop ms (16 ms hop) | latency |", "|---|---|---|---|"]
        seen = {}
        for m_, r_, h_, l_ in rt:
            seen[m_] = (r_, h_, l_)
        for m_ in [m for m in ORDER if m in seen]:
            r_, h_, l_ = seen[m_]
            md.append(f"| {LABEL.get(m_, m_)} | {r_:.3f} | {'' if h_ is None else f'{h_:.2f}'} | {l_} |" if r_ is not None else f"| {m_} | | | {l_} |")
        md.append("")
    md += extra_sections(W, T, rng, groups)
    open(R5 / "summary_r5.md", "w").write("\n".join(md))
    figs(T, W)
    print("\n".join(md))


CORE = ["noisy", "ds_est", "mvdr_online_est", "deepfilternet3", "tse", "mvdr_online_est_dfn3", "mvdr_online_est_tse"]


def extra_sections(W, T, rng, groups):
    md = []
    # multiple comparisons
    if not T.empty and "p_wc_holm" in T:
        md += ["## Multiple comparisons (real set): cluster-bootstrap p for d word-correct = 0, Holm-adjusted within each group", "",
               "| Method | group | n items (clusters) | d word-correct [95% CI] | p | p Holm |", "|---|---|---|---|---|---|"]
        for gname in ["0S (no overlap)", "OV10-40 (overlap)"]:
            for _, r in T[(T.tag == "r5") & (T.group == gname) & T.p_wc.notna()].iterrows():
                md.append(f"| {LABEL.get(r.method, r.method)} | {gname} | {int(r.n_paired)} ({int(r.n_clusters)}) | {fmt(r.d_wc, r.d_wc_lo, r.d_wc_hi, 3)} | {r.p_wc:.3f} | {r.p_wc_holm:.3f} |")
        md += ["", "p resolution is 1/2000 (bootstrap); p = 0.000 means no resample crossed zero.", ""]
    # common item set for the core methods (levels comparable across methods)
    if "r5" in W:
        w = W["r5"]; have = [m for m in CORE if m in set(w.method)]
        ids = set.intersection(*[set(w[w.method == m].id) for m in have]) if have else set()
        if ids:
            s = w[w.id.isin(ids)]
            md += [f"## Core methods on one common item set (real; n = {len(ids)} items, {s[s.id.isin(ids)].cl.nunique()} recordings)", "",
                   "| Method | WER | word-correct | d word-correct vs unprocessed [95% CI] | insertions/ref word |", "|---|---|---|---|---|"]
            for m in have:
                a = s[s.method == m]; e, lo, hi = boot(a, "word_correct", rng)
                p = paired(s, "word_correct"); p = p[p.method == m]; de = boot(p, "d", rng)
                md.append(f"| {LABEL.get(m, m)} | {a.wer.mean():.3f} | {e:.3f} [{lo:.3f}, {hi:.3f}] | {fmt(*de, 3)} | {a.ins_rate.mean():.3f} |")
            md.append("")
    # sensitivity: dry enrolment
    if "r5" in W and "tse_dryenrol" in set(W["r5"].method):
        w = W["r5"]; a = w[w.method == "tse_dryenrol"].set_index("id"); b = w[w.method == "tse"].set_index("id")
        j = a.index.intersection(b.index)
        if len(j):
            from .common import OUT, load
            same = sum(bool(np.max(np.abs(load(OUT / "r5" / "tse_dryenrol" / f"{i}.wav") - load(OUT / "r5" / "tse" / f"{i}.wav"))) < 1e-6) for i in j)
            dd = pd.DataFrame(dict(d=(a.loc[j, "word_correct"] - b.loc[j, "word_correct"]).values, cl=a.loc[j, "cl"].values))
            md += ["## Sensitivity: enrolment from the same room vs studio-clean enrolment (TSE, real set)", "",
                   f"Same enrolment utterance, taken from the dry loudspeaker feed instead of the in-room mic-0 recording. n = {len(j)} items, {dd.cl.nunique()} recordings.", "",
                   f"word-correct, in-room enrolment {b.loc[j, 'word_correct'].mean():.3f}; studio enrolment {a.loc[j, 'word_correct'].mean():.3f}; "
                   f"identical output files (same separated stream selected) in {same}/{len(j)} items; "
                   f"difference (studio minus in-room) {fmt(*boot(dd, 'd', rng), 3)}.", ""]
    # sensitivity: oracle utterance boundaries
    parts = sorted(R5.glob("wer_r5ctx*.csv"))
    if parts:
        c = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True).drop_duplicates(["method", "id"]); c["cl"] = c.id.map(cluster_of)
        md += ["## Sensitivity: oracle utterance boundaries (real set, 2 s of extra context on each side)", "",
               "Full window: the output over the whole longer window is transcribed and scored against the target sentence, so "
               "transcribed interferer words count as insertions (no oracle timing at scoring). Cut: the method ran on the long window "
               "(no oracle start for the tracker/extractor) but the output is trimmed to the oracle span for scoring.", "",
               "| Method | scoring | n | WER | word-correct | insertions/ref word | d word-correct vs unprocessed (same scoring) |", "|---|---|---|---|---|---|---|"]
        for scoring, suf in (("full window", ""), ("cut to oracle span", "_cut")):
            base = c[c.method == "noisy" + suf].set_index("id")
            for m in [x for x in CORE + ["tse_dryenrol"] if (x + suf) in set(c.method)]:
                a = c[c.method == m + suf].set_index("id"); j = a.index.intersection(base.index)
                if not len(j):
                    continue
                dd = pd.DataFrame(dict(d=(a.loc[j, "word_correct"] - base.loc[j, "word_correct"]).values, cl=a.loc[j, "cl"].values))
                md.append(f"| {LABEL.get(m, m)} | {scoring} | {len(a)} | {a.wer.mean():.3f} | {a.word_correct.mean():.3f} | {a.ins_rate.mean():.3f} | "
                          f"{fmt(*boot(dd, 'd', rng), 3) if m != 'noisy' else ''} |")
        md.append("")
    # sensitivity: estimated reference (on the twin)
    p = R5 / "sens_ref_r5.csv"
    if p.exists():
        o = pd.read_csv(p)
        md += ["## Sensitivity: objective deltas against an exact vs a degraded (-10 dB RIR-error) reference, simulated twin", "",
               "| Method | n | d SI-SDR exact ref | d SI-SDR degraded ref | d ESTOI exact | d ESTOI degraded |", "|---|---|---|---|---|---|"]
        for m in o.method.unique():
            a = o[(o.method == m) & (o.ref == "exact")].iloc[0]; b = o[(o.method == m) & (o.ref == "perturbed")].iloc[0]
            md.append(f"| {LABEL.get(m, m)} | {int(a.n)} | {a.d_si_sdr:+.2f} | {b.d_si_sdr:+.2f} | {a.d_estoi:+.3f} | {b.d_estoi:+.3f} |")
        md.append("")
    J = {k: json.load(open(R5 / f"rtf_cpu_r5_{k}.json")) for k in ("loaded", "idle") if (R5 / f"rtf_cpu_r5_{k}.json").exists()}
    if J:
        md += ["## Runtime, load-robust check (single thread requested; same 3 OV20 items; warm-up excluded)", ""]
        for k, j in J.items():
            md.append(f"- {k}: 1-min load average {j['load_before'][0]:.1f} before, {j['load_after'][0]:.1f} after.")
        md += ["", "| Method | " + " | ".join(f"RTF wall ({k}) | RTF CPU ({k})" for k in J) + " |", "|---|" + "---|---|" * len(J)]
        for m in next(iter(J.values()))["methods"]:
            md.append(f"| {LABEL.get(m, m)} | " + " | ".join(f"{J[k]['methods'][m]['rtf_wall']:.3f} | {J[k]['methods'][m]['rtf_cpu']:.3f}" for k in J) + " |")
        md += ["", "CPU > wall means the library used more than one thread despite the 1-thread setting.", ""]
    return md


def figs(T, W):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for gname in ["0S (no overlap)", "OV10-40 (overlap)"]:
        meths = [m for m in ORDER if m not in ("noisy",) and m in set(T.method)]
        fig, ax = plt.subplots(figsize=(9, 5.5))
        y = np.arange(len(meths))
        for k, (tag, col) in enumerate((("r5", "#1f5fa8"), ("r5sim", "#e08a1e"))):
            s = T[(T.tag == tag) & (T.group == gname)].set_index("method")
            v = [s.d_wc.get(m, np.nan) for m in meths]
            lo = [s.d_wc.get(m, np.nan) - s.d_wc_lo.get(m, np.nan) for m in meths]
            hi = [s.d_wc_hi.get(m, np.nan) - s.d_wc.get(m, np.nan) for m in meths]
            ax.barh(y + (0.2 if k else -0.2), v, 0.4, xerr=[lo, hi], color=col, label="real LibriCSS" if tag == "r5" else "simulated twin", capsize=2)
        ax.set_yticks(y); ax.set_yticklabels([LABEL.get(m, m) for m in meths], fontsize=8); ax.invert_yaxis()
        ax.axvline(0, color="k", lw=0.8); ax.set_xlabel("Δ word-correct vs unprocessed mic 0 (Whisper base.en), 95% cluster-bootstrap CI")
        ax.set_title(f"Round 5, {gname}: real vs simulated twin"); ax.legend(loc="lower left", fontsize=8)
        fig.tight_layout(); fig.savefig(FIG / f"dwc_{'0S' if gname.startswith('0S') else 'OV'}.png", dpi=130); plt.close(fig)
    p = R5 / "doa_r5.csv"
    if p.exists():
        d = pd.read_csv(p)
        fig, ax = plt.subplots(figsize=(6, 4))
        for col, name in (("err_blind", "SRP blind (segment)"), ("err_tonly", "SRP target-only frames"), ("err_causal_final", "causal SRP (end)")):
            v = np.sort(d[col].to_numpy()); ax.plot(v, np.arange(1, len(v) + 1) / len(v), label=name)
        ax.set_xscale("symlog", linthresh=1); ax.set_xlabel("absolute DOA error (deg)"); ax.set_ylabel("fraction of items")
        ax.set_title("DOA error on real LibriCSS items"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(FIG / "doa_cdf.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    main()
