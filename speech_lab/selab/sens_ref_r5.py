"""Sensitivity of the objective metrics to an ESTIMATED reference (critique fix), measured on the twin.

On the simulated twin the exact reverberant target image is known.  We degrade it the way system identification
degrades the real reference: the image is re-generated with an RIR error, e = ref * h_err, where h_err is a
random exponentially decaying filter (RT60 0.32 s, the fitted room) scaled so that the reference error is
-10 dB relative to the reference (the median sysid residual on the real data; an upper-end assumption because
that residual also contains the room noise).  Then every method's delta SI-SDR / ESTOI is computed against
both references, paired by item.  If the deltas barely move, real-set objective deltas computed against the
estimated reference can be read like the sim ones; if they are compressed, by how much.
python -m selab.sens_ref_r5   -> results/r5/sens_ref_r5.csv
"""
import json
import numpy as np, pandas as pd
from scipy.signal import fftconvolve
from .common import MIX, OUT, RES, FS, load
from .metrics import si_sdr, stoi
from .score_r5 import sub48

METHODS = ["noisy", "ds_est", "mvdr_online_est", "deepfilternet3", "tse"]


def perturbed(ref, rng, err_db=-10.0, rt60=0.32):
    n = int(0.25 * FS); t = np.arange(n) / FS
    h = rng.standard_normal(n) * np.exp(-6.91 * t / rt60)
    e = fftconvolve(ref, h)[: len(ref)]
    e *= np.sqrt(np.sum(ref ** 2) * 10 ** (err_db / 10) / (np.sum(e ** 2) + 1e-12))
    return ref + e


def main():
    meta = {m["id"]: m for m in json.load(open(MIX / "r5sim" / "meta.json"))}
    rng = np.random.default_rng(1)
    rows = []
    for i in sub48(meta):
        ref = load(MIX / "r5sim" / i / "ref.wav"); rp = perturbed(ref, rng)
        for me in METHODS:
            p = OUT / "r5sim" / me / f"{i}.wav"
            if not p.exists():
                continue
            y = load(p); n = min(len(ref), len(y))
            for kind, r in (("exact", ref), ("perturbed", rp)):
                rows.append(dict(id=i, cond=meta[i]["cond"], method=me, ref=kind, si_sdr=si_sdr(r[:n], y[:n]),
                                 estoi=stoi(r[:n], y[:n], extended=True)))
    df = pd.DataFrame(rows); df.to_csv(RES / "r5" / "sens_ref_r5_items.csv", index=False)
    out = []
    for kind in ("exact", "perturbed"):
        s = df[df.ref == kind].pivot_table(index="id", columns="method", values=["si_sdr", "estoi"])
        for me in METHODS[1:]:
            if ("si_sdr", me) not in s:
                continue
            out.append(dict(ref=kind, method=me, n=int(s[("si_sdr", me)].notna().sum()),
                            d_si_sdr=float((s[("si_sdr", me)] - s[("si_sdr", "noisy")]).mean()),
                            d_estoi=float((s[("estoi", me)] - s[("estoi", "noisy")]).mean()),
                            abs_si_sdr=float(s[("si_sdr", me)].mean())))
    o = pd.DataFrame(out); o.to_csv(RES / "r5" / "sens_ref_r5.csv", index=False); print(o.to_string())


if __name__ == "__main__":
    main()
