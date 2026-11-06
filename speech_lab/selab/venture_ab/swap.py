"""User-driven wrong-group recovery ("tap-to-swap"), simulated user. Pre-registered in
venture/03_EXPERIMENTS/swap_PREREG.md.  New file; reuses pointing / voiceprint caches without modifying any existing file.

python -m selab.venture_ab.swap feat tune|test   -> SW/feat/<gid>.npz  (raw mic0 Silero VAD + 12-sector 32 ms frame energies; resumable)
python -m selab.venture_ab.swap tune             -> SW/tune_grid.csv, SW/params.json (TUNE set only; P2 W,h)
python -m selab.venture_ab.swap obj test         -> SW/test_obj.csv (per replicate rows)
python -m selab.venture_ab.swap asr test         -> SW/test_asr.csv (Whisper, resumable)
python -m selab.venture_ab.swap ui               -> venture/04_PRODUCT/swap_ui/data.json + wav clips (light)
"""
import json, os, sys, time
from pathlib import Path
import numpy as np, pandas as pd

from ..common import FS
from . import pointing as P

VEN = Path("/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture")
EXP = VEN / "03_EXPERIMENTS"
SW = Path(os.environ.get("VSW_OUT", str(EXP / "swap_work")))
PW = EXP / "pointing_work"
VW = EXP / "voiceprint_work"
SECT = np.arange(0, 360, 30.0)
SK = [f"s{int(a):03d}" for a in SECT]
RING6 = [f"s{int(a):03d}" for a in range(0, 360, 60)]
XF = 0.1                 # crossfade (s)
FRM = 512                # 32 ms frames
REACH = 30.0             # deg
NREP = 20
SEED0 = 20261027
T_ACC = 4.0


def sel(which):
    return json.load(open(PW / "selection.json"))[which]


def az_of(path, Z):
    if path == "e+0":
        return float(Z["aims"][0])
    if path == "wrong_group":
        return float(Z["aims"][-1])
    return float(path[1:])


# ------------------------------------------------------------------------------------------- features
def feat_clip(c):
    from ..diar import core
    out = SW / "feat" / f"{c['gid']}.npz"
    if out.exists():
        return
    Z = np.load(PW / "clips" / f"{c['gid']}.npz"); S = np.load(VW / "sect" / f"{c['gid']}.npz")
    raw = (Z["raw_T"] + Z["raw_I"] + Z["raw_N"]).astype(np.float32)
    p, _ = core.silero_probs(raw)
    nf = len(p); En = np.zeros((12, nf))
    for i, k in enumerate(SK):
        y = (S[f"{k}_T"] + S[f"{k}_I"] + S[f"{k}_N"]).astype(np.float64)[:nf * FRM]
        En[i] = np.sum(y.reshape(nf, FRM) ** 2, 1)
    np.savez(out, vad=p, En=En)
    print(c["gid"], nf, flush=True)


def feat(which):
    (SW / "feat").mkdir(parents=True, exist_ok=True)
    for c in sel(which):
        try:
            feat_clip(c)
        except Exception as e:
            import traceback; print("FAIL", c["gid"], repr(e), traceback.format_exc()[-1500:], flush=True)


# ------------------------------------------------------------------------------------------- data
def load(c):
    Z = dict(np.load(PW / "clips" / f"{c['gid']}.npz")); S = dict(np.load(VW / "sect" / f"{c['gid']}.npz"))
    F = dict(np.load(SW / "feat" / f"{c['gid']}.npz"))
    comp = {k: (Z[f"{k}_T"], Z[f"{k}_I"], Z[f"{k}_N"]) for k in ("raw", "e+0", "wrong_group")}
    for k in SK:
        comp[k] = (S[f"{k}_T"], S[f"{k}_I"], S[f"{k}_N"])
    return dict(c=c, Z=Z, comp=comp, F=F, n=len(Z["raw_T"]), gc=float(c["sector_centre"]))


def reached(az, gc):
    return float(P.angd(az, gc)) <= REACH


# ------------------------------------------------------------------------------------------- policies
def cw_next(az, ring):
    best, bs = None, 1e9
    for k in ring:
        step = (az - float(k[1:])) % 360
        if 5 < step < bs:
            best, bs = k, step
    return best


def p2_choose(D, t, az, W, h, rejected=()):
    F = D["F"]; v = F["vad"] >= 0.5; En = F["En"]; nf = len(v)
    hi = min(int(np.floor(t * FS / FRM)), nf)
    cand = [i for i, a in enumerate(SECT) if P.angd(a, az) > h and all(P.angd(a, r) > h for r in rejected)]
    if not cand:
        return None
    for back in (W, 6.0):
        lo = max(int(np.ceil((t - back) * FS / FRM)), 0)
        m = v[lo:hi]
        if m.sum() > 0:
            e = En[cand][:, lo:hi][:, m].sum(1)
            return SK[cand[int(np.argmax(e))]]
    return None


def nearest_sector(gc):
    return int(np.argmin(P.angd(SECT, gc)))


def p3_choose(D, rng, p):
    i = nearest_sector(D["gc"])
    if rng.random() < p:
        return SK[i]
    return SK[(i + (1 if rng.random() < 0.5 else -1)) % 12]


def choose(D, policy, t, az, prm, rng, rejected):
    if policy == "P1":
        return cw_next(az, RING6)
    if policy == "P1-12":
        return cw_next(az, SK)
    if policy in ("P2", "P2-mem", "P2-naive"):
        h = 15.0 if policy == "P2-naive" else prm["h"]
        k = p2_choose(D, t, az, prm["W"], h, rejected if policy == "P2-mem" else ())
        return k if k is not None else cw_next(az, RING6)
    if policy.startswith("P3"):
        return p3_choose(D, rng, prm["p"])
    raise ValueError(policy)


# ------------------------------------------------------------------------------------------- simulated user
def next_tap(D, d, Rk, clock):
    if clock in ("fixed", "jitter"):
        return d + Rk
    gm = D["Z"]["gm"]; s = int(round(d * FS))
    cs = np.cumsum(gm[s:]); need = Rk * FS
    j = np.searchsorted(cs, need)
    return np.inf if j >= len(cs) else (s + j + 1) / FS


def simulate(D, start, policy, prm, R, clock, rng, accidental=False):
    Z = D["Z"]; n = D["n"]; end = n / FS; gc = D["gc"]
    cur = start; az = az_of(start, Z); ev = []; rejected = []
    d = 0.0; maxt = 3
    if accidental:
        if policy.startswith("P3"):
            i = nearest_sector(gc); k = SK[(i + (1 if rng.random() < 0.5 else -1)) % 12]
        else:
            k = choose(D, policy, T_ACC, az, prm, rng, rejected)
        rejected.append(az); ev.append((T_ACC, k)); cur = k; az = float(k[1:]); d = T_ACC + XF; maxt = 2
    taps = 0; t_reach = 0.0 if reached(az, gc) else np.inf; taps_reach = 0 if reached(az, gc) else np.inf
    while taps < maxt and not reached(az, gc):
        Rk = R if clock != "jitter" else float(np.clip(R * np.exp(0.4 * rng.standard_normal()), 0.3, 10.0))
        t = next_tap(D, d, Rk, clock)
        if t >= end:
            break
        k = choose(D, policy, t, az, prm, rng, rejected)
        rejected.append(az); taps += 1
        if k != cur:
            ev.append((t, k)); cur = k; az = float(k[1:])
        d = t + XF
        if reached(az, gc):
            t_reach, taps_reach = d, taps
    return ev, taps, taps_reach, t_reach


def weights(ev, start, n):
    keys = list(dict.fromkeys([start] + [p for _, p in ev]))
    W = {k: np.zeros(n) for k in keys}; W[start][:] = 1.0; L_ = int(XF * FS)
    for t, q in ev:
        s = min(int(round(t * FS)), n)
        if s >= n:
            break
        r = np.minimum(np.arange(1, n - s + 1) / L_, 1.0)
        for k in W:
            W[k][s:] = W[k][s] * (1 - r) + (r if k == q else 0.0)
    return W


def mix(W, comp):
    return tuple(sum(W[k] * comp[k][j] for k in W) for j in range(3))


def metrics(D, T, I, N, post_from):
    Z = D["Z"]; comp = D["comp"]; rT, rI, rN = comp["raw"]; both = Z["gm"] & Z["om"]
    r = dict(dB=P.db(T[both], I[both]) - P.db(rT[both], rI[both]), dSNR=P.db(T, I + N) - P.db(rT, rI + rN))
    r["dB_post"] = r["dB_post_e0"] = np.nan; r["post_s"] = 0.0
    if post_from is not None:
        post = both.copy(); post[:int(np.ceil(post_from * FS))] = False
        r["post_s"] = post.sum() / FS
        if post.sum() >= 0.3 * FS:
            eT, eI, _ = comp["e+0"]
            b0 = P.db(rT[post], rI[post])
            r["dB_post"] = P.db(T[post], I[post]) - b0
            r["dB_post_e0"] = P.db(eT[post], eI[post]) - b0
    return r


def run_one(D, start, policy, prm, R, clock, rep, accidental=False):
    rng = np.random.default_rng(SEED0 + rep)
    ev, taps, tr, trec = simulate(D, start, policy, prm, R, clock, rng, accidental)
    T, I, N = mix(weights(ev, start, D["n"]), D["comp"])
    m = metrics(D, T, I, N, (ev[-1][0] + XF) if ev else None)
    c = D["c"]
    return dict(gid=c["gid"], rec=f"{c['cond']}_s{c['session']}", session=c["session"], start=start, policy=policy, R=R,
                clock=clock, rep=rep, accidental=accidental, n_taps=taps, taps_reach=tr, t_reach=trec,
                final_az=(float(ev[-1][1][1:]) if ev else az_of(start, D["Z"])), n_events=len(ev),
                events=json.dumps([(round(t, 2), q) for t, q in ev]), **m)


def plain(D):
    rows = {}
    for k in ("e+0", "wrong_group"):
        rows[k] = metrics(D, *D["comp"][k], None)
    return rows


# ------------------------------------------------------------------------------------------- tune
def tune():
    cl = [load(c) for c in sel("tune")]
    rows = []
    for W in (1.0, 2.0, 3.0):
        for h in (15.0, 45.0, 75.0):
            prm = dict(W=W, h=h); wg, cost, taps = [], [], []
            for D in cl:
                pl = plain(D)
                r = run_one(D, "wrong_group", "P2", prm, 2.0, "fixed", 0)
                a = run_one(D, "e+0", "P2", prm, 2.0, "fixed", 0, accidental=True)
                wg.append(r["dB"]); taps.append(r["taps_reach"]); cost.append(pl["e+0"]["dB"] - a["dB"])
            rr = dict(W=W, h=h, n_tune=len(cl), wg_dB=float(np.median(wg)), acc_cost=float(np.median(cost)),
                      taps_med=float(np.median(taps)))
            rows.append(rr); print(json.dumps(rr), flush=True)
    d = pd.DataFrame(rows); d.to_csv(SW / "tune_grid.csv", index=False)
    ok = d[d.acc_cost <= 1.0]; note = "constraint met (acc cost <= 1 dB)"
    if not len(ok):
        ok = d; note = "NO config met acc-cost constraint; ignored"
    top = ok.wg_dB.max(); tied = ok[ok.wg_dB >= top - 0.05].copy()
    tied["k"] = list(zip(tied.W != 2.0, tied.h != 45.0, tied.W))
    b = tied.sort_values("k").iloc[0]
    out = dict(W=float(b.W), h=float(b.h), note=note, tune=dict(wg_dB=float(b.wg_dB), acc_cost=float(b.acc_cost), taps_med=float(b.taps_med)),
               n_tune=len(cl), frozen=time.strftime("%Y-%m-%d %H:%M:%S %Z"))
    json.dump(out, open(SW / "params.json", "w"), indent=1); print("FROZEN", json.dumps(out), flush=True)


def load_params():
    return json.load(open(SW / "params.json"))


# ------------------------------------------------------------------------------------------- obj
POL = ["P1", "P1-12", "P2", "P2-mem", "P2-naive", "P3-0.8", "P3-0.95"]


def prm_for(pol, base):
    if pol.startswith("P3"):
        return dict(p=float(pol.split("-")[1]))
    return dict(W=base["W"], h=base["h"])


def obj(which="test"):
    base = load_params(); (SW / "obj_parts").mkdir(exist_ok=True)
    for c in sel(which):
        part = SW / "obj_parts" / f"{c['gid']}.csv"
        if part.exists():
            continue
        rows = []; prow = []
        D = load(c); pl = plain(D)
        for k, m in pl.items():
            prow.append(dict(gid=c["gid"], rec=f"{c['cond']}_s{c['session']}", session=c["session"], path=k, **m))
        for pol in POL:
            prm = prm_for(pol, base); stoch = pol.startswith("P3")
            for R in (1.0, 2.0, 4.0):
                for clock in ("fixed", "jitter", "gs"):
                    nrep = NREP if (stoch or clock == "jitter") else 1
                    for rep in range(nrep):
                        rows.append(run_one(D, "wrong_group", pol, prm, R, clock, rep))
            for rep in range(NREP if stoch else 1):
                rows.append(run_one(D, "e+0", pol, prm, 2.0, "fixed", rep, accidental=True))
        pd.DataFrame(prow).to_csv(SW / "obj_parts" / f"{c['gid']}.plain.csv", index=False)
        pd.DataFrame(rows).to_csv(part, index=False)
        print(c["gid"], len(rows), flush=True)
    ids = [c["gid"] for c in sel(which)]
    if all((SW / "obj_parts" / f"{g}.csv").exists() for g in ids):
        pd.concat([pd.read_csv(SW / "obj_parts" / f"{g}.csv") for g in ids]).to_csv(SW / f"{which}_obj.csv", index=False)
        pd.concat([pd.read_csv(SW / "obj_parts" / f"{g}.plain.csv") for g in ids]).to_csv(SW / f"{which}_plain.csv", index=False)
        print("OBJ_DONE", flush=True)


# ------------------------------------------------------------------------------------------- asr
ASR_SIGS = [("wrong_group", "P1", False), ("wrong_group", "P2", False), ("wrong_group", "P2-mem", False),
            ("wrong_group", "P3-0.8", False), ("wrong_group", "P3-0.95", False), ("e+0", "P2", True), ("e+0", "P3-0.95", True)]


def asr(which="test"):
    from ..score_r5 import asr_score
    from ..common import MODELS
    from faster_whisper import WhisperModel
    LEVEL = 10 ** (-26 / 20); base = load_params()
    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=1, num_workers=1, download_root=str(MODELS / "whisper"))
    outp = SW / f"{which}_asr.csv"
    done = set(pd.read_csv(outp)["gid"]) if outp.exists() else set()
    for c in sel(which):
        if c["gid"] in done:
            continue
        D = load(c); rows = []
        for start, pol, acc in ASR_SIGS:
            rng = np.random.default_rng(SEED0)
            ev, *_ = simulate(D, start, pol, prm_for(pol, base), 2.0, "fixed", rng, acc)
            x = sum(mix(weights(ev, start, D["n"]), D["comp"]))
            xx = (x * LEVEL / (np.sqrt(np.mean(x ** 2)) + 1e-12)).astype(np.float32)
            segs, _ = model.transcribe(xx, language="en", beam_size=1, condition_on_previous_text=False,
                                       without_timestamps=True, vad_filter=False, temperature=0.0)
            r = asr_score(c["text"], " ".join(s.text for s in segs))
            rows.append(dict(gid=c["gid"], rec=f"{c['cond']}_s{c['session']}", sig=f"{'acc' if acc else 'wg'}_{pol}",
                             word_correct=r["word_correct"], wer=r["wer"]))
        pd.DataFrame(rows).to_csv(outp, mode="a", header=not outp.exists(), index=False)
        print(c["gid"], flush=True)


# ------------------------------------------------------------------------------------------- ui data (light)
def ui(gids):
    import soundfile as sf
    base = load_params(); out = VEN / "04_PRODUCT" / "swap_ui"; (out / "audio").mkdir(parents=True, exist_ok=True)
    test = {c["gid"]: c for c in sel("test")}; data = dict(clips=[], sectors=[float(a) for a in SECT], source="LibriCSS (CC BY 4.0)")
    for gid in gids:
        c = test[gid]; D = load(c); F = D["F"]; v = F["vad"] >= 0.5
        hopf = 8   # 256 ms display frames
        nf = (len(v) // hopf) * hopf
        E = (F["En"][:, :nf] * v[:nf]).reshape(12, -1, hopf).sum(2)
        Edb = 10 * np.log10(E + 1e-9); Edb = np.clip(Edb - Edb.max() + 30, 0, 30) / 30
        def wav(name, x):
            x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
            sf.write(out / "audio" / f"{gid}_{name}.wav", x.astype(np.float32), FS, subtype="PCM_16")
            return f"audio/{gid}_{name}.wav"
        files = dict(raw=wav("raw", sum(D["comp"]["raw"])))
        for k in SK:
            files[k] = wav(k, sum(D["comp"][k]))
        files["wrong_group"] = wav("wrong_group", sum(D["comp"]["wrong_group"]))
        data["clips"].append(dict(gid=gid, group_centre=D["gc"], wrong_az=az_of("wrong_group", D["Z"]), hop_s=hopf * FRM / FS,
                                  activity=np.round(Edb, 3).tolist(), audio=files, text=c["text"], P2=dict(W=base["W"], h=base["h"]),
                                  vad=[float(x) for x in np.round(v[:nf].reshape(-1, hopf).mean(1), 3)]))
    json.dump(data, open(out / "data.json", "w"))
    print("ui data", [c["gid"] for c in data["clips"]])


if __name__ == "__main__":
    a = sys.argv[1:]
    {"feat": lambda: feat(a[1]), "tune": tune, "obj": lambda: obj(a[1] if len(a) > 1 else "test"),
     "asr": lambda: asr(a[1] if len(a) > 1 else "test"), "ui": lambda: ui(a[1:])}[a[0]]()
