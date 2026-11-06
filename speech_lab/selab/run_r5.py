"""Run one round-5 method over a 2-D-array set (r5 = real LibriCSS, r5sim = its simulated twin).

python -m selab.run_r5 --method mvdr_online_est --tag r5 [--resume]
Writes outputs/<tag>/<method>/<id>.wav and results/r5/runtime_<tag>_<method>.json
"""
import argparse, json, resource, time, traceback
import numpy as np
import soundfile as sf
from .common import MIX, OUT, RES, load, save


def doa_ref_table(tag):
    p = MIX / tag / "doa_ref.json"
    return json.load(open(p)) if p.exists() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True); ap.add_argument("--tag", default="r5")
    ap.add_argument("--resume", action="store_true"); ap.add_argument("--limit", type=int)
    ap.add_argument("--items", default=None, help="'sub48' = 2 items per recording (same subset as score_r5)")
    a = ap.parse_args()
    from . import r5methods as R
    M = R.get_methods()
    meta = json.load(open(MIX / a.tag / "meta.json"))
    dref = doa_ref_table(a.tag)
    od = OUT / a.tag / a.method
    if a.resume:
        meta = [m for m in meta if not (od / f"{m['id']}.wav").exists()]
    if a.items == "sub48":
        from .score_r5 import sub48
        keep = set(sub48({m["id"]: m for m in json.load(open(MIX / a.tag / "meta.json"))}))
        meta = [m for m in meta if m["id"] in keep]
    meta = meta[: a.limit] if a.limit else meta
    times, durs, fails, infos, hop = [], [], [], {}, []
    for i, m in enumerate(meta):
        d = MIX / a.tag / m["id"]
        try:
            x, _ = sf.read(str(d / "mix_mc.wav"), dtype="float32"); x = x.T
            ctx = dict(enrol=load(d / "enrol.wav"), az_ref=dref.get(f'{m["session"]}_{m["ch"]}', m.get("az_sysid")))
            if (d / "enrol_dry.wav").exists():
                ctx["enrol_dry"] = load(d / "enrol_dry.wav")
            tp = OUT / a.tag / "tse" / f"{m['id']}.wav"
            if a.method == "mvdr_mask_tse" and tp.exists():
                ctx["tse_cached"] = load(tp)
            # chained methods: reuse the (deterministic) online-MVDR output already on disk; the runtime of the
            # cached first stage is added back from its own runtime json in the analysis, not timed here
            mp = OUT / a.tag / "mvdr_online_est" / f"{m['id']}.wav"
            if a.method in ("mvdr_online_est_dfn3", "mvdr_online_est_tse") and mp.exists():
                ctx["mvdr_cached"] = load(mp)
            t0 = time.perf_counter()
            y = M[a.method](x, m["mic_xy"], ctx)
            dt = time.perf_counter() - t0
            if i > 0:
                times.append(dt); durs.append(m["dur"])
            if ctx.get("info"):
                infos[m["id"]] = ctx["info"]
            if R.LAST:
                hop.append(dict(R.LAST)); R.LAST.clear()
            save(od / f"{m['id']}.wav", np.nan_to_num(y)[: x.shape[1]])
        except Exception as e:
            fails.append(dict(id=m["id"], err=repr(e), tb=traceback.format_exc()[-1500:]))
    if not meta:
        print(json.dumps(dict(method=a.method, n=0, note="nothing to do"))); return
    rep = dict(method=a.method, tag=a.tag, n=len(meta), n_fail=len(fails), fails=fails[:3],
               rtf=float(np.sum(times) / np.sum(durs)) if times else None,
               peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, infos=infos,
               streaming={k: float(np.mean([h[k] for h in hop])) for k in hop[0]} if hop else None,
               latency=R.LATENCY.get(a.method), cpu="2 vCPU aarch64, no GPU")
    (RES / "r5").mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(RES / "r5" / f"runtime_{a.tag}_{a.method}{'_resume' if a.resume else ''}{'_' + a.items if a.items else ''}.json", "w"), indent=1, default=float)
    print(json.dumps({k: rep[k] for k in ("method", "tag", "n", "n_fail", "rtf")}, default=float), flush=True)
    if fails:
        print("FAIL", fails[0]["tb"])


if __name__ == "__main__":
    main()
