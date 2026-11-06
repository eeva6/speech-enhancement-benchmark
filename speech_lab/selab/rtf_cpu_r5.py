"""Load-robust runtime check (critique: RTFs were wall-clock on a machine at load ~10-15).

Runs each method single-threaded on a few real items and records BOTH wall-clock RTF and process-CPU RTF
(time.process_time, user+sys of this process).  CPU time is much less sensitive to other tenants than wall
time (it still inflates somewhat from cache/memory-bandwidth contention, so it remains an upper bound for an
idle core).  python -m selab.rtf_cpu_r5 [n_items]  -> results/r5/rtf_cpu_r5.json
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1"); os.environ.setdefault("MKL_NUM_THREADS", "1")
import json, sys, time
import numpy as np, soundfile as sf
from .common import MIX, RES, load


def main(n=4):
    import torch; torch.set_num_threads(1)
    from . import r5methods as R
    M = R.get_methods()
    meta = json.load(open(MIX / "r5" / "meta.json"))
    pick = [m for m in meta if m["cond"] == "OV20"][:n]
    out = {"load_before": os.getloadavg(), "threads": 1, "items": [m["id"] for m in pick], "methods": {}}
    for meth in ["ds_est", "mvdr_online_est", "mvdr_online_ref", "deepfilternet3", "tse"]:
        walls, cpus, durs = [], [], []
        for k, m in enumerate(pick):
            d = MIX / "r5" / m["id"]
            x, _ = sf.read(str(d / "mix_mc.wav"), dtype="float32"); x = x.T
            ctx = dict(enrol=load(d / "enrol.wav"), az_ref=m["az_sysid"])
            if k == 0:   # warm-up (model load, caches) not timed
                M[meth](x, m["mic_xy"], dict(ctx))
            t0, c0 = time.perf_counter(), time.process_time()
            M[meth](x, m["mic_xy"], ctx)
            walls.append(time.perf_counter() - t0); cpus.append(time.process_time() - c0); durs.append(m["dur"])
            R.LAST.clear()
        out["methods"][meth] = dict(rtf_wall=sum(walls) / sum(durs), rtf_cpu=sum(cpus) / sum(durs), audio_s=sum(durs))
        print(meth, out["methods"][meth], os.getloadavg(), flush=True)
    out["load_after"] = os.getloadavg()
    json.dump(out, open(RES / "r5" / "rtf_cpu_r5.json", "w"), indent=1)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
