"""Round-3 analysis: out-of-domain (OOD) table, in-domain vs OOD generalisation gap, and the latency-budget table.

    python -m selab.analyze_r3      -> results/r3/summary_r3.md, results/r3/*.csv, results/r3/figs/*.png
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .common import RES, MIX
from .analyze import word_correct_rate

OUT = RES / "r3"


def load(tag, k_asr):
    m = pd.read_csv(RES / tag / "metrics.csv")
    m["cond"] = m.id.str.replace(r"_snr.*", "", regex=True)
    base = m[m.method == "noisy"].set_index("id")
    for c in ["si_sdr", "estoi", "pesq"]:
        m["d_" + c] = m[c] - m.id.map(base[c])
    w = pd.read_csv(RES / tag / "wer.csv")
    meta = {x["id"]: x for x in json.load(open(MIX / tag / "meta.json"))}
    w["wcr"] = [word_correct_rate(meta[i]["text"], h) for i, h in zip(w.id, w.hyp.fillna(""))]
    w = w[w.id.str[-2:].astype(int) < k_asr]
    wb = w[w.method == "noisy"].set_index("id")["wcr"]
    w["d_wcr"] = w.wcr - w.id.map(wb)
    m = m.merge(w[["method", "id", "wcr", "d_wcr"]], on=["method", "id"], how="left")
    return m


def boot_ci(x, n=2000, seed=0):
    x = np.asarray(x.dropna())
    if len(x) < 2:
        return np.nan, np.nan
    b = np.random.default_rng(seed).choice(x, (n, len(x))).mean(1)
    return np.percentile(b, 2.5), np.percentile(b, 97.5)


def runtime(tag, m):
    for suf in ["_resume", ""]:
        p = RES / tag / f"runtime_{m}{suf}.json"
        if p.exists():
            d = json.load(open(p))
            if d.get("rtf"):
                return d
    return {}


def main():
    (OUT / "figs").mkdir(parents=True, exist_ok=True)
    r3 = load("r3", 4)
    lines = ["# Round 3 results: out-of-domain test + latency budget\n",
             "OOD set: 144 mixtures, CMU ARCTIC talkers (Scottish/US/Indian-English targets; disjoint interferer talkers), "
             "recorded MS-SNSD test noise, SNR -5/0/+5 dB, 8 utterances per cell. Deltas are paired vs the unprocessed mixture. "
             "ASR = Whisper base.en word-correct rate on the first 4 utterances of each cell (72 per method). "
             "95% CIs are bootstrap over mixtures.\n"]
    # --- overall OOD table
    rows = []
    for meth, g in r3.groupby("method"):
        if meth == "noisy":
            continue
        lo, hi = boot_ci(g.d_estoi)
        alo, ahi = boot_ci(g.d_wcr)
        rt = runtime("r3", meth)
        rows.append(dict(method=meth, d_si_sdr=g.d_si_sdr.mean(), d_estoi=g.d_estoi.mean(), estoi_ci=f"[{lo:.3f}, {hi:.3f}]",
                         d_pesq=g.d_pesq.mean(), d_wcr=g.d_wcr.mean(), wcr_ci=f"[{alo:.2f}, {ahi:.2f}]",
                         rtf=rt.get("rtf"), peak_rss_mb=rt.get("peak_rss_mb")))
    t = pd.DataFrame(rows).sort_values("d_estoi", ascending=False)
    t.to_csv(OUT / "summary_ood.csv", index=False)
    lines += ["## Overall (all six OOD conditions)\n", t.round(3).to_markdown(index=False), ""]
    for v, lab in [("d_estoi", "ΔESTOI"), ("d_si_sdr", "ΔSI-SDR (dB)"), ("d_wcr", "Δ ASR word-correct rate")]:
        p = r3[r3.method != "noisy"].pivot_table(index="method", columns="cond", values=v)
        p.round(3).to_csv(OUT / f"by_cond_{v}.csv")
        lines += [f"## {lab} by condition\n", p.round(2 if v != "d_si_sdr" else 1).to_markdown(), ""]
        if v == "d_estoi":
            fig, ax = plt.subplots(figsize=(9, 5))
            im = ax.imshow(p.values, cmap="RdBu", vmin=-0.3, vmax=0.3, aspect="auto")
            ax.set_xticks(range(p.shape[1])); ax.set_xticklabels(p.columns, rotation=30, ha="right")
            ax.set_yticks(range(p.shape[0])); ax.set_yticklabels(p.index)
            for i in range(p.shape[0]):
                for j in range(p.shape[1]):
                    ax.text(j, i, f"{p.values[i, j]:+.2f}", ha="center", va="center", fontsize=8, color="white" if abs(p.values[i, j]) > 0.18 else "black")
            plt.colorbar(im, ax=ax); ax.set_title("Round 3 (out-of-domain): ΔESTOI vs unprocessed")
            fig.tight_layout(); fig.savefig(OUT / "figs" / "heat_d_estoi_ood.png", dpi=130); plt.close(fig)

    # --- generalisation gap: matched conditions in-domain (r1+r2 pooled) vs OOD
    pairs = {"competing": "ood_competing", "babble": "rec_babble", "broadband_env": "rec_transient", "pink": "rec_hvac"}
    ind = pd.concat([load("r1", 3).assign(rnd="r1"), load("r2", 4).assign(rnd="r2")])
    meths = ["wiener_dd", "rnnoise", "deepfilternet3", "demucs_dns64", "metricgan_plus", "tse_convtasnet_ecapa"]
    gap = []
    for a, b in pairs.items():
        for mth in meths:
            gi = ind[(ind.cond == a) & (ind.method == mth)]
            go = r3[(r3.cond == b) & (r3.method == mth)]
            gap.append(dict(method=mth, in_domain=a, ood=b, d_estoi_in=gi.d_estoi.mean(), d_estoi_ood=go.d_estoi.mean(),
                            d_sisdr_in=gi.d_si_sdr.mean(), d_sisdr_ood=go.d_si_sdr.mean()))
    g = pd.DataFrame(gap)
    g.to_csv(OUT / "generalisation_gap.csv", index=False)
    lines += ["## In-domain (LibriSpeech + ESC-50/MUSAN/synthetic, r1+r2 pooled) vs OOD (ARCTIC + recorded MS-SNSD), roughly matched noise types\n",
              "Matches are approximate: pink->recorded HVAC/vacuum (stationary), environmental->recorded transients, "
              "babble->recorded babble, competing->competing. In-domain SNRs span -10..+10 dB, OOD -5..+5 dB.\n",
              g.round(3).to_markdown(index=False), ""]

    # --- latency budget table (single-channel on OOD set, array on r1 array conditions)
    r1 = load("r1", 3)
    arr = r1[r1.cond.str.startswith("array")]
    lat = [  # algorithmic latency (ms): window + lookahead; sources in REPORT §8
        ("wiener_stream8", 8, "streamed frame by frame here", "r3"), ("wiener_stream16", 16, "streamed", "r3"),
        ("rnnoise", 20, "measured 320-sample delay @16 kHz (10 ms frame + 10 ms)", "r3"),
        ("wiener_stream32", 32, "streamed", "r3"), ("wiener_dd", 32, "offline loop, same 32 ms STFT", "r3"),
        ("deepfilternet3", 40, "20 ms window + 2x10 ms lookahead (config.ini); run offline here", "r3"),
        ("demucs_dns64", 41.3, "streaming wrapper, 1-frame (RTF 2.52: not real-time on this CPU)", "r3"),
        ("tse_convtasnet_ecapa", None, "non-causal checkpoint, whole utterance", "r3"),
        ("bf_online_ff", 32, "4-mic online MVDR, streamed frame by frame", "r1-array"),
        ("bf_online_ff_rnnoise", 52, "online MVDR + RNNoise", "r1-array"),
        ("bf_mvdr_ff", None, "offline (utterance-level covariance)", "r1-array")]
    rows = []
    for mth, ms, note, src in lat:
        d = r3 if src == "r3" else arr
        gm = d[d.method == mth]
        rt = runtime("r3" if src == "r3" else "r1", mth)
        st = rt.get("streaming") or {}
        rows.append(dict(method=mth, algo_latency_ms=ms, set=src, d_estoi=gm.d_estoi.mean(), d_si_sdr=gm.d_si_sdr.mean(),
                         d_wcr=gm.d_wcr.mean(), rtf=rt.get("rtf"), per_hop_ms=st.get("per_hop_ms"), hop_ms=st.get("hop_ms"), note=note))
    L = pd.DataFrame(rows)
    L.to_csv(OUT / "latency_budget.csv", index=False)
    lines += ["## Latency budget (algorithmic latency vs benefit)\n",
              "rtf = processing time / audio duration on 2 vCPU aarch64 (offline batch unless per_hop_ms is given, in which case it was "
              "processed hop by hop and per_hop_ms is the mean compute per hop). Single-channel rows are on the OOD set; bf_* rows on the "
              "round-1 simulated 4-mic array conditions (array_babble, array_competing).\n", L.round(3).to_markdown(index=False), ""]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for _, r in L.dropna(subset=["algo_latency_ms"]).iterrows():
        ax.scatter(r.algo_latency_ms, r.d_estoi, s=40, c="C1" if r.set != "r3" else "C0")
        ax.annotate(r.method, (r.algo_latency_ms, r.d_estoi), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set_xlim(0, 66); ax.axhline(0, color="k", lw=0.5); ax.set_xlabel("algorithmic latency (ms)"); ax.set_ylabel("mean ΔESTOI")
    ax.set_title("Benefit vs latency (blue: OOD single-channel, orange: simulated array)")
    fig.tight_layout(); fig.savefig(OUT / "figs" / "latency_vs_estoi.png", dpi=130); plt.close(fig)
    (OUT / "summary_r3.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
