"""Round-6 held-out protocol (critique fix): tune on LibriCSS sessions 0-2, freeze, test on sessions 3-5.

Tuning set = every item of sessions 0-2 (72 items, 54 overlapped); test set = every item of sessions 3-5 (72, 54).
The tracker hyper-parameters were already chosen on sessions 0-2 only.  The filter grid below is scored by
Whisper word-correct on the OVERLAPPED tuning items; a config is admissible only if its mean delta on the 0S
tuning items is >= -0.02.  The best admissible config per latency class (<=5 ms, <=10 ms) is frozen
(results/r6/holdout_choice.json) and run once on the test sessions with the baselines.

python -m selab.holdout_r6 proc   [tune|test]     # processing (resumable)
python -m selab.holdout_r6 asr    [tune|test] k n # ASR shard k of n (resumable)
python -m selab.holdout_r6 select                 # -> holdout_choice.json, holdout_tune.csv
python -m selab.holdout_r6 all                    # everything, sequentially
"""
import json, subprocess, sys
import numpy as np, pandas as pd
from .common import RES, MIX
from .run_r6 import select

R6 = RES / "r6"
# (method, suffix, filter kwargs); suffix '' = the a-priori default (WNG floor 0 dB, coherence 0.5)
GRID = [("ds_td_rt", "", {}), ("sd4_rtn", "", {}),
        ("sd4_rt", "", {}), ("sd4_rt", "w-6", {"wng_db": -6.0}), ("sd4_rt", "w6", {"wng_db": 6.0}),
        ("gm4_rt", "", {}), ("gm4_rt", "w6", {"wng_db": 6.0}), ("gm4_rt", "c03", {"coh_thr": 0.3}),
        ("rtf4_rt", "", {}), ("rtf4_rt", "w6", {"wng_db": 6.0}),
        # added after the panel diagnosis (tracker errors concentrate at the start / at turn changes); their
        # parameters (1 s ramp, cosine 0.15) were set a priori, not tuned
        ("sd8_rt", "", {}), ("sd8_rt", "r1000", {"ramp_ms": 1000.0}), ("sd4_rt", "r1000", {"ramp_ms": 1000.0}),
        ("sd8_rt", "v15m", {"verify": 0.15, "fallback": "mic0"}), ("sd4_rt", "v15m", {"verify": 0.15, "fallback": "mic0"})]
BASE = ["noisy", "ds_est"]


def name(m, s):
    return m + (f"__{s}" if s else "")


def sh(cmd):
    print("+", cmd, flush=True); subprocess.run(cmd, shell=True, check=False)


def proc(split):
    items = "s012" if split == "tune" else "s345"
    py = sys.executable
    base_fill(items)
    if split == "tune":
        for m, s, kw in GRID:
            sh(f"{py} -m selab.run_r6 --tag r5 --items {items} --methods {m} --suffix '{s}' --fkw '{json.dumps(kw)}'")
    else:
        ch = json.load(open(R6 / "holdout_choice.json"))
        for c in ch["frozen"]:
            sh(f"{py} -m selab.run_r6 --tag r5 --items {items} --methods {c['method']} --suffix '{c['suffix']}' --fkw '{json.dumps(c['fkw'])}'")
            # the matching 8-ms (<=10 ms class) and reference-direction versions with the same parameters
        for extra in ch.get("extras", []):
            sh(f"{py} -m selab.run_r6 --tag r5 --items {items} --methods {extra['method']} --suffix '{extra['suffix']}' --fkw '{json.dumps(extra['fkw'])}'")


def base_fill(items):
    """round-5 baselines (unprocessed mic 0, round-5 delay-and-sum) on the items they were not yet run on;
    same code path as run_r5 but without touching round-5 runtime records."""
    import soundfile as sf
    from .common import OUT, save
    from . import r5methods as R
    M = R.get_methods()
    for b in BASE:
        for m in select(json.load(open(MIX / "r5" / "meta.json")), items):
            o = OUT / "r5" / b / f"{m['id']}.wav"
            if o.exists():
                continue
            x, _ = sf.read(str(MIX / "r5" / m["id"] / "mix_mc.wav"), dtype="float32"); x = x.T
            save(o, np.nan_to_num(M[b](x, m["mic_xy"], {}))[: x.shape[1]])


def methods_for(split):
    if split == "tune":
        return BASE + [name(m, s) for m, s, _ in GRID]
    ch = json.load(open(R6 / "holdout_choice.json"))
    ms = BASE + ["ds_td_rt"] + [name(c["method"], c["suffix"]) for c in ch["frozen"] + ch.get("extras", [])]
    return list(dict.fromkeys(ms))   # de-duplicate (ds_td_rt is also a frozen pick) so it is not transcribed twice


def asr(split, k=0, n=1):
    items = "s012" if split == "tune" else "s345"
    sh(f"{sys.executable} -m selab.score_r6 --tag r5 --items {items} --asr --methods {','.join(methods_for(split))} --shard {k} --nshard {n}")


def select_cfg():
    from .analyze_r6 import load_wer
    w = load_wer("r5")
    meta = select(json.load(open(MIX / "r5" / "meta.json")), "s012")
    ov = [m["id"] for m in meta if m["cond"] != "0S"]; s0 = [m["id"] for m in meta if m["cond"] == "0S"]
    base = w[w.method == "noisy"].set_index("id").word_correct
    rows = []
    for m, s, kw in GRID:
        nm = name(m, s); x = w[w.method == nm].set_index("id").word_correct
        d_ov = (x.reindex(ov) - base.reindex(ov)).dropna(); d_0 = (x.reindex(s0) - base.reindex(s0)).dropna()
        rows.append(dict(method=m, suffix=s, fkw=json.dumps(kw), name=nm, n_ov=len(d_ov), d_ov=d_ov.mean(),
                         n_0s=len(d_0), d_0s=d_0.mean(), latency_ms=4.0 if ("4_" in m) else (8.0 if "8_" in m else 0.62)))
    T = pd.DataFrame(rows); T.to_csv(R6 / "holdout_tune.csv", index=False)
    print(T.to_string())
    adm = T[(T.d_0s >= -0.02) & (T.n_ov >= 50)]
    frozen, extras = [], []
    for cls, lim in (("<=5 ms", 5.0), ("<=10 ms", 10.0)):
        sub = adm[adm.latency_ms <= lim].sort_values("d_ov", ascending=False)
        if sub.empty:
            continue
        b = sub.iloc[0]
        if any(c["method"] == b.method and c["suffix"] == b.suffix for c in frozen):
            continue
        frozen.append(dict(method=b.method, suffix=b.suffix, fkw=json.loads(b.fkw), cls=cls))
    # secondary: best configuration of the STFT beamformer family (superdirective / MVDR / RTF-MVDR), per class
    for cls, lim in (("<=5 ms STFT beamformer", 5.0), ("<=10 ms STFT beamformer", 10.0)):
        sub = adm[(adm.latency_ms <= lim) & ~adm.method.str.startswith("ds_td")].sort_values("d_ov", ascending=False)
        if sub.empty:
            continue
        b = sub.iloc[0]
        if lim == 10.0:   # the 8-ms class: best 8-ms configuration
            sub8 = sub[sub.latency_ms == 8.0]
            b = sub8.iloc[0] if len(sub8) else b
        if not any(c["method"] == b.method and c["suffix"] == b.suffix for c in frozen):
            frozen.append(dict(method=b.method, suffix=b.suffix, fkw=json.loads(b.fkw), cls=cls))
    for c in list(frozen):
        f, st = c["method"].rsplit("_", 1)
        if True:   # reference-direction upper bound with the same parameters
            extras.append(dict(method=f"{f}_ref", suffix=c["suffix"], fkw=c["fkw"], cls="upper bound"))
    json.dump(dict(frozen=frozen, extras=extras, rule="per latency class (<=5 ms, <=10 ms) and, separately, within the "
                   "STFT-beamformer family: max mean d word-correct vs unprocessed on overlapped sessions 0-2 items, subject to "
                   "0S delta >= -0.02 (the <=10 ms family pick is the best 8-ms config)"), open(R6 / "holdout_choice.json", "w"), indent=1)
    print("frozen:", frozen, extras)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "proc":
        proc(sys.argv[2])
    elif cmd == "asr":
        asr(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0, int(sys.argv[4]) if len(sys.argv) > 4 else 1)
    elif cmd == "select":
        select_cfg()
    elif cmd == "all":
        proc("tune"); asr("tune"); select_cfg(); proc("test"); asr("test")
