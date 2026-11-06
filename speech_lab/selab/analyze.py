"""Aggregate metrics -> tables + figures.  python -m selab.analyze --tag r1
All improvements are PAIRED per utterance against the unprocessed mixture (method 'noisy'),
so methods run on subsets (sepformer_enh) are still compared like-for-like. 95% CIs: bootstrap over utterances.
"""
import argparse, json, glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .common import RES, MIX, OUT, load

ORDER = ["noisy", "specsub", "wiener_dd", "mmse_lsa", "noisereduce", "specsub_oraclenoise", "wiener_dd_oraclenoise",
         "mmse_lsa_oraclenoise", "metricgan_plus", "demucs_dns64", "sepformer_enh", "tse_convtasnet_ecapa",
         "demucs_then_tse", "tse_convtasnet_oracle", "bf_ds", "bf_mvdr_ff", "bf_mvdr_mask", "bf_mvdr_mask_pf", "bf_mvdr_oracle"]
SC_CONDS = ["babble", "traffic", "broadband_env", "pink", "competing", "reverb_babble"]


def boot_ci(x, n=2000, seed=0):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 2:
        return (np.nan, np.nan)
    r = np.random.default_rng(seed)
    b = r.choice(x, (n, len(x))).mean(1)
    return tuple(np.percentile(b, [2.5, 97.5]))


def word_correct_rate(ref_text, hyp):
    """Fraction of reference words recognised (hits / N). Unlike WER it is not inflated by insertions,
    e.g. when the ASR also transcribes the competing talker or hallucinates on noise - closer to
    keyword-correct scoring used in human intelligibility tests."""
    import jiwer, re
    f = lambda s: " ".join(re.sub(r"[^a-z' ]", " ", str(s).lower()).split())
    h = f(hyp) if isinstance(hyp, str) else ""
    o = jiwer.process_words(f(ref_text), h or "x")
    return o.hits / (o.hits + o.substitutions + o.deletions)


def load_all(tag, asr_k=3):
    d = RES / tag
    df = pd.read_csv(d / "metrics.csv")
    if (d / "wer.csv").exists():
        meta = {m["id"]: m for m in json.load(open(MIX / tag / "meta.json"))}
        w = pd.read_csv(d / "wer.csv")
        # ASR was run on the first asr_k utterances per cell only (CPU budget); keep exactly that subset for all methods
        w = w[w.id.str.rsplit("_", n=1).str[1].astype(int) < asr_k].copy()
        w["wcr"] = [word_correct_rate(meta[i]["text"], h) for i, h in zip(w.id, w.hyp)]
        w = w[["method", "id", "wer", "wcr"]]
        df = df.merge(w, on=["method", "id"], how="left")
        clean = w[w.method == "clean_ref"].set_index("id")["wer"]
    else:
        clean = None
    base = df[df.method == "noisy"].set_index("id")
    for k in ["si_sdr", "stoi", "estoi", "pesq"] + (["wer", "wcr"] if "wer" in df else []):
        df["d_" + k] = df[k] - df.id.map(base[k])
    rt = {}
    for f in glob.glob(str(d / "runtime_*.json")):
        j = json.load(open(f)); rt[j["method"]] = j
    return df, rt, clean


def order(ms):
    return [m for m in ORDER if m in ms] + sorted(m for m in ms if m not in ORDER)


def table(df, rt, metric_cols, subset):
    rows = []
    for m in order(df.method.unique()):
        g = df[(df.method == m) & df.cond.isin(subset)]
        if g.empty:
            continue
        r = dict(method=m, n=len(g))
        for c in metric_cols:
            r[c] = g[c].mean()
            lo, hi = boot_ci(g[c]); r[c + "_ci"] = f"[{lo:.2f}, {hi:.2f}]"
        j = rt.get(m, {})
        r.update(rtf=j.get("rtf"), peak_rss_mb=j.get("peak_rss_mb"), n_params=j.get("n_params"), n_fail=j.get("n_fail"))
        rows.append(r)
    return pd.DataFrame(rows)


def fmt(t, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in t.iterrows():
        cells = []
        for c in cols:
            v = r.get(c)
            if isinstance(v, float):
                cells.append("" if np.isnan(v) else (f"{v:.3f}" if abs(v) < 10 and c not in ("peak_rss_mb",) else f"{v:.0f}"))
            elif v is None:
                cells.append("")
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def heat(df, metric, conds, path, title):
    ms = [m for m in order(df.method.unique()) if m != "noisy"]
    M = np.array([[df[(df.method == m) & (df.cond == c)][metric].mean() for c in conds] for m in ms])
    keep = ~np.all(np.isnan(M), axis=1)
    ms = [m for m, k in zip(ms, keep) if k]; M = M[keep]
    fig, ax = plt.subplots(figsize=(1.3 * len(conds) + 3, 0.42 * len(ms) + 1.5))
    v = np.nanmax(np.abs(M))
    im = ax.imshow(M, cmap="RdBu", vmin=-v, vmax=v, aspect="auto")
    ax.set_xticks(range(len(conds)), conds, rotation=30, ha="right"); ax.set_yticks(range(len(ms)), ms)
    for i in range(len(ms)):
        for j in range(len(conds)):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}" if abs(M[i, j]) < 10 else f"{M[i, j]:.0f}", ha="center", va="center", fontsize=8)
    plt.colorbar(im, ax=ax, shrink=0.8); ax.set_title(title)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def snr_lines(df, metric, conds, path, ylabel, methods):
    fig, axes = plt.subplots(1, len(conds), figsize=(3.2 * len(conds), 3.2), sharey=True)
    for ax, c in zip(np.atleast_1d(axes), conds):
        for m in methods:
            g = df[(df.method == m) & (df.cond == c)].groupby("snr")[metric].mean()
            if len(g):
                ax.plot(g.index, g.values, marker="o", label=m)
        ax.set_title(c); ax.set_xlabel("input SNR (dB)"); ax.grid(alpha=.3)
    np.atleast_1d(axes)[0].set_ylabel(ylabel)
    np.atleast_1d(axes)[-1].legend(fontsize=7, loc="best")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def cost_plot(t, metric, path):
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for _, r in t.iterrows():
        if r["rtf"] is None or (isinstance(r["rtf"], float) and np.isnan(r["rtf"])) or r.method == "noisy":
            continue
        ax.scatter(r["rtf"], r[metric]); ax.annotate(r.method, (r["rtf"], r[metric]), fontsize=7)
    ax.set_xscale("log"); ax.set_xlabel("real-time factor on 2 vCPU (log; <1 = faster than real time)")
    ax.set_ylabel(metric); ax.axhline(0, color="k", lw=.5); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def spectro_panel(tag, mid, methods, path):
    import librosa, librosa.display
    sigs = [("mixture", MIX / tag / mid / "mix.wav"), ("reference", MIX / tag / mid / "ref.wav")] + \
           [(m, OUT / tag / m / f"{mid}.wav") for m in methods]
    sigs = [s for s in sigs if s[1].exists()]
    fig, axes = plt.subplots(len(sigs), 1, figsize=(9, 1.6 * len(sigs)), sharex=True)
    for ax, (name, p) in zip(axes, sigs):
        x = load(p)
        S = librosa.amplitude_to_db(np.abs(librosa.stft(x, n_fft=512, hop_length=128)), ref=np.max)
        librosa.display.specshow(S, sr=16000, hop_length=128, y_axis="hz", x_axis="time", ax=ax, vmin=-80, vmax=0)
        ax.set_title(name, fontsize=8, loc="left"); ax.set_ylabel("")
    fig.suptitle(mid); fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="r1"); ap.add_argument("--asr_k", type=int, default=3)
    a = ap.parse_args()
    df, rt, clean = load_all(a.tag, a.asr_k)
    fd = RES / a.tag / "figs"; fd.mkdir(parents=True, exist_ok=True)
    mc = ["d_si_sdr", "d_estoi", "d_pesq"] + (["wcr", "d_wcr", "d_wer"] if "wer" in df else [])
    t_sc = table(df, rt, mc, SC_CONDS)
    arr = [c for c in df.cond.unique() if c.startswith("array")]
    t_ar = table(df, rt, mc, arr)
    per = df.groupby(["method", "cond"])[[c for c in mc]].mean().reset_index()
    per.to_csv(RES / a.tag / "per_condition_means.csv", index=False)
    t_sc.to_csv(RES / a.tag / "summary_single_channel.csv", index=False)
    t_ar.to_csv(RES / a.tag / "summary_array.csv", index=False)
    heat(df, "d_estoi", SC_CONDS, fd / "heat_d_estoi.png", "ΔESTOI vs unprocessed (single-channel conditions)")
    heat(df, "d_si_sdr", SC_CONDS, fd / "heat_d_sisdr.png", "SI-SDR improvement (dB)")
    if "wer" in df:
        heat(df, "d_wcr", SC_CONDS + arr, fd / "heat_d_wcr.png", "Δ ASR word-correct rate vs unprocessed (positive = better)")
    if arr:
        heat(df, "d_estoi", arr, fd / "heat_array_d_estoi.png", "ΔESTOI, 4-mic array conditions")
    key = [m for m in ["noisy", "wiener_dd", "metricgan_plus", "demucs_dns64", "tse_convtasnet_ecapa", "sepformer_enh"] if m in df.method.unique()]
    snr_lines(df, "estoi", SC_CONDS, fd / "estoi_vs_snr.png", "ESTOI", key)
    if "wer" in df:
        snr_lines(df, "wcr", SC_CONDS, fd / "wcr_vs_snr.png", "ASR word-correct rate (Whisper base.en)", key)
    cost_plot(t_sc, "d_estoi", fd / "cost_vs_benefit.png")
    for mid in ["babble_snr+0_00", "competing_snr+0_00", "traffic_snr-5_00", "reverb_babble_snr+0_00"]:
        if not (MIX / a.tag / mid).exists():
            continue
        spectro_panel(a.tag, mid, ["wiener_dd", "demucs_dns64", "tse_convtasnet_ecapa"], fd / f"spec_{mid}.png")
    cols = ["method", "n"] + mc + ["rtf", "peak_rss_mb", "n_params"]
    with open(RES / a.tag / "summary.md", "w") as f:
        f.write(f"# Results {a.tag}\n\nPaired deltas vs unprocessed mixture (d_*). wcr = Whisper base.en word-correct rate (hits/N, higher better); d_wer = change in WER (negative better). ASR columns use only the first {a.asr_k} utterances of each condition x SNR cell.\n\n")
        if clean is not None:
            f.write(f"Clean-reference WER ceiling: {clean.mean():.3f}\n\n")
        f.write("## Single-channel conditions\n\n" + fmt(t_sc, cols) + "\n\n## Array conditions (mic-0 for single-channel methods)\n\n" + fmt(t_ar, cols) + "\n\n")
        f.write("## 95% bootstrap CIs (single-channel)\n\n" + fmt(t_sc, ["method"] + [c + "_ci" for c in mc]) + "\n")
    print(open(RES / a.tag / "summary.md").read())


if __name__ == "__main__":
    main()
