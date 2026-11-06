"""Isolated per-block compute benchmark of the streaming engine.

For each array type (scene) and each mode: a fresh engine running ONLY that mode (plus the tracker for trk/hyb),
1 s warm-up, then N consecutive real blocks (looping the scene), each timed with perf_counter_ns, GC disabled.
Also times the all-modes engine (what the live path runs so that switching is instant) and the tracker step.
Writes results/rtdemo/bench_<tag>.json and appends rows to results/rtdemo/latency_compute.csv.

python -m selab.rtdemo.bench [--n 5000] [--tag isolated]
"""
import argparse, gc, json, os, time, subprocess
import numpy as np
from ..common import ROOT, FS
from .engine import Engine, load_scene, B, MODE_INFO

OUT = ROOT / "results" / "rtdemo"
SC = {"easycom": "easycom_s10", "libricss7": "libricss_ov40", "lin4": "sim_restaurant"}


def r7_alive():
    try:
        pid = int(open(ROOT / "results" / "r7" / "pids" / "pipeline.pid").read().strip())
        os.kill(pid, 0); return True
    except Exception:
        return False


def st(t):
    t = np.asarray(t, float) / 1e6
    return dict(n=int(len(t)), mean=float(t.mean()), median=float(np.median(t)), p95=float(np.percentile(t, 95)),
                p99=float(np.percentile(t, 99)), max=float(t.max()))


def run_one(meta, x, comps, modes, n, warm=FS // B):
    eng = Engine(meta, modes)
    T = x.shape[1] // B
    tb, ts = [], []
    gc.disable()
    try:
        for k in range(warm + n):
            i = (k % T) * B
            xb = x[:, i:i + B]; cb = None if comps is None else {q: v[i:i + B] for q, v in comps.items()}
            t0 = time.perf_counter_ns()
            if eng.steer is not None:
                up = eng.steer.push(xb)
            t1 = time.perf_counter_ns()
            for m in eng.modes:
                eng._one(m, xb, cb) if hasattr(eng, "_one") else None
            t2 = time.perf_counter_ns()
            if k >= warm:
                tb.append(t2 - t1)
                if eng.steer is not None and up:
                    ts.append(t1 - t0)
    finally:
        gc.enable()
    return eng, tb, ts


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=5000); ap.add_argument("--tag", default="isolated")
    a = ap.parse_args()
    res = dict(tag=a.tag, n_blocks=a.n, block_ms=1000 * B / FS, load_before=list(os.getloadavg()), r7_pipeline_running=r7_alive(),
               started_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), nproc=os.cpu_count(),
               nice=os.nice(0), omp_threads=os.environ.get("OMP_NUM_THREADS"), arrays={})
    try:
        res["cpu"] = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    rows = []
    for arr, sid in SC.items():
        meta, x, comps = load_scene(sid)
        allm = Engine(meta, ["raw"]).modes if False else None
        modes = ["raw", "hs_ds", "hs_sd4", "trk_sd4", "hyb_sd4", "anc_sim"] + (["ear"] if arr == "easycom" else [])
        R = {}
        for m in modes:
            eng, tb, ts = run_one(meta, x, comps, [m], a.n)
            R[m] = dict(block=st(tb), latency_ms=eng.latency_ms(m), rtf_mean=float(np.mean(tb) / 1e9 / (B / FS)),
                        rtf_p95=float(np.percentile(tb, 95) / 1e9 / (B / FS)))
            if ts:
                R[m]["tracker_step"] = st(ts); R[m]["tracker_rtf_mean"] = float(np.mean(ts) / 1e9 / 0.016)
            print(arr, m, {k: round(v, 4) for k, v in R[m]["block"].items() if k != "n"}, flush=True)
        eng, tb, ts = run_one(meta, x, comps, None, a.n)
        R["ALL_MODES"] = dict(block=st(tb), modes=eng.modes, rtf_mean=float(np.mean(tb) / 1e9 / (B / FS)),
                              tracker_step=st(ts), tracker_rtf_mean=float(np.mean(ts) / 1e9 / 0.016),
                              total_rtf_mean=float((np.sum(tb) + np.sum(ts)) / 1e9 / (len(tb) * B / FS)))
        print(arr, "ALL", R["ALL_MODES"]["block"], "trk", R["ALL_MODES"]["tracker_step"], flush=True)
        res["arrays"][arr] = dict(scene=sid, modes=R)
    res["load_after"] = list(os.getloadavg()); res["r7_pipeline_running_after"] = r7_alive()
    json.dump(res, open(OUT / f"bench_{a.tag}.json", "w"), indent=1)
    print("wrote", OUT / f"bench_{a.tag}.json")


if __name__ == "__main__":
    main()
