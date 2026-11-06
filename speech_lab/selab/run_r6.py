"""Run round-6 low-latency front-ends (selab/r6.py) over a 2-D-array set.

python -m selab.run_r6 --tag r5 --methods ds_td_rt,sd4_ref --items sub48 [--fkw '{"wng_db":3}'] [--tkw '{...}']
       [--suffix name]
Method name = <filter>_<steer>, filter in ds_td sd4 sd8 gm4 gm8 rtf4 rtf8, steer in r5t rtn rt ref blind.
A suffix names a parameter variant (written to outputs/<tag>/<method>__<suffix>/).
Resumable: items whose wav exists are skipped.  Tracker outputs are cached per item in outputs/<tag>/r6_tracks/.
Per-item timing rows -> results/r6/runtime/<tag>_<method>_<pid>.csv
"""
import argparse, json, os, time, traceback
import numpy as np, pandas as pd, soundfile as sf
from .common import MIX, OUT, RES, load, save, FS

SESS = {"s012": {0, 1, 2}, "s345": {3, 4, 5}}


def select(meta, items):
    if items in (None, "all"):
        return meta
    if items == "sub48":
        from .score_r5 import sub48
        keep = set(sub48({m["id"]: m for m in meta}))
        return [m for m in meta if m["id"] in keep]
    if items in SESS:
        return [m for m in meta if m["session"] in SESS[items]]
    if items.startswith("sub48_"):
        s = SESS[items[6:]]
        return [m for m in select(meta, "sub48") if m["session"] in s]
    raise ValueError(items)


def get_track(tag, m, x, steer, az_ref, need_flags, tkw, tname):
    from . import r6
    from . import r5methods as R5
    if steer == "ref":
        if not need_flags:
            return r6.const_track(x, az_ref)
        steer = "reff"
    if steer == "blind":
        az = R5.doa_blind(R5.srp_frames(R5.mstft(x), m["mic_xy"]))
        return r6.const_track(x, az)
    cd = OUT / tag / "r6_tracks" / (steer + (f"__{tname}" if tname else "")); cd.mkdir(parents=True, exist_ok=True)
    cp = cd / f"{m['id']}.npz"
    if cp.exists():
        z = np.load(cp); return {k: (z[k] if z[k].ndim else z[k].item()) for k in z.files}
    if steer == "reff":
        t = r6.ref_flags(x, m["mic_xy"], az_ref, **tkw)
    else:
        t = r6.track(x, m["mic_xy"], steer, enrol=load(MIX / tag / m["id"] / "enrol.wav"), **(tkw if steer != "r5t" else {}))
    np.savez(cp, **{k: np.asarray(v) for k, v in t.items()})
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="r5"); ap.add_argument("--methods", required=True)
    ap.add_argument("--items", default="sub48"); ap.add_argument("--fkw", default="{}"); ap.add_argument("--tkw", default="{}")
    ap.add_argument("--suffix", default=""); ap.add_argument("--tname", default="", help="tracker-variant cache name")
    ap.add_argument("--shard", type=int, default=0); ap.add_argument("--nshard", type=int, default=1)
    ap.add_argument("--warm", action="store_true", help="WARM START: run over mixtures/r6ctx (2 s of preceding audio), "
                    "cut the output back to the item span; written as <method>__warm[...] under the item's own tag")
    a = ap.parse_args()
    import torch; torch.set_num_threads(1)
    from . import r6
    fkw, tkw = json.loads(a.fkw), json.loads(a.tkw)
    meta = select(json.load(open(MIX / a.tag / "meta.json")), a.items)[a.shard::a.nshard]
    dref = json.load(open(MIX / a.tag / "doa_ref.json"))
    rd = RES / "r6" / "runtime"; rd.mkdir(parents=True, exist_ok=True)
    for meth in a.methods.split(","):
        filt, steer = meth.rsplit("_", 1)
        suf = "_".join(x for x in (("warm" if a.warm else ""), a.suffix) if x)
        name = meth + (f"__{suf}" if suf else "")
        od = OUT / a.tag / name
        todo = [m for m in meta if not (od / f"{m['id']}.wav").exists()]
        rows, fails = [], []
        for m in todo:
            try:
                src = MIX / ("r6ctx" if a.warm else a.tag) / m["id"] / "mix_mc.wav"
                x, _ = sf.read(str(src), dtype="float32"); x = x.T
                c0 = int(round(2.0 * FS)) if a.warm else 0
                n_item = x.shape[1] - c0
                az_ref = dref.get(f'{m["session"]}_{m["ch"]}', m.get("az_sysid"))
                tn = "_".join(t for t in (("warm" if a.warm else ""), a.tname) if t)
                trk = get_track(a.tag, m, x, steer, az_ref, filt.startswith(("rtf", "gm")), tkw, tn)
                y, info = r6.run_filter(filt, x, m["mic_xy"], trk, **fkw)
                save(od / f"{m['id']}.wav", np.nan_to_num(y)[c0: c0 + n_item])
                rows.append(dict(method=name, tag=a.tag, id=m["id"], dur=x.shape[1] / FS, warm=a.warm, filt_sec=info["sec"],
                                 per_hop_ms=info["per_hop_ms"], hop_ms=info["hop_ms"], latency_ms=info["latency_ms"],
                                 trk_sec=float(trk.get("sec", 0)), embed_sec=float(trk.get("embed_sec", 0)),
                                 n_embed=int(trk.get("n_embed", 0)), trk_frames=int(trk.get("n_frames", 0)),
                                 rtf_good=info["rtf_good"], load1=os.getloadavg()[0]))
            except Exception as e:
                fails.append(m["id"]); print("FAIL", name, m["id"], repr(e), traceback.format_exc()[-800:], flush=True)
        if rows:
            pd.DataFrame(rows).to_csv(rd / f"{a.tag}_{name}_{os.getpid()}.csv", index=False)
        print(json.dumps(dict(method=name, tag=a.tag, n_done=len(rows), n_fail=len(fails))), flush=True)


if __name__ == "__main__":
    main()
