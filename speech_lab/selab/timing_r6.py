"""Round-6 compute benchmark: per-hop wall time of each streaming filter and the trackers, run single-threaded
on 8 panel items, ideally with nothing else heavy running (load average recorded).

python -m selab.timing_r6  -> results/r6/timing_r6.csv, timing_r6.json
"""
import json, os, time
import numpy as np, pandas as pd, soundfile as sf
from .common import MIX, RES, FS, load
from .run_r6 import select
from . import r6

FILTERS = ["ds_td", "sd4", "sd8", "gm4", "gm8", "rtf4", "rtf8"]


def main():
    import torch; torch.set_num_threads(1)
    os.environ["OMP_NUM_THREADS"] = "1"
    meta = [m for m in select(json.load(open(MIX / "r5" / "meta.json")), "sub48") if m["cond"] != "0S"][:8]
    dref = json.load(open(MIX / "r5" / "doa_ref.json"))
    rows = []
    for m in meta:
        x, _ = sf.read(str(MIX / "r5" / m["id"] / "mix_mc.wav"), dtype="float32"); x = x.T
        dur = x.shape[1] / FS
        az = dref.get(f'{m["session"]}_{m["ch"]}', m["az_sysid"])
        trks = {}
        for mode in ("r5t", "rtn", "rt"):
            l0 = os.getloadavg()[0]
            t = r6.track(x, m["mic_xy"], mode, enrol=load(MIX / "r5" / m["id"] / "enrol.wav"))
            trks[mode] = t
            rows.append(dict(id=m["id"], component=f"tracker_{mode}", dur=dur, sec=t["sec"], hops=t["n_frames"],
                             hop_ms=16.0, per_hop_ms=1000 * t["sec"] / t["n_frames"], embed_sec=t["embed_sec"],
                             n_embed=t["n_embed"], load1=l0))
        for f in FILTERS:
            l0 = os.getloadavg()[0]
            per = []
            # time each hop individually to get the tail (p99) as well as the mean
            p = r6.make_filter(f, m["mic_xy"])
            H = p.B if isinstance(p, r6.DSTime) else p.H
            trk = trks["rt"]
            for i in range(0, x.shape[1] - H + 1, H):
                j = r6.steer_at(trk, i + H)
                a = trk["az"][j] if j >= 0 else 0.0; fl = int(trk["flag"][j]) if j >= 0 else 0
                t0 = time.perf_counter(); p.process_hop(x[:, i:i + H], float(a), fl); per.append(time.perf_counter() - t0)
            per = np.array(per) * 1000
            rows.append(dict(id=m["id"], component=f, dur=dur, sec=per.sum() / 1000, hops=len(per), hop_ms=1000 * H / FS,
                             per_hop_ms=per.mean(), p99_ms=float(np.percentile(per, 99)), max_ms=float(per.max()), load1=l0))
    d = pd.DataFrame(rows); d.to_csv(RES / "r6" / "timing_r6.csv", index=False)
    g = d.groupby("component").agg(per_hop_ms=("per_hop_ms", "mean"), p99_ms=("p99_ms", "mean"), hop_ms=("hop_ms", "first"),
                                   sec=("sec", "sum"), dur=("dur", "sum"), embed_sec=("embed_sec", "sum"), load1=("load1", "mean"))
    g["rtf"] = g.sec / g.dur; g["embed_rtf"] = g.embed_sec / g.dur
    lat = {"ds_td": r6.LATENCY_MS["ds_td"], **{k: v for k, v in r6.LATENCY_MS.items() if k != "ds_td"}}
    g["algorithmic_latency_ms"] = [lat.get(c, np.nan) for c in g.index]
    g.to_csv(RES / "r6" / "timing_r6_summary.csv")
    print(g.round(4).to_string())
    json.dump(dict(cpu="2 vCPU aarch64, single thread, Python/numpy reference implementation", n_items=len(meta),
                   load_mean=float(d.load1.mean())), open(RES / "r6" / "timing_r6.json", "w"), indent=1)


if __name__ == "__main__":
    main()
