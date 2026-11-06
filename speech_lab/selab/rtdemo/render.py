"""Pre-render every demo scene with the causal streaming engine (resumable, one scene at a time).

python -m selab.rtdemo.render [scene ...]       render (skips scenes with listening/rtdemo/render/<id>/DONE)
python -m selab.rtdemo.render --verify <scene>  re-run each mode ALONE in a fresh engine (what a live stream that
                                                only computes the active mode does) and compare bit-for-bit
python -m selab.rtdemo.render --web             (re)build the web page data from the renders
Outputs
  listening/rtdemo/render/<id>/<mode>.f32.npy    engine output, float64->float32, true causal timeline (not
                                                 latency-compensated: this is what the wearer would get)
  listening/rtdemo/render/<id>/steer.json        tracker / hybrid azimuth per 16 ms step (head-relative)
  results/rtdemo/timing/<id>.json                per-block compute per mode under load (+ load average)
  listening/rtdemo/web/data/<id>/<mode>.wav      16-bit PCM copies for the browser page + scene.json
"""
import json, os, sys, time
import numpy as np
import soundfile as sf
from ..common import ROOT, FS
from .engine import load_scene, run_offline, Engine, MODE_INFO, B

REN = ROOT / "listening" / "rtdemo" / "render"
WEB = ROOT / "listening" / "rtdemo" / "web"
TIM = ROOT / "results" / "rtdemo" / "timing"
SCENES = ["sim_street", "sim_restaurant", "libricss_ov40", "easycom_s10", "easycom_s11"]


def loadavg():
    return [round(v, 2) for v in os.getloadavg()]


def stats_ms(t):
    t = np.asarray(t) * 1000
    return dict(n=int(len(t)), mean=float(t.mean()), median=float(np.median(t)), p95=float(np.percentile(t, 95)),
                p99=float(np.percentile(t, 99)), max=float(t.max()))


def render(sid):
    d = REN / sid
    if (d / "DONE").exists():
        print("done", sid); return
    d.mkdir(parents=True, exist_ok=True); TIM.mkdir(parents=True, exist_ok=True)
    meta, x, comps = load_scene(sid)
    la0 = loadavg(); t0 = time.time()
    outs, eng = run_offline(meta, x, comps)
    wall = time.time() - t0; la1 = loadavg()
    for m, y in outs.items():
        np.save(d / f"{m}.f32.npy", y.astype(np.float32))
    sl = np.array(eng.steer_log) if eng.steer_log else np.zeros((0, 4))
    json.dump(dict(t=(sl[:, 0] / FS).round(4).tolist(), trk=sl[:, 1].round(1).tolist(), hyb=sl[:, 2].round(1).tolist(),
                   hyb_conf=sl[:, 3].astype(bool).tolist() if len(sl) else []), open(d / "steer.json", "w"))
    dur = x.shape[1] / FS
    tim = dict(scene=sid, audio_s=dur, wall_s=wall, load_before=la0, load_after=la1, block_ms=1000 * B / FS,
               note="measured while the round-7 pipeline ran (2 workers, nice 0) and this job at nice 19 on 2 vCPU: "
                    "max/p99 include scheduler pre-emption, not compute",
               modes={m: dict(stats_ms(t), latency_ms=eng.latency_ms(m), rtf_mean=float(np.mean(t) / (B / FS)))
                      for m, t in eng.timing.items()},
               steer=dict(stats_ms(eng.t_steer), hop_ms=16.0, rtf_mean=float(np.mean(eng.t_steer) / 0.016)) if eng.t_steer else None,
               limiter_hits={m: l.n_hits for m, l in eng.lim.items()}, weight_table_precompute_s=eng.t_precompute)
    json.dump(tim, open(TIM / f"{sid}.json", "w"), indent=1)
    (d / "DONE").write_text(time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
    print(sid, f"wall {wall:.1f}s for {dur:.1f}s audio, load {la0}->{la1}", flush=True)


def verify(sid, modes=None):
    """each mode alone in a fresh engine vs the all-modes render: must be bit-identical."""
    meta, x, comps = load_scene(sid)
    res = {}
    for m in modes or [p.name.split(".")[0] for p in sorted((REN / sid).glob("*.f32.npy"))]:
        outs, _ = run_offline(meta, x, comps, modes=[m], precompute=False)
        ref = np.load(REN / sid / f"{m}.f32.npy")
        y = outs[m].astype(np.float32)
        res[m] = dict(bit_identical=bool(np.array_equal(y, ref)), max_abs_diff=float(np.max(np.abs(y - ref))),
                      check="mode alone, fresh engine, lazily designed weights vs all-modes render with precomputed table")
        print(sid, m, res[m], flush=True)
    p = ROOT / "results" / "rtdemo" / "verify_single_mode.json"
    allr = json.load(open(p)) if p.exists() else {}
    allr[sid] = res; json.dump(allr, open(p, "w"), indent=1)
    return res


def gated_rms_db(y, blk=0.4):
    """BS.1770-style gating (abs -70 dBFS, rel -10 dB) on 400 ms blocks, no K-weighting."""
    n = int(blk * FS); h = n // 4
    e = np.array([np.mean(y[i:i + n] ** 2) for i in range(0, len(y) - n + 1, h)]) + 1e-12
    e = e[10 * np.log10(e) > -70]
    if len(e) == 0:
        return -70.0
    e = e[10 * np.log10(e) > 10 * np.log10(e.mean()) - 10]
    return float(10 * np.log10(e.mean()))


def build_web():
    from .scenes import OUTD
    idx = []
    for sid in SCENES:
        d = REN / sid
        if not (d / "DONE").exists():
            continue
        meta = json.load(open(OUTD / sid / "scene.json"))
        tim = json.load(open(TIM / f"{sid}.json"))
        wd = WEB / "data" / sid; wd.mkdir(parents=True, exist_ok=True)
        modes = []
        for m in MODE_INFO:
            p = d / f"{m}.f32.npy"
            if not p.exists():
                continue
            y = np.load(p).astype(np.float64)
            sf.write(wd / f"{m}.wav", np.clip(y, -1, 1), FS, subtype="PCM_16")
            modes.append(dict(id=m, label=MODE_INFO[m]["label"], steer=MODE_INFO[m]["steer"],
                              latency_ms=round(tim["modes"][m]["latency_ms"], 2), level_db=round(gated_rms_db(y), 2),
                              simulated=(m == "anc_sim")))
        steer = json.load(open(d / "steer.json"))
        sc = dict(id=sid, title=meta["title"], kind=meta["kind"], licence=meta["licence"], external_ok=meta["external_ok"],
                  notes=meta.get("notes", ""), duration=meta["n"] / FS, modes=modes, steer=steer,
                  talkers=meta["talkers"], wearer_acts=meta.get("wearer_acts", []), scene_type=meta.get("scene_type"))
        json.dump(sc, open(wd / "scene.json", "w"))
        idx.append(dict(id=sid, title=meta["title"], external_ok=meta["external_ok"], kind=meta["kind"]))
    json.dump(idx, open(WEB / "data" / "index.json", "w"), indent=1)
    print("web scenes:", [i["id"] for i in idx])


def main():
    a = sys.argv[1:]
    if a and a[0] == "--verify":
        for s in a[1:] or SCENES:
            verify(s)
    elif a and a[0] == "--web":
        build_web()
    else:
        for s in a or SCENES:
            render(s)
        build_web()


if __name__ == "__main__":
    main()
