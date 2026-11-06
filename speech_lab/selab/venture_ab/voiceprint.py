"""Voiceprint check on the group sector beam (Conversation Bubble wrong-group fix), pre-registered in
venture/03_EXPERIMENTS/voiceprint_PREREG.md.  New file; reuses pointing.py / build.py / r6 / diar.core without modifying them.

python -m selab.venture_ab.voiceprint proc tune|test  -> VW/sect/<gid>.npz  (12 fixed-sector sd8 beams of T, I, N; resumable)
python -m selab.venture_ab.voiceprint emb tune|test   -> VW/emb/<gid>.npz   (ECAPA 1 s windows / 0.25 s hop + Silero VAD; resumable)
python -m selab.venture_ab.voiceprint tune            -> VW/tune_grid.csv, VW/params.json (TUNE set only)
python -m selab.venture_ab.voiceprint obj test        -> VW/test_obj.csv, VW/test_events.csv
python -m selab.venture_ab.voiceprint asr test        -> VW/test_asr.csv (Whisper, resumable)
python -m selab.venture_ab.voiceprint report          -> VW/summary.json, VW/tables.md, ../voiceprint_check.png
"""
import json, os, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.signal import fftconvolve

from ..common import MIX, FS
from .. import libricss as L
from .. import r6
from .build import wait_mem, sysid_lean
from . import pointing as P

VEN = Path("/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS")
VW = Path(os.environ.get("VVW_OUT", str(VEN / "voiceprint_work")))
PW = P.PW
SECT = np.arange(0, 360, 30.0)
SK = [f"s{int(a):03d}" for a in SECT]
AIMS = P.AIMS
WIN, HOP, T0 = 1.0, 0.25, 1.0          # ECAPA window / decision hop / first window end (s)
XF = 0.3                                # crossfade (s)
E_PRI, E_SENS = 3.0, 5.0


def sel(which):
    return json.load(open(PW / "selection.json"))[which]


# ------------------------------------------------------------------------------------------- proc (12 sector beams)
def decompose(c):
    """identical to pointing.proc_clip's decomposition (copied, not modified)."""
    W = 12.0
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
    return yy, T, I, yy - T - I


def proc_clip(c):
    out = VW / "sect" / f"{c['gid']}.npz"
    if out.exists():
        return
    t0 = time.time()
    yy, T, I, N = decompose(c); xy = c["mic_xy"]
    sv = {}
    for k, az in zip(SK, SECT):
        trk = r6.const_track(yy, az)
        for nm, comp in (("T", T), ("I", I), ("N", N)):
            sv[f"{k}_{nm}"] = r6.run_filter("sd8", comp, xy, trk)[0]
    # reproduction check vs cached pointing e+0 beam (group image)
    Z = np.load(PW / "clips" / f"{c['gid']}.npz")
    e0 = r6.run_filter("sd8", T, xy, r6.const_track(yy, float(Z["aims"][0])))[0]
    rep = float(np.max(np.abs(e0 - Z["e+0_T"])) / (np.max(np.abs(Z["e+0_T"])) + 1e-12))
    np.savez(out, **{k: np.asarray(v, np.float32) for k, v in sv.items()}, repro_relerr=rep)
    print(c["gid"], f"{time.time() - t0:.1f}s repro_relerr={rep:.2e}", flush=True)


def proc(which):
    (VW / "sect").mkdir(parents=True, exist_ok=True)
    for c in sel(which):
        try:
            wait_mem(); proc_clip(c)
        except Exception as e:
            import traceback; print("FAIL", c["gid"], repr(e), traceback.format_exc()[-1500:], flush=True)


# ------------------------------------------------------------------------------------------- emb (ECAPA + VAD)
def paths(gid):
    Z = dict(np.load(PW / "clips" / f"{gid}.npz")); S = dict(np.load(VW / "sect" / f"{gid}.npz"))
    comp = {}
    for k in AIMS:
        comp[k] = (Z[f"{k}_T"], Z[f"{k}_I"], Z[f"{k}_N"])
    for k in SK:
        comp[k] = (S[f"{k}_T"], S[f"{k}_I"], S[f"{k}_N"])
    comp["raw"] = (Z["raw_T"], Z["raw_I"], Z["raw_N"])
    return Z, comp


def win_ends(n):
    return np.arange(T0, n / FS + 1e-9, HOP)


def emb_clip(c):
    from ..diar import core
    out = VW / "emb" / f"{c['gid']}.npz"
    if out.exists():
        return
    t0 = time.time()
    Z, comp = paths(c["gid"]); n = len(Z["raw_T"]); te = win_ends(n)
    sv = dict(te=te)
    for k in AIMS + SK:
        y = (comp[k][0] + comp[k][1] + comp[k][2]).astype(np.float32)
        p, _ = core.silero_probs(y)
        sp = (p >= 0.5).astype(float)
        # speech fraction over 32 ms chunks lying fully inside [t-1, t]
        cs = np.r_[0, np.cumsum(sp)]
        lo = np.ceil((te - WIN) * FS / 512).astype(int); hi = np.floor(te * FS / 512).astype(int)
        hi = np.minimum(hi, len(sp)); lo = np.clip(lo, 0, hi)
        sv[f"{k}_vad"] = (cs[hi] - cs[lo]) / np.maximum(hi - lo, 1)
        first = T0 if k == "e+0" else E_PRI        # enrolment needs e+0 from 1.0 s; decisions start at E >= 3 s
        idx = np.flatnonzero(te >= first - 1e-9)
        wins = np.stack([te[idx] - WIN, te[idx]], 1)
        Em = np.full((len(te), 192), np.nan, np.float32)
        Em[idx] = core.embed_windows(y, wins)
        sv[f"{k}_emb"] = Em
    np.savez(out, **sv)
    print(c["gid"], f"{time.time() - t0:.1f}s", flush=True)


def emb(which):
    (VW / "emb").mkdir(parents=True, exist_ok=True)
    for c in sel(which):
        if not (VW / "sect" / f"{c['gid']}.npz").exists():
            print("NO_SECT", c["gid"], flush=True); continue
        try:
            wait_mem(); emb_clip(c)
        except Exception as e:
            import traceback; print("FAIL", c["gid"], repr(e), traceback.format_exc()[-1500:], flush=True)


# ------------------------------------------------------------------------------------------- decision simulation
def enrol(Em, E):
    te = Em["te"]; k = np.flatnonzero((te >= T0 - 1e-9) & (te <= E + 1e-9) & (Em["e+0_vad"] >= 0.5))
    if len(k) == 0:
        return None
    X = Em["e+0_emb"][k]
    cen = X.mean(0); cen /= np.linalg.norm(cen) + 1e-9
    return X, cen


def score(Em, path, j, enr, mode):
    v = Em[f"{path}_emb"][j]
    if np.any(np.isnan(v)):
        return np.nan
    X, cen = enr
    return float(v @ cen) if mode == "centroid" else float(np.max(X @ v))


def simulate(Em, aim, method, prm, E, n):
    """returns events [(t, target_path)], detect_t (first c>=K), and n_actions. Output path starts at `aim`."""
    enr = enrol(Em, E)
    ev = []; det = None
    if enr is None:
        return ev, det, "no_enrol"
    te = Em["te"]; thr, K, mode = prm["thr"], int(prm["K"]), prm["score"]
    cur = aim; c = 0; reverted = False; crel = 0
    for j in np.flatnonzero(te >= E - 1e-9):
        t = float(te[j])
        if method == "reaim":
            if Em[f"{cur}_vad"][j] < 0.5:
                continue
            s = score(Em, cur, j, enr, mode)
            if s < thr:
                c += 1
            else:
                c = 0
            if c >= K:
                if det is None:
                    det = t
                ss = np.array([score(Em, k, j, enr, mode) for k in SK])
                b = int(np.nanargmax(ss)); kb = SK[b]
                if kb != cur and ss[b] >= thr and ss[b] - s >= prm["margin"]:
                    ev.append((t, kb)); cur = kb; c = 0
        else:  # revert: always judge the condition beam path
            if Em[f"{aim}_vad"][j] < 0.5:
                continue
            s = score(Em, aim, j, enr, mode)
            if not reverted:
                c = c + 1 if s < thr else 0
                if c >= K:
                    if det is None:
                        det = t
                    ev.append((t, "raw")); reverted = True; c = 0; crel = 0
            else:
                crel = crel + 1 if s >= thr + 0.10 else 0
                if crel >= K:
                    ev.append((t, aim)); reverted = False; crel = 0
    return ev, det, "ok"


def weights(ev, aim, n):
    """path -> weight array (n,), 300 ms linear crossfades starting at each event time."""
    keys = [aim] + [p for _, p in ev if p != aim]
    W = {k: np.zeros(n) for k in dict.fromkeys(keys)}
    W[aim][:] = 1.0
    L_ = int(XF * FS)
    for t, q in ev:
        s = min(int(round(t * FS)), n)
        if s >= n:
            break
        r = np.minimum(np.arange(1, n - s + 1) / L_, 1.0)
        for k in W:
            W[k][s:] = W[k][s] * (1 - r) + (r if k == q else 0.0)
    return W


def mix_out(W, comp):
    T = sum(W[k] * comp[k][0] for k in W); I = sum(W[k] * comp[k][1] for k in W); N = sum(W[k] * comp[k][2] for k in W)
    return T, I, N


def dbm(T, I, N, Z, both, E):
    rT, rI, rN = Z["raw_T"], Z["raw_I"], Z["raw_N"]
    B0 = P.db(rT[both], rI[both]); S0 = P.db(rT, rI + rN)
    r = dict(dB=P.db(T[both], I[both]) - B0, dSNR=P.db(T, I + N) - S0)
    post = both.copy(); post[:int(E * FS)] = False
    r["dB_post"] = (P.db(T[post], I[post]) - P.db(rT[post], rI[post])) if post.sum() >= 0.3 * FS else np.nan
    return r


def recovery(ev, method, gc, E, end_t):
    """time from E until the output is fully on a sector within 20 deg of group centre (reaim) / raw (revert)."""
    for t, q in ev:
        if method == "revert" and q == "raw":
            return t + XF - E
        if method == "reaim" and q.startswith("s") and P.angd(float(q[1:]), gc) <= 20:
            return t + XF - E
    return np.inf


def clip_eval(c, prm_by_method, E=E_PRI, aims=AIMS, Zc=None):
    Z, comp = Zc if Zc is not None else paths(c["gid"])
    Em = dict(np.load(VW / "emb" / f"{c['gid']}.npz"))
    n = len(Z["raw_T"]); both = Z["gm"] & Z["om"]; rows = []
    for i, k in enumerate(aims):
        plain = dbm(*comp[k], Z, both, E)
        for method, prm in prm_by_method.items():
            ev, det, st = simulate(Em, k, method, prm, E, n)
            W = weights(ev, k, n); m = dbm(*mix_out(W, comp), Z, both, E)
            rows.append(dict(gid=c["gid"], rec=f"{c['cond']}_s{c['session']}", session=c["session"], aim=k, method=method,
                             dB_plain=plain["dB"], dSNR_plain=plain["dSNR"], dB_post_plain=plain["dB_post"],
                             dB=m["dB"], dSNR=m["dSNR"], dB_post=m["dB_post"], n_actions=len(ev), status=st,
                             detect_s=(det - E) if det is not None else np.inf,
                             recover_s=recovery(ev, method, c["sector_centre"], E, n / FS),
                             events=json.dumps([(round(t, 2), q) for t, q in ev])))
    return rows


# ------------------------------------------------------------------------------------------- tune / obj
def grid(method):
    out = []
    for thr in (0.2, 0.3, 0.4, 0.5):
        for K in (2, 4, 6):
            for sc in ("centroid", "max"):
                for mg in ((0.05, 0.10, 0.15) if method == "reaim" else (None,)):
                    out.append(dict(thr=thr, K=K, score=sc, margin=mg))
    return out


def tune():
    cl = [c for c in sel("tune") if (VW / "emb" / f"{c['gid']}.npz").exists()]
    cache = {c["gid"]: paths(c["gid"]) for c in cl}
    T3 = ["e+0", "e+20", "e-20", "wrong_group"]
    allrows = []; best = {}
    for method in ("reaim", "revert"):
        rows = []
        for prm in grid(method):
            R = pd.DataFrame(sum([clip_eval(c, {method: prm}, aims=T3, Zc=cache[c["gid"]]) for c in cl], []))
            R["cost"] = R.dB_plain - R.dB
            r = dict(method=method, **prm, n_tune=len(cl))
            r["eng_e0"] = int((R[R.aim == "e+0"].n_actions > 0).sum())
            r["eng_sum"] = int((R[R.aim.isin(["e+0", "e+20", "e-20"])].n_actions > 0).sum())
            for k in ("e+0", "e+20", "e-20"):
                r[f"cost_{k}"] = float(R[R.aim == k].cost.median())
            r["wg_dB"] = float(R[R.aim == "wrong_group"].dB.median())
            r["wg_rec_med"] = float(R[R.aim == "wrong_group"].recover_s.median())
            rows.append(r); print(json.dumps(r), flush=True)
        d = pd.DataFrame(rows); allrows.append(d)
        ok = d[(d.eng_e0 <= 1) & (d[["cost_e+0", "cost_e+20", "cost_e-20"]].max(1) <= 0.5)]
        mg = d.margin.fillna(0)
        d["_mg"] = mg
        if len(ok):
            ok = d.loc[ok.index]
            b = ok.sort_values(["wg_dB", "eng_sum", "K", "_mg", "thr"], ascending=[False, True, False, False, False]).iloc[0]
            note = "constraints met"
        else:
            b = d.sort_values(["eng_e0", "wg_dB"], ascending=[True, False]).iloc[0]; note = "NO config met constraints; fewest e0 engagements chosen"
        best[method] = dict(thr=float(b.thr), K=int(b.K), score=b.score, margin=(None if pd.isna(b.margin) else float(b.margin)),
                            note=note, tune=dict(eng_e0=int(b.eng_e0), cost_e0=float(b["cost_e+0"]), cost_p20=float(b["cost_e+20"]),
                                                 cost_m20=float(b["cost_e-20"]), wg_dB=float(b.wg_dB), wg_rec_med=float(b.wg_rec_med)))
    pd.concat(allrows).drop(columns=["_mg"], errors="ignore").to_csv(VW / "tune_grid.csv", index=False)
    best["n_tune"] = len(cl); best["E"] = E_PRI; best["frozen"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    json.dump(best, open(VW / "params.json", "w"), indent=1); print("FROZEN", json.dumps(best), flush=True)


def load_params():
    p = json.load(open(VW / "params.json"))
    return {m: dict(thr=p[m]["thr"], K=p[m]["K"], score=p[m]["score"], margin=p[m]["margin"]) for m in ("reaim", "revert")}


def obj(which="test"):
    prm = load_params(); rows = []
    for E, tag in ((E_PRI, ""), (E_SENS, "_E5")):
        rr = []
        for c in sel(which):
            if (VW / "emb" / f"{c['gid']}.npz").exists():
                rr += clip_eval(c, prm, E=E)
        pd.DataFrame(rr).to_csv(VW / f"{which}_obj{tag}.csv", index=False); print(tag, len(rr), flush=True)


def asr(which="test"):
    from ..score_r5 import asr_score
    from ..common import MODELS
    from faster_whisper import WhisperModel
    LEVEL = 10 ** (-26 / 20); prm = load_params()
    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=1, num_workers=1, download_root=str(MODELS / "whisper"))
    outp = VW / f"{which}_asr.csv"
    done = set(pd.read_csv(outp)["gid"]) if outp.exists() else set()
    for c in sel(which):
        gid = c["gid"]
        if gid in done or not (VW / "emb" / f"{gid}.npz").exists():
            continue
        Z, comp = paths(gid); Em = dict(np.load(VW / "emb" / f"{gid}.npz")); n = len(Z["raw_T"]); rows = []
        for k in ("e+0", "e+20", "e-20", "wrong_group"):
            for method, p in prm.items():
                ev, _, _ = simulate(Em, k, method, p, E_PRI, n)
                x = sum(mix_out(weights(ev, k, n), comp))
                xx = (x * LEVEL / (np.sqrt(np.mean(x ** 2)) + 1e-12)).astype(np.float32)
                segs, _ = model.transcribe(xx, language="en", beam_size=1, condition_on_previous_text=False,
                                           without_timestamps=True, vad_filter=False, temperature=0.0)
                r = asr_score(c["text"], " ".join(s.text for s in segs))
                rows.append(dict(gid=gid, rec=f"{c['cond']}_s{c['session']}", sig=f"vp_{method}_{k}", n_actions=len(ev),
                                 word_correct=r["word_correct"], wer=r["wer"]))
        pd.DataFrame(rows).to_csv(outp, mode="a", header=not outp.exists(), index=False)
        print(gid, flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"proc": lambda: proc(a[1]), "emb": lambda: emb(a[1]), "tune": tune,
     "obj": lambda: obj(a[1] if len(a) > 1 else "test"), "asr": lambda: asr(a[1] if len(a) > 1 else "test")}[a[0]]()
