"""Venture A/B set (Conversation Bubble): real LibriCSS 7-mic clips, before/after, with component-exact metrics.

python -m selab.venture_ab.build select          # pre-registered clip selection -> OUTW/selection.json
python -m selab.venture_ab.build proc            # per pool item: sysid components + all modes (resumable)
python -m selab.venture_ab.build asr             # Whisper word-correct, -26 dBFS normalised (resumable)

Component decomposition: the recording y (7ch) = T (target image, 7ch) + I (competing loudspeakers' images) + N
(residual = real room noise + system-ID model error).  T and I come from the same LS system identification as
round 5 (selab.libricss.sysid), recomputed per item for ALL loudspeakers.  Every mode is linear given steering /
weights computed from y (or, for the ORACLE MVDR, from the true components), so f(y) = f(T) + f(I) + f(N) exactly
and output SNR/SIR are measured on the separately filtered components ("shadow filtering").
Never modifies existing lab files; writes under OUTW only.
"""
import json, os, sys, time
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve, stft, istft

from ..common import MIX, OUT, FS
from .. import libricss as L
from .. import r5methods as R5
from .. import r6

OUTW = Path(os.environ.get("VAB_OUT", "/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS/ab_set_work"))
SEED = 20261025
MODES = ["raw", "causal_trk_sd8", "causal_ref_sd8", "r5_ds32", "oracle_mvdr", "anc_sim"]


def meta_all():
    return {m["id"]: m for m in json.load(open(MIX / "r5" / "meta.json"))}


def pool():
    M = meta_all()
    p = [m for m in M.values() if m["session"] in (3, 4, 5) and m["cond"] in ("OV10", "OV20", "OV40") and 8.0 <= m["dur"] <= 15.0]
    return sorted(p, key=lambda m: m["id"])


def select():
    p = pool(); rng = np.random.default_rng(SEED)
    recs = sorted({(m["cond"], m["session"]) for m in p})
    pick = []
    for r in recs:
        c = [m["id"] for m in p if (m["cond"], m["session"]) == r]
        pick.append(c[int(rng.integers(len(c)))])
    for cond in ("OV10", "OV20", "OV40"):
        c = [m["id"] for m in p if m["cond"] == cond and m["id"] not in pick]
        if c:
            pick.append(c[int(rng.integers(len(c)))])
    out = dict(seed=SEED, rule="see ab_set_PREREG.md", pool=[m["id"] for m in p], selected=pick)
    OUTW.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(OUTW / "selection.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
    return out


def rec_dir(m):
    import glob
    c = m["cond"]; s = m["session"]
    return [d for d in glob.glob(str(L.LC / c / "*")) if f"session{s}_" in d][0]


def sysid_lean(y, x, t0, t1, A, fchunk=512):
    """Same math as selab.libricss.sysid (LS multichannel RIRs, drift-corrected), but lower peak memory:
    frequency-chunked normal equations and no residual computation (returns res = None)."""
    NS, HS = L.NS, L.HS
    a, b = int(t0 * FS), int(t1 * FS)
    lag_c = np.polyval(A, (t0 + t1) / 2)
    sh = int(np.round(lag_c)) - 400
    xa, xb = a - sh, b - sh
    if xa < 0 or xb > len(x):
        return None
    Y = np.stack([stft(y[a:b, m], FS, nperseg=NS, noverlap=NS - HS, boundary=None, padded=False)[2].astype(np.complex64) for m in range(y.shape[1])])
    X = np.stack([stft(x[xa:xb, k], FS, nperseg=NS, noverlap=NS - HS, boundary=None, padded=False)[2].astype(np.complex64) for k in range(x.shape[1])])
    T = min(Y.shape[2], X.shape[2]); Y, X = Y[:, :, :T], X[:, :, :T]
    f = np.fft.rfftfreq(NS, 1 / FS)
    tc = (np.arange(T) * HS + NS / 2) / FS + t0
    dlag = np.polyval(A, tc) - lag_c
    Hh = np.zeros((len(f), Y.shape[0], X.shape[0]), np.complex64)
    for f0 in range(0, len(f), fchunk):
        sl = slice(f0, f0 + fchunk)
        X[:, sl, :] = X[:, sl, :] * np.exp(-2j * np.pi * f[None, sl, None] * dlag[None, None, :] / FS).astype(np.complex64)
    act = np.abs(X).sum(1) > 0
    on = act.any(1)
    X = X[on]
    for f0 in range(0, len(f), fchunk):
        sl = slice(f0, f0 + fchunk)
        Xo = X[:, sl, :]
        G = np.einsum("kft,jft->fkj", Xo, Xo.conj())
        Bm = np.einsum("kft,mft->fkm", Xo.conj(), Y[:, sl, :])
        G = G + 1e-6 * np.trace(G, axis1=1, axis2=2).real[:, None, None] / len(Xo) * np.eye(len(Xo))
        sol = np.linalg.solve(G.conj(), Bm)
        Hh[sl][:, :, on] = np.transpose(sol, (0, 2, 1))
    return Hh, None, sh


def components(m, W=12.0):
    """Recompute the round-5 system identification for item m and return (y_seg 7xn, T 7xn, I 7xn, info)."""
    d = rec_dir(m)
    info = {u["uid"]: u for u in L.read_info(d)}
    u = info[m["uid"]]
    A = np.array(m["clock"])
    lag = np.polyval(A, (u["start"] + u["end"]) / 2)
    a, b = int(u["start"] * FS), int(u["end"] * FS)
    t0 = (a + lag) / FS - W - 1.5; t1 = (b + lag) / FS + W + 1.5
    y, x, base = L.read_win(d, t0, t1, margin=1.0)
    Ab = L.shift_clock(A, base)
    B = int(round(base * FS))
    a, b = a - B, b - B
    lag_b = np.polyval(Ab, (a / FS + b / FS) / 2)
    ra, rb = int(a + lag_b), int(b + lag_b)
    Hh, res, sh = sysid_lean(y, x, ra / FS - W, rb / FS + W, Ab)
    h = np.fft.irfft(Hh, axis=0).astype(np.float32)  # (L,7,8)
    ch = m["ch"]
    pk = int(np.argmax(np.abs(h[:, 0, ch])))
    ra, rb = a + sh + pk, b + sh + pk
    n = rb - ra; NS = L.NS
    T = np.zeros((7, n)); I = np.zeros((7, n))
    for k in range(x.shape[1]):
        src = x[ra - sh - 2 * NS:rb - sh, k].astype(np.float64)
        if not np.any(src):
            continue
        for mi in range(7):
            img = fftconvolve(src, h[:, mi, k])[2 * NS:2 * NS + n]
            if k == ch:
                T[mi] = img
            else:
                I[mi] += img
    yseg = y[ra:rb].T.astype(np.float64)
    del y, x, Hh, h
    return yseg, T, I, dict(res_db=None, n=n)


def oracle_mvdr(T, I, N):
    """ORACLE: offline MVDR (32 ms STFT) with Rn from the true I+N images and the target RTF (mic-0 referenced)
    = principal eigenvector of the true target-image covariance.  Returns the weights (F,M) to apply to any signal."""
    XT = R5.mstft(T); XV = R5.mstft(I + N)
    Rt = np.einsum("mft,nft->fmn", XT, XT.conj()) / XT.shape[2]
    Rv = np.einsum("mft,nft->fmn", XV, XV.conj()) / XV.shape[2]
    M = T.shape[0]
    tr = np.real(np.trace(Rv, axis1=1, axis2=2))[:, None, None]
    Rv = Rv + 1e-3 * tr / M * np.eye(M)
    ev, U = np.linalg.eigh(Rt)
    hvec = U[:, :, -1]; hvec = hvec / (hvec[:, :1] + 1e-12)
    a = np.linalg.solve(Rv, hvec[..., None])[..., 0]
    return a / (np.einsum("fm,fm->f", hvec.conj(), a)[:, None] + 1e-12)


def apply_stft_w(w, x):
    X = R5.mstft(x)
    return R5.mistft(np.einsum("fm,mft->ft", w.conj(), X), x.shape[1]).astype(np.float64)


def anc_filters():
    from ..rtdemo import anc_sim
    f, c = anc_sim.filters()
    return f, c


def proc_item(m, anc):
    od = OUTW / "items" / m["id"]
    if (od / "done.json").exists():
        return
    od.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    yseg, T, I, info = components(m)
    x_r5, _ = sf.read(str(MIX / "r5" / m["id"] / "mix_mc.wav"), dtype="float64"); x_r5 = x_r5.T
    n = min(yseg.shape[1], x_r5.shape[1])
    seg_err = float(np.max(np.abs(yseg[:, :n] - x_r5[:, :n])))
    ref_r5, _ = sf.read(str(MIX / "r5" / m["id"] / "ref.wav"), dtype="float64")
    nn = min(len(ref_r5), T.shape[1])
    ref_corr = float(np.corrcoef(ref_r5[:nn], T[0, :nn])[0, 1])
    y = x_r5[:, :n]; T = T[:, :n]; I = I[:, :n]; N = y - T - I
    xy = m["mic_xy"]
    dref = json.load(open(MIX / "r5" / "doa_ref.json"))
    az_ref = dref.get(f'{m["session"]}_{m["ch"]}', m.get("az_sysid"))
    comps = dict(mix=y, T=T, I=I, N=N)
    outs = {}
    # A0 raw
    outs["raw"] = {k: v[0].copy() for k, v in comps.items()}
    # A1 causal tracker sd8 (cached round-6 'rt' track computed from the mixture; filter weights depend only on steering)
    z = np.load(OUT / "r5" / "r6_tracks" / "rt" / f"{m['id']}.npz")
    trk = {k: (z[k] if z[k].ndim else z[k].item()) for k in z.files}
    outs["causal_trk_sd8"] = {k: r6.run_filter("sd8", v, xy, trk)[0].astype(np.float64) for k, v in comps.items()}
    # A2 causal sd8, ORACLE direction
    ctr = r6.const_track(y, az_ref)
    outs["causal_ref_sd8"] = {k: r6.run_filter("sd8", v, xy, ctr)[0].astype(np.float64) for k, v in comps.items()}
    # A3 R5 DS 32 ms, blind whole-utterance direction from the mixture
    az_b = R5.doa_blind(R5.srp_frames(R5.mstft(y), xy))
    D = R5.steer2d(xy, az_b, np.fft.rfftfreq(R5.NFFT, 1 / FS)) / len(xy)
    outs["r5_ds32"] = {k: apply_stft_w(D, v) for k, v in comps.items()}
    # A4 ORACLE MVDR
    w = oracle_mvdr(T, I, N)
    outs["oracle_mvdr"] = {k: apply_stft_w(w, v) for k, v in comps.items()}
    # C SIMULATED ANC at the ear (mic 0 stands in for the ear's direct sound)
    from scipy.signal import lfilter
    hc, hb = anc["companion"], anc["babble"]
    a_T = lfilter(hc, 1, T[0]); a_I = lfilter(hb, 1, I[0]); a_N = lfilter(hb, 1, N[0])
    outs["anc_sim"] = dict(mix=a_T + a_I + a_N, T=a_T, I=a_I, N=a_N)
    for mode, d in outs.items():
        np.savez_compressed(od / f"{mode}.npz", **{k: v.astype(np.float32) for k, v in d.items()})
        # exactness of the decomposition (linearity check)
        d["lin_err_db"] = float(10 * np.log10(np.sum((d["mix"] - d["T"] - d["I"] - d["N"]) ** 2) / np.sum(d["mix"] ** 2) + 1e-30))
    meta_out = dict(id=m["id"], seg_err=seg_err, ref_corr=ref_corr, sysid_res_db=info["res_db"], az_ref=az_ref,
                    az_blind=az_b, n=n, sec=time.time() - t_start,
                    lin_err_db={k: v["lin_err_db"] for k, v in outs.items()})
    json.dump(meta_out, open(od / "done.json", "w"), indent=1)
    print(json.dumps(meta_out), flush=True)


def mem_avail_mb():
    for ln in open("/proc/meminfo"):
        if ln.startswith("MemAvailable"):
            return int(ln.split()[1]) / 1024
    return 1e9


def wait_mem(need=450, maxwait=5400):
    t = 0
    while mem_avail_mb() < need and t < maxwait:
        time.sleep(15); t += 15


def proc():
    sel = json.load(open(OUTW / "selection.json"))
    M = meta_all()
    anc, _ = anc_filters()
    order = sel["selected"] + [i for i in sel["pool"] if i not in sel["selected"]]
    for iid in order:
        try:
            wait_mem()
            proc_item(M[iid], anc)
        except Exception as e:
            import traceback
            print("FAIL", iid, repr(e), traceback.format_exc()[-1500:], flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"select": select, "proc": proc}[cmd]()
