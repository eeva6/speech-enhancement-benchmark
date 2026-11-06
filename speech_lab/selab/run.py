"""Run one enhancement method over a mixture set, in its own process (so peak memory is per-method).

python -m selab.run --method wiener_dd --tag r1 [--out_tag r1] [--noise_psd oracle] [--only cond1,cond2]
Writes outputs/<out_tag>/<method>/<id>.wav and results/<out_tag>/runtime_<method>.json
"""
import argparse, json, resource, time, traceback
import numpy as np
from .common import MIX, OUT, RES, FS, load, save


def registry():
    from . import classical, neural, beamform, streaming
    R = {"noisy": lambda x, **_: x.copy()}
    R.update(classical.METHODS); R.update(neural.METHODS); R.update(streaming.SC_METHODS)
    B = dict(beamform.METHODS); B.update(streaming.BF_METHODS)
    return R, B


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True)
    ap.add_argument("--tag", default="r1")
    ap.add_argument("--out_tag", default=None)
    ap.add_argument("--noise_psd", default="ms")
    ap.add_argument("--only", default=None, help="comma-separated condition filter")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--resume", action="store_true", help="skip ids whose output already exists")
    ap.add_argument("--max_per_cell", type=int, default=None, help="use only the first k utterances of each cond x SNR cell")
    a = ap.parse_args()
    out_tag = a.out_tag or a.tag
    meta = json.load(open(MIX / a.tag / "meta.json"))
    if a.only:
        keep = set(a.only.split(","))
        meta = [m for m in meta if m["cond"] in keep]
    SC, BF = registry()
    is_bf = a.method in BF
    if is_bf:
        meta = [m for m in meta if m["cond"].startswith("array")]
    meta = meta[: a.limit] if a.limit else meta
    if a.max_per_cell:
        meta = [m for m in meta if int(m["id"].rsplit("_", 1)[1]) < a.max_per_cell]
    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    times, durs, fails, infos, stream_stats = [], [], [], {}, []
    name = a.method + ("" if a.noise_psd == "ms" else f"_{a.noise_psd}noise")
    od = OUT / out_tag / name
    first_call = None
    if a.resume:
        meta = [m for m in meta if not (od / f"{m['id']}.wav").exists()]
    for i, m in enumerate(meta):
        d = MIX / a.tag / m["id"]
        try:
            x = load(d / "mix.wav")
            kw = {}
            if a.method in ("specsub", "wiener_dd", "mmse_lsa"):
                kw = dict(noise_psd=a.noise_psd, noise_sig=load(d / "noise.wav") if a.noise_psd == "oracle" else None)
            info = {}
            t0 = time.perf_counter()
            if is_bf:
                y = BF[a.method](d, m)
            else:
                y = SC[a.method](x, enrol=load(d / "enrol.wav"), ref=load(d / "ref.wav"), info=info, **kw)
            dt = time.perf_counter() - t0
            if i == 0:
                first_call = dt  # includes model load / JIT warm-up; excluded from RTF
            else:
                times.append(dt); durs.append(m["dur"])
            if info:
                infos[m["id"]] = info
            from . import streaming as _st
            if _st.LAST_STATS:
                stream_stats.append(dict(_st.LAST_STATS)); _st.LAST_STATS.clear()
            save(od / f"{m['id']}.wav", np.nan_to_num(y))
        except Exception as e:
            fails.append(dict(id=m["id"], err=repr(e), tb=traceback.format_exc()[-1500:]))
    rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    params = None
    try:
        from . import neural
        params = neural.n_params(a.method) if a.method in neural.METHODS else None
    except Exception:
        pass
    rep = dict(method=name, tag=a.tag, n=len(meta), n_fail=len(fails), fails=fails[:5],
               first_call_s=first_call, mean_proc_s=float(np.mean(times)) if times else None,
               rtf=float(np.sum(times) / np.sum(durs)) if times else None,
               peak_rss_mb=rss1 / 1024, rss_before_mb=rss0 / 1024, n_params=params,
               noise_psd=a.noise_psd, infos=infos,
               streaming=({k: float(np.mean([s[k] for s in stream_stats])) for k in stream_stats[0]} if stream_stats else None), threads=2, cpu="2 vCPU aarch64 (sandbox), no GPU")
    (RES / out_tag).mkdir(parents=True, exist_ok=True)
    suffix = name
    if len(meta) == 0:  # nothing processed on this resume pass: keep the earlier runtime record
        print(json.dumps(dict(method=name, n=0, note="all outputs already present; runtime record kept")))
        return
    json.dump(rep, open(RES / out_tag / f"runtime_{suffix}{'_resume' if a.resume else ''}.json", "w"), indent=1, default=float)
    print(json.dumps({k: rep[k] for k in ("method", "n", "n_fail", "rtf", "peak_rss_mb", "first_call_s")}, default=float))
    if fails:
        print("FAIL example:", fails[0]["tb"])


if __name__ == "__main__":
    main()
