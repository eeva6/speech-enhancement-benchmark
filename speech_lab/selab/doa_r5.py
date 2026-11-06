"""Round 5 DOA: reference azimuth per loudspeaker (from system identification) and estimation error.

Reference: a LibriCSS loudspeaker (dry-feed channel ch) stays put across the six mini-sessions (0S..OV40) of one
session index, but NOT across session indices (checked: the same channel lands at different azimuths in different
sessions).  So the reference for (session, ch) is the circular median of the per-item system-identification azimuths (direct-path TDOAs of RIRs estimated from the dry feed), using only
items whose TDOA fit residual is < 25 us.  Its spread across sessions is reported as the reference's own error.
Estimators (on the 7-ch mixture, no oracle): SRP-PHAT blind over the segment; SRP over target-only frames
(transcript timing = oracle activity); causal running SRP per 16-ms hop. Cross-check: pyroomacoustics SRP/MUSIC.
python -m selab.doa_r5 --tag r5
"""
import argparse, json
import numpy as np, pandas as pd, soundfile as sf
from .common import MIX, RES, FS
from . import r5methods as R


def circ_median(a):
    a = np.asarray(a, float)
    best = min(a, key=lambda c: np.sum(np.abs((a - c + 180) % 360 - 180)))
    return float(best)


def ref_table(meta, thr=25.0):
    by = {}
    for m in meta:
        if m["az_fit_us"] < thr:
            by.setdefault(f'{m["session"]}_{m["ch"]}', []).append((m["az_sysid"], m["session"], m["cond"]))
    tab, rows = {}, []
    for ch, v in sorted(by.items()):
        med = circ_median([a for a, _, _ in v])
        dev = [R.angerr(a, med) for a, _, _ in v]
        tab[ch] = med
        rows.append(dict(key=ch, az_ref=med, n_items=len(v), n_recordings=len({(c, s) for _, s, c in v}),
                         median_dev=float(np.median(dev)), max_dev=float(np.max(dev)), frac_within_5=float(np.mean(np.array(dev) <= 5))))
    return tab, pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="r5"); ap.add_argument("--pra_n", type=int, default=24)
    a = ap.parse_args()
    meta = json.load(open(MIX / a.tag / "meta.json"))
    if a.tag == "r5":
        tab, ref = ref_table(meta)
        json.dump(tab, open(MIX / a.tag / "doa_ref.json", "w"), indent=1)
        (RES / "r5").mkdir(parents=True, exist_ok=True)
        ref.to_csv(RES / "r5" / "doa_reference_by_loudspeaker.csv", index=False)
        print(ref.to_string())
    else:
        tab = json.load(open(MIX / a.tag / "doa_ref.json"))
    rows = []
    for i, m in enumerate(meta):
        x, _ = sf.read(str(MIX / a.tag / m["id"] / "mix_mc.wav"), dtype="float32"); x = x.T
        X = R.mstft(x); P = R.srp_frames(X, m["mic_xy"])
        t = np.arange(P.shape[0]) * R.HOP / FS
        busy = np.zeros(len(t), bool)
        for b0, b1 in m["busy"]:
            busy |= (t >= b0 - 0.05) & (t <= b1 + 0.05)
        key = f'{m["session"]}_{m["ch"]}'
        if key not in tab:   # no reference with a good TDOA fit -> excluded from DOA-error statistics
            continue
        ref = tab[key]
        trk = R.doa_causal(P)
        r = dict(id=m["id"], cond=m["cond"], ch=m["ch"], ovl=m["ovl"], az_ref=ref, az_sysid_item=m["az_sysid"],
                 err_blind=R.angerr(R.doa_blind(P), ref), err_tonly=R.angerr(R.doa_from_frames(P, ~busy), ref),
                 err_causal_median=float(np.median([R.angerr(v, ref) for v in trk])),
                 causal_frac_within_10=float(np.mean([R.angerr(v, ref) <= 10 for v in trk])),
                 err_causal_final=R.angerr(trk[-1], ref))
        if i < a.pra_n:   # independent implementation check
            import pyroomacoustics as pra
            L = np.vstack([np.asarray(m["mic_xy"]).T])
            for name in ("SRP", "MUSIC"):
                d = pra.doa.algorithms[name](L, FS, R.NFFT, c=343.0, num_src=1, azimuth=np.deg2rad(np.arange(360)))
                d.locate_sources(X, freq_range=[200, 5000])
                r[f"err_pra_{name.lower()}"] = R.angerr(float(np.rad2deg(d.azimuth_recon[0])), ref)
        rows.append(r)
    df = pd.DataFrame(rows); df.to_csv(RES / "r5" / f"doa_{a.tag}.csv", index=False)
    print(df.groupby("cond")[[c for c in df.columns if c.startswith("err") or "frac" in c]].median().round(1).to_string())


if __name__ == "__main__":
    main()
