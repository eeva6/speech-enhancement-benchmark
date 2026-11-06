"""Venture pointing-error sweep + wrong-talker fallback (Conversation Bubble), pre-registered in
venture/03_EXPERIMENTS/pointing_PREREG.md.  New file; reuses group.py / build.py / r6 without modifying them.

python -m selab.venture_ab.pointing select          -> PW/selection.json (test: sessions 3-5, tune: sessions 0-2)
python -m selab.venture_ab.pointing proc tune|test  -> PW/clips/<gid>.npz   (resumable, one clip at a time)
python -m selab.venture_ab.pointing tune            -> PW/tune_grid.csv, PW/fallback_params.json (TUNE set only)
python -m selab.venture_ab.pointing obj test        -> PW/test_obj.csv (beam + fallback objective metrics)
python -m selab.venture_ab.pointing asr test        -> PW/test_asr.csv (Whisper, resumable)
python -m selab.venture_ab.pointing report          -> PW/summary.json, figure
"""
import json, os, sys, time, glob
from pathlib import Path
import numpy as np, pandas as pd, soundfile as sf
from scipy.signal import fftconvolve

from ..common import MIX, FS
from .. import libricss as L
from .. import r5methods as R5
from .. import r6
from .build import meta_all, wait_mem, sysid_lean
from . import group as G

PW = Path(os.environ.get("VPW_OUT", "/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS/pointing_work"))
ABW = Path("/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS/ab_set_work")
ERRS = [0, 10, -10, 20, -20, 30, -30, 45, -45]
AIMS = [f"e{e:+d}" for e in ERRS] + ["wrong_group"]
FR, FH = 512, 256          # detector frames (32 ms / 16 ms)
AZG = np.arange(0, 360, 5.0)


def cmean(az):
    return float(np.rad2deg(np.angle(np.mean(np.exp(1j * np.deg2rad(np.asarray(az, float)))))) % 360)


def recs(sessions):
    M = meta_all(); r = {}
    for m in M.values():
        if m["session"] in sessions and m["cond"] in ("OV10", "OV20", "OV40"):
            r.setdefault((m["cond"], m["session"]), m)
    return r


def ovl(a, b):
    return a["ws"] < b["we"] and b["ws"] < a["we"]


def pick(sessions, seed, cap, start=()):
    dref = json.load(open(MIX / "r5" / "doa_ref.json"))
    rng = np.random.default_rng(seed); pools = {}; nc = {}
    for (cond, s), m0 in sorted(recs(sessions).items()):
        c = G.candidates(cond, s, m0, dref); nc[f"{cond}_s{s}"] = len(c)
        pools[(cond, s)] = [c[i] for i in rng.permutation(len(c))]
    chosen = list(start)
    keys = sorted(pools)
    while len(chosen) < cap:
        added = False
        for k in keys:
            if len(chosen) >= cap:
                break
            mine = [c for c in chosen if (c["cond"], c["session"]) == k]
            while pools[k]:
                c = pools[k].pop(0)
                if not any(ovl(c, m) for m in mine):
                    chosen.append(c); added = True; break
        if not added:
            break
    return chosen, nc


def select():
    PW.mkdir(parents=True, exist_ok=True)
    ab = json.load(open(ABW / "group_selection.json"))["selected"]
    test, nct = pick((3, 4, 5), 20261027, 32, start=ab)
    tune, ncu = pick((0, 1, 2), 20261028, 24)
    for c in test:
        c["set"] = "test"; c["from_ab"] = c["gid"] in {a["gid"] for a in ab}
    for c in tune:
        c["set"] = "tune"; c["from_ab"] = False
    json.dump(dict(rule="pointing_PREREG.md", n_candidates_test=nct, n_candidates_tune=ncu, test=test, tune=tune),
              open(PW / "selection.json", "w"), indent=1)
    print(len(test), len(tune), nct, ncu)


def srp_track(Y, xy):
    """causal SRP-PHAT dominant azimuth + activity per 32 ms frame (hop 16 ms) on the 7-ch mixture Y (M,n)."""
    M, n = Y.shape; f = np.fft.rfftfreq(FR, 1 / FS); band = (f >= 300) & (f <= 3500); fb = f[band]
    D = R5.steer2d(xy, AZG, fb)                       # (A,Fb,M)
    win = np.hanning(FR)
    J = (n - FR) // FH + 1; dom = np.zeros(J); en = np.zeros(J)
    for j0 in range(0, J, 200):
        js = np.arange(j0, min(J, j0 + 200))
        fr = np.stack([Y[:, j * FH:j * FH + FR] * win for j in js])      # (B,M,FR)
        X = np.fft.rfft(fr, axis=-1)[:, :, band]                         # (B,M,Fb)
        en[js] = np.sum(np.abs(X[:, 0]) ** 2, -1)
        Xp = X / (np.abs(X) + 1e-12)
        P = np.abs(np.einsum("afm,bmf->baf", D.conj(), Xp)) ** 2         # (B,A,Fb)
        dom[js] = AZG[np.argmax(P.sum(-1), 1)]
    # causal minimum-tracked noise floor (rises 0.5 dB/s), active if > floor + 6 dB
    act = np.zeros(J, bool); fl = None; rise = 10 ** (0.05 * FH / FS)
    for j in range(J):
        e = en[j] + 1e-12
        fl = e if fl is None else min(e, fl * rise)
        act[j] = e > 4.0 * fl and j > 30        # first ~0.5 s: floor not yet learned
    return dom, act, (np.arange(J) * FH + FR)      # avail sample per frame


def proc_clip(c):
    out = PW / "clips" / f"{c['gid']}.npz"
    if out.exists():
        return
    t0 = time.time(); W = 12.0
    A = np.array(c["clock"]); lag = np.polyval(A, (c["ws"] + c["we"]) / 2)
    y, x, base = L.read_win(c["rec_dir"], (c["ws"] * FS + lag) / FS - W - 1.5, (c["we"] * FS + lag) / FS + W + 1.5, margin=1.0)
    Ab = L.shift_clock(A, base); B = int(round(base * FS))
    a, b = int(c["ws"] * FS) - B, int(c["we"] * FS) - B
    lag_b = np.polyval(Ab, (a + b) / 2 / FS); ra, rb = int(a + lag_b), int(b + lag_b)
    Hh, _, sh = sysid_lean(y, x, ra / FS - W, rb / FS + W, Ab)
    h = np.fft.irfft(Hh, axis=0).astype(np.float32)
    n = rb - ra; NS = L.NS
    T = np.zeros((7, n)); I = np.zeros((7, n))
    for k in range(x.shape[1]):
        src = x[ra - sh - 2 * NS:rb - sh, k].astype(np.float64)
        if not np.any(src) or not np.any(h[:, :, k]):
            continue
        for mi in range(7):
            img = fftconvolve(src, h[:, mi, k])[2 * NS:2 * NS + n]
            (T if k in c["group_ch"] else I)[mi] += img
    yy = y[ra:rb].T.astype(np.float64); del y, x, Hh, h
    N = yy - T - I; xy = c["mic_xy"]
    dref = json.load(open(MIX / "r5" / "doa_ref.json"))
    oth_az = [dref.get(f"{c['session']}_{k}") for k in c["other_ch"]]
    oth_az = [v for v in oth_az if v is not None]
    aims = {f"e{e:+d}": (c["sector_centre"] + e) % 360 for e in ERRS}
    aims["wrong_group"] = cmean(oth_az) if oth_az else (c["sector_centre"] + 180) % 360
    sv = dict(raw_T=T[0], raw_I=I[0], raw_N=N[0])
    for k, az in aims.items():
        trk = r6.const_track(yy, az)
        for nm, comp in (("T", T), ("I", I), ("N", N)):
            sv[f"{k}_{nm}"] = r6.run_filter("sd8", comp, xy, trk)[0]
    dom, act, avail = srp_track(yy, xy)
    gm, om = G.masks(c, n)
    np.savez(out, **{k: np.asarray(v, np.float32) for k, v in sv.items()}, dom=dom, act=act, avail=avail, gm=gm, om=om,
             aims=np.array([aims[k] for k in AIMS]))
    print(c["gid"], f"{time.time() - t0:.1f}s", json.dumps({k: round(v, 1) for k, v in aims.items()}), flush=True)


def proc(which):
    sel = json.load(open(PW / "selection.json"))[which]
    (PW / "clips").mkdir(parents=True, exist_ok=True)
    for c in sel:
        try:
            wait_mem(); proc_clip(c)
        except Exception as e:
            import traceback; print("FAIL", c["gid"], repr(e), traceback.format_exc()[-1500:], flush=True)


def angd(a, b):
    return np.abs((np.asarray(a) - b + 180) % 360 - 180)


def gain_curve(dom, act, avail, aim, n, tau, theta, lo, hyst=0.15, slew_s=0.3):
    """causal fallback gain g(t) in [0,1] (1 = beam, 0 = unprocessed mic 0)."""
    J = len(dom); a = np.exp(-(FH / FS) / tau); f = 1.0; eng = False
    tgt = np.ones(J)
    inn = angd(dom, aim) <= theta
    for j in range(J):
        if act[j]:
            f = a * f + (1 - a) * float(inn[j])
        if eng and f > lo + hyst:
            eng = False
        elif (not eng) and f < lo:
            eng = True
        tgt[j] = 0.0 if eng else 1.0
    # sample-wise: target known from avail[j]; slew limited
    step = 1.0 / (slew_s * FS)
    t_samp = np.ones(n)
    for j in range(J):
        s0 = avail[j]
        if s0 >= n:
            break
        s1 = avail[j + 1] if j + 1 < J else n
        t_samp[s0:min(s1, n)] = tgt[j]
    g = np.empty(n); cur = 1.0
    # vectorised per block of constant target
    edges = np.flatnonzero(np.diff(t_samp)) + 1
    starts = np.r_[0, edges]; ends = np.r_[edges, n]
    for s, e in zip(starts, ends):
        tv = t_samp[s]; L_ = e - s
        r = cur + np.sign(tv - cur) * step * np.arange(1, L_ + 1)
        r = np.minimum(r, tv) if tv >= cur else np.maximum(r, tv)
        g[s:e] = r; cur = g[e - 1]
    return g


def db(a, b):
    return float(10 * np.log10((np.sum(a ** 2) + 1e-20) / (np.sum(b ** 2) + 1e-20)))


def clip_metrics(Z, params=None):
    """per aim: ΔB, ΔSNR for beam and (if params) fallback; also mean g."""
    both = Z["gm"] & Z["om"]; n = len(Z["raw_T"])
    rT, rI, rN = Z["raw_T"], Z["raw_I"], Z["raw_N"]
    B0 = db(rT[both], rI[both]); S0 = db(rT, rI + rN)
    out = {}
    for i, k in enumerate(AIMS):
        T, I_, N_ = Z[f"{k}_T"], Z[f"{k}_I"], Z[f"{k}_N"]
        r = dict(dB_beam=db(T[both], I_[both]) - B0, dSNR_beam=db(T, I_ + N_) - S0)
        if params is not None:
            g = gain_curve(Z["dom"], Z["act"], Z["avail"], float(Z["aims"][i]), n, **params)
            fT, fI, fN = g * T + (1 - g) * rT, g * I_ + (1 - g) * rI, g * N_ + (1 - g) * rN
            r.update(dB_fb=db(fT[both], fI[both]) - B0, dSNR_fb=db(fT, fI + fN) - S0, g_mean=float(g.mean()))
        out[k] = r
    return out


def load(gid):
    return dict(np.load(PW / "clips" / f"{gid}.npz"))


def tune():
    sel = json.load(open(PW / "selection.json"))["tune"]
    Zs = {c["gid"]: load(c["gid"]) for c in sel if (PW / "clips" / f"{c['gid']}.npz").exists()}
    rows = []
    for tau in (2.0, 4.0, 8.0):
        for theta in (30.0, 45.0, 60.0):
            for lo in (0.2, 0.3, 0.4, 0.5):
                p = dict(tau=tau, theta=theta, lo=lo)
                m = {gid: clip_metrics(Z, p) for gid, Z in Zs.items()}
                r = dict(p)
                for k in AIMS:
                    r[f"fb_{k}"] = float(np.median([m[g][k]["dB_fb"] for g in m]))
                    r[f"beam_{k}"] = float(np.median([m[g][k]["dB_beam"] for g in m]))
                r["cost_e0"] = float(np.median([m[g]["e+0"]["dB_beam"] - m[g]["e+0"]["dB_fb"] for g in m]))
                r["min_fb"] = min(r[f"fb_{k}"] for k in AIMS)
                rows.append(r); print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k in ("tau", "theta", "lo", "cost_e0", "min_fb")}), flush=True)
    d = pd.DataFrame(rows); d.to_csv(PW / "tune_grid.csv", index=False)
    ok = d[d.cost_e0 <= 1.0]
    if len(ok):
        best = ok.sort_values(["min_fb", "cost_e0"], ascending=[False, True]).iloc[0]; note = "constraint met"
    else:
        best = d.sort_values("cost_e0").iloc[0]; note = "NO config met cost<=1 dB; smallest-cost chosen"
    P = dict(tau=float(best.tau), theta=float(best.theta), lo=float(best.lo), n_tune=len(Zs), note=note,
             tune_cost_e0=float(best.cost_e0), tune_min_fb=float(best.min_fb), frozen=time.strftime("%Y-%m-%d %H:%M:%S %Z"))
    json.dump(P, open(PW / "fallback_params.json", "w"), indent=1); print("FROZEN", P)


def obj(which="test"):
    sel = json.load(open(PW / "selection.json"))[which]
    P = json.load(open(PW / "fallback_params.json")); p = dict(tau=P["tau"], theta=P["theta"], lo=P["lo"])
    rows = []
    for c in sel:
        if not (PW / "clips" / f"{c['gid']}.npz").exists():
            continue
        m = clip_metrics(load(c["gid"]), p)
        for k, r in m.items():
            rows.append(dict(gid=c["gid"], rec=f"{c['cond']}_s{c['session']}", session=c["session"], cond=c["cond"],
                             from_ab=c.get("from_ab", False), aim=k, **r))
    pd.DataFrame(rows).to_csv(PW / f"{which}_obj.csv", index=False); print(len(rows))


def asr(which="test"):
    from ..score_r5 import asr_score
    from ..common import MODELS
    from faster_whisper import WhisperModel
    LEVEL = 10 ** (-26 / 20)
    sel = json.load(open(PW / "selection.json"))[which]
    P = json.load(open(PW / "fallback_params.json")); p = dict(tau=P["tau"], theta=P["theta"], lo=P["lo"])
    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=1, num_workers=1, download_root=str(MODELS / "whisper"))
    outp = PW / f"{which}_asr.csv"
    done = set(pd.read_csv(outp)["gid"]) if outp.exists() else set()
    for c in sel:
        gid = c["gid"]
        if gid in done or not (PW / "clips" / f"{gid}.npz").exists():
            continue
        Z = load(gid); n = len(Z["raw_T"]); rows = []
        sigs = {"raw": Z["raw_T"] + Z["raw_I"] + Z["raw_N"]}
        for i, k in enumerate(AIMS):
            bm = Z[f"{k}_T"] + Z[f"{k}_I"] + Z[f"{k}_N"]
            g = gain_curve(Z["dom"], Z["act"], Z["avail"], float(Z["aims"][i]), n, **p)
            sigs[f"beam_{k}"] = bm; sigs[f"fb_{k}"] = g * bm + (1 - g) * sigs["raw"]
        for nm, x in sigs.items():
            xx = (x * LEVEL / (np.sqrt(np.mean(x ** 2)) + 1e-12)).astype(np.float32)
            segs, _ = model.transcribe(xx, language="en", beam_size=1, condition_on_previous_text=False,
                                       without_timestamps=True, vad_filter=False, temperature=0.0)
            r = asr_score(c["text"], " ".join(s.text for s in segs))
            rows.append(dict(gid=gid, rec=f"{c['cond']}_s{c['session']}", sig=nm, word_correct=r["word_correct"], wer=r["wer"]))
        pd.DataFrame(rows).to_csv(outp, mode="a", header=not outp.exists(), index=False)
        print(gid, flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"select": select, "proc": lambda: proc(a[1]), "tune": tune, "obj": lambda: obj(a[1] if len(a) > 1 else "test"),
     "asr": lambda: asr(a[1] if len(a) > 1 else "test")}[a[0]]()
