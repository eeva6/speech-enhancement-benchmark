"""Round-6 tracker accuracy on every item: fraction of 16-ms tracker steps within 10 deg of the reference azimuth,
end-of-segment error, compute.  Tracker outputs are cached (shared with run_r6).
Tracker hyper-parameters (lam_long 0.99, gate 20 deg) were chosen on sessions 0-2 only (work_r6/trk_grid*.csv).
python -m selab.trk_eval_r6 --tag r5 --modes r5t,rtn,rt  -> results/r6/tracker_<tag>.csv
"""
import argparse, json
import numpy as np, pandas as pd, soundfile as sf
from .common import MIX, RES, FS
from .run_r6 import get_track
from . import r6


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="r5"); ap.add_argument("--modes", default="r5t,rtn,rt")
    ap.add_argument("--shard", type=int, default=0); ap.add_argument("--nshard", type=int, default=1)
    ap.add_argument("--items", default="all")
    ap.add_argument("--warm", action="store_true", help="run over mixtures/r6ctx (2 s history), score item frames only")
    a = ap.parse_args()
    import torch; torch.set_num_threads(1)
    from .run_r6 import select
    meta = select(json.load(open(MIX / a.tag / "meta.json")), a.items)[a.shard::a.nshard]
    dref = json.load(open(MIX / a.tag / "doa_ref.json"))
    rows = []
    for m in meta:
        key = f'{m["session"]}_{m["ch"]}'
        if key not in dref:
            continue
        azr = dref[key]
        src = MIX / ("r6ctx" if a.warm else a.tag) / m["id"] / "mix_mc.wav"
        x, _ = sf.read(str(src), dtype="float32"); x = x.T
        c0 = 2.0 if a.warm else 0.0
        busy = m.get("busy", [])
        for mode in a.modes.split(","):
            t = get_track(a.tag, m, x, mode, azr, False, {}, "warm" if a.warm else "")
            keep = t["avail"] / FS > c0 + 1e-9      # item frames only (available after the item started)
            t = {k: (v[keep] if isinstance(v, np.ndarray) and v.shape == keep.shape else v) for k, v in t.items()}
            e = np.abs(r6.angdiff(t["az"], azr))
            tc = t["avail"] / FS - c0
            ov = np.zeros(len(tc), bool)
            for b0, b1 in busy:
                ov |= (tc >= b0) & (tc <= b1)
            rows.append(dict(id=m["id"], cond=m["cond"], session=m["session"], mode=mode, frac10=float((e <= 10).mean()),
                             frac10_overlapped_steps=float((e[ov] <= 10).mean()) if ov.any() else np.nan,
                             end_err=float(e[-1]), median_err=float(np.median(e)), trk_sec=float(t["sec"]),
                             embed_sec=float(t["embed_sec"]), n_embed=int(t["n_embed"]), n_frames=int(t["n_frames"]),
                             dur=x.shape[1] / FS - c0))
    w = ("_warm" if a.warm else "") + ("" if a.items == "all" else f"_{a.items}")
    out = RES / "r6" / (f"tracker_{a.tag}{w}.csv" if a.nshard == 1 else f"tracker_{a.tag}{w}.part{a.shard}.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    d = pd.DataFrame(rows); d["ov"] = d.cond != "0S"
    print(d.groupby(["ov", "mode"]).agg(frac10=("frac10", "mean"), end10=("end_err", lambda v: (v <= 10).mean())).round(3))


if __name__ == "__main__":
    main()
