"""Round-7 compute benchmark: per-hop wall time (mean, p99) of each new front-end, single thread, frozen params.
Weights for every steering direction are precomputed first (a real-time build holds a 1-degree weight table), so
the per-hop time is the streaming cost only.  Run when the machine is idle (load average recorded per item).

python -m selab.timing_r7 [--n 12]  -> results/r7/timing_r7.csv, timing_r7_summary.csv
"""
import argparse, json, os, time
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np, pandas as pd, soundfile as sf
from .common import MIX, RES, FS
from . import bf_r7 as B, r6
from .run_r7 import items, load_frozen, DEFAULT


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=12); a = ap.parse_args()
    fz = dict(DEFAULT); fz.update(load_frozen())
    its = items("val", "sub300")[: a.n]
    rows = []
    for m in its:
        x, _ = sf.read(str(MIX / "r7" / "val" / m["id"] / "mix_mc.wav"), dtype="float32"); x = x.T[:4].astype(np.float64)
        l0 = os.getloadavg()[0]
        ts = B.track_states(x)
        rows.append(dict(id=m["id"], component="tracker_rtn_atf", hop_ms=16.0, per_hop_ms=1000 * ts["sec"].mean(),
                         p99_ms=1000 * np.quantile(ts["sec"], 0.99), load1=l0))
        doa = np.load(MIX / "r7" / "val" / m["id"] / "doa_ref.npz")
        hy, _ = B.hybrid(ts, fz["X"], fz["thr"])
        t0 = time.perf_counter(); B.hybrid(ts, fz["X"], fz["thr"]); hyb_ms = 1000 * (time.perf_counter() - t0) / len(hy)
        rows.append(dict(id=m["id"], component="hybrid_logic", hop_ms=16.0, per_hop_ms=hyb_ms, p99_ms=np.nan, load1=l0))
        steers = {"hs": B.const_steer(x.shape[1]),
                  "trk": dict(az=ts["az"], el=0 * ts["az"], avail=ts["avail"]),
                  "hyb": dict(az=hy, el=0 * hy, avail=ts["avail"]), "ref": B.ref_steer(doa)}
        for st, sv in steers.items():
            for filt in ("ds_td", "sd4", "sd8"):
                if st == "ref" and filt == "sd4":
                    continue
                fixed = (0.0, 0.0) if st == "hs" else None
                p = B.make(filt, fz["ref"], fz["wng_db"], fixed)
                for az, el in set(zip(np.round(sv["az"]).astype(int) % 360, (np.round(sv["el"] / 2) * 2).astype(int))):
                    (p.taps(az, el) if filt == "ds_td" else p.weights((int(az), int(el))))     # warm the weight table
                l0 = os.getloadavg()[0]
                _, tt, li = _run(p, x, sv)
                rows.append(dict(id=m["id"], component=f"{st}_{filt}", hop_ms=li["hop_ms"], latency_ms=li["latency_ms"],
                                 per_hop_ms=1000 * tt.mean(), p99_ms=1000 * np.quantile(tt, 0.99), load1=l0))
    d = pd.DataFrame(rows); d.to_csv(RES / "r7" / "timing_r7.csv", index=False)
    g = d.groupby("component").agg(per_hop_ms=("per_hop_ms", "mean"), p99_ms=("p99_ms", "mean"), hop_ms=("hop_ms", "first"),
                                   latency_ms=("latency_ms", "first"), load1=("load1", "mean"))
    g["cpu_fraction"] = g.per_hop_ms / g.hop_ms
    g.to_csv(RES / "r7" / "timing_r7_summary.csv"); print(g.round(4).to_string())


def _run(p, x4, steer):
    H = p.B if isinstance(p, B.DSTimeATF) else p.H
    av, AZ, EL = steer["avail"], steer["az"], steer["el"]; tt = []
    for i in range(0, x4.shape[1] - H + 1, H):
        j = np.searchsorted(av, i + H, side="right") - 1
        a, e = (float(AZ[j]), float(EL[j])) if j >= 0 else (0.0, 0.0)
        t0 = time.perf_counter(); p.hop(x4[:, i:i + H], a, e); tt.append(time.perf_counter() - t0)
    return None, np.array(tt), dict(hop_ms=1000 * H / FS, latency_ms=1000 * p.latency_samples / FS)


if __name__ == "__main__":
    main()
