"""Round 5: REAL multichannel test set from LibriCSS (Chen et al., ICASSP 2020).

LibriSpeech test-clean utterances were replayed through 8 loudspeakers (fixed positions) in a real meeting
room and recorded with a 7-mic circular array (mic 0 = centre, mics 1-6 on a 4.25 cm radius circle).
`clean/each_spk.wav` holds the 8 DRY loudspeaker feeds (one channel per loudspeaker), on the playback clock.

Per test item (one target utterance, cut from the 10-min recording at its own time span):
  mix_mc.wav   7-channel real recording segment (the input to every method)
  mix.wav      mic 0 (centre) = unprocessed reference mic
  ref.wav      ESTIMATED reverberant image of the target at mic 0 (dry feed x estimated RIR, see below)
  enrol.wav    another utterance of the same LibriSpeech speaker, cut from the same recording at mic 0
  meta         transcript, speaker, loudspeaker channel, overlap fraction, target-only intervals, sysid DOA

System identification (used ONLY for references and the DOA check, never by a method):
  the dry feeds are aligned to the recording (playback/record clocks differ by ~10-30 ppm: offset + drift
  fitted per item by GCC-PHAT), then per frequency bin a least-squares fit y_m(f,t) = sum_k H_mk(f) X_k(f,t)
  over a +-W s window (STFT 8192/2048, i.e. 0.51 s RIRs).  From the 7-mic RIRs of the target loudspeaker the
  direct-path TDOAs give a reference azimuth that is independent of the mixture-based estimators.
"""
import json, glob, os, re
import numpy as np
import soundfile as sf
from scipy.signal import stft, istft
from .common import ROOT, MIX, FS, save

LC = ROOT / "data" / "libricss" / "for_release"
R = 0.0425
MIC_XY = np.array([[0.0, 0.0]] + [[R * np.cos(np.deg2rad(60 * i)), R * np.sin(np.deg2rad(60 * i))] for i in range(6)])
C = 343.0
NS, HS = 8192, 2048


def sessions(conds=("0S", "OV10", "OV20", "OV40"), sess=range(6)):
    out = []
    for c in conds:
        for d in sorted(glob.glob(str(LC / c / "*"))):
            s = int(re.search(r"session(\d+)", d).group(1))
            if s in sess and os.path.exists(d + "/record/raw_recording.wav") and os.path.exists(d + "/clean/each_spk.wav"):
                out.append((c, s, d))
    return out


def read_info(d):
    rows = []
    for ln in open(d + "/transcription/meeting_info.txt").read().strip().split("\n")[1:]:
        a = ln.split("\t")
        rows.append(dict(start=float(a[0]), end=float(a[1]), spk=a[2], uid=a[3], text=a[4]))
    return rows


def gcc(a, b, lo, hi):
    """lag k (fractional) maximising GCC-PHAT with a[n+k] ~ b[n], searched in [lo, hi]."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    Rr = np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)); Rr /= np.abs(Rr) + 1e-9
    c = np.fft.irfft(Rr, n)
    lags = np.arange(lo, hi + 1); v = c[lags % n]; k = int(np.argmax(v))
    if 0 < k < len(v) - 1:
        p = v[k - 1:k + 2]; den = p[0] - 2 * p[1] + p[2]
        fr = 0.5 * (p[0] - p[2]) / den if den != 0 else 0.0
    else:
        fr = 0.0
    return lags[k] + fr, float(v[k])


def clock_fit(y0, mix):
    """Global offset/drift recording vs playback: y(n + lag(n)) ~ x(n). Robust (median of local slopes)."""
    ts = np.arange(10, len(mix) / FS - 30, 20)
    lags = np.array([gcc(y0[int(t * FS):int((t + 20) * FS)], mix[int(t * FS):int((t + 20) * FS)], -4000, 4000)[0] for t in ts])
    A = np.polyfit(ts + 10, lags, 1)
    for _ in range(3):  # iteratively drop outliers (dominant-talker distance changes the peak by up to ~190 samples)
        r = lags - np.polyval(A, ts + 10); keep = np.abs(r) < max(3 * np.median(np.abs(r)), 20)
        A = np.polyfit(ts[keep] + 10, lags[keep], 1)
    return A


def sysid(y, x, t0, t1, A):
    """LS multichannel RIR estimate over recording-time window [t0,t1] s. y (n,7) recording, x (n,8) dry.
    Returns H (F,7,8), residual ratio per mic (dB) and the integer shift used."""
    a, b = int(t0 * FS), int(t1 * FS)
    lag_c = np.polyval(A, (t0 + t1) / 2)          # recording index = playback index + lag
    sh = int(np.round(lag_c)) - 400                 # leave 400 samples (25 ms) of pre-delay room in the RIR
    xa, xb = a - sh, b - sh
    if xa < 0 or xb > len(x):
        return None
    Y = np.stack([stft(y[a:b, m], FS, nperseg=NS, noverlap=NS - HS, boundary=None, padded=False)[2] for m in range(y.shape[1])]).astype(np.complex64)
    X = np.stack([stft(x[xa:xb, k], FS, nperseg=NS, noverlap=NS - HS, boundary=None, padded=False)[2] for k in range(x.shape[1])]).astype(np.complex64)
    T = min(Y.shape[2], X.shape[2]); Y, X = Y[:, :, :T], X[:, :, :T]
    f = np.fft.rfftfreq(NS, 1 / FS)
    tc = (np.arange(T) * HS + NS / 2) / FS + t0
    dlag = np.polyval(A, tc) - lag_c                # drift inside the window (samples), corrected by phase
    X = X * np.exp(-2j * np.pi * f[None, :, None] * dlag[None, None, :] / FS)
    act = np.abs(X).sum(1) > 0                      # (8,T) active loudspeakers
    on = act.any(1)
    Hh = np.zeros((len(f), Y.shape[0], X.shape[0]), np.complex64)
    Xo = X[on]                                      # (K,F,T)
    G = np.einsum("kft,jft->fkj", Xo, Xo.conj())    # normal equations, batched over frequency
    Bm = np.einsum("kft,mft->fkm", Xo.conj(), Y)
    G = G + 1e-6 * np.trace(G, axis1=1, axis2=2).real[:, None, None] / len(Xo) * np.eye(len(Xo))
    sol = np.linalg.solve(G.conj(), Bm)             # (F,K,7): sum_k H_mk X_k  ->  (X^H X)^T ... see note
    Hh[:, :, on] = np.transpose(sol, (0, 2, 1))
    E = np.einsum("fmk,kft->mft", Hh, X)
    res = 10 * np.log10(np.sum(np.abs(Y - E) ** 2, (1, 2)) / np.sum(np.abs(Y) ** 2, (1, 2)))
    return Hh, res, sh


def direct_tdoa(h):
    """h (L,7) RIRs of one loudspeaker -> TDOA of each mic vs mic 0 (s) from the direct-path peak, x8 upsampled."""
    from scipy.signal import resample
    U = 8
    pk = int(np.argmax(np.abs(h[:, 0])))
    lo = max(pk - 64, 0); seg = h[lo:pk + 64]
    hu = resample(seg, len(seg) * U, axis=0)
    # first peak within 6 dB of the max = direct path (robust against a stronger early reflection)
    env = np.abs(hu)
    t = []
    for m in range(h.shape[1]):
        e = env[:, m]; thr = 0.5 * e.max()
        idx = np.where(e >= thr)[0][0]
        j = idx + int(np.argmax(e[idx:idx + 4 * U]))
        t.append(j)
    t = np.array(t, float) / U / FS
    return t - t[0]


def fit_az(tdoa, xy=MIC_XY):
    """far-field azimuth (deg) minimising TDOA error; returns az, rms residual (us)."""
    az = np.deg2rad(np.arange(0, 360, 0.5))
    u = np.stack([np.cos(az), np.sin(az)], 1)
    pred = -(xy @ u.T) / C; pred = pred - pred[0]            # (7,A) arrival time rel. mic 0
    err = np.sqrt(np.mean((pred - tdoa[:, None]) ** 2, 0))
    k = int(np.argmin(err))
    return float(np.rad2deg(az[k])), float(err[k] * 1e6)


def rt60_from_rir(h):
    e = np.cumsum(h[::-1] ** 2)[::-1]; e = 10 * np.log10(e / e[0] + 1e-12)
    i5, i25 = np.argmax(e < -5), np.argmax(e < -25)
    return float(3 * (i25 - i5) / FS) if i25 > i5 else float("nan")


def build(tag="r5", per_session=6, W=12.0, seed=5, min_dur=3.0, max_dur=15.0):
    out = MIX / tag; out.mkdir(parents=True, exist_ok=True)
    mp = out / "meta.json"
    meta = json.load(open(mp)) if mp.exists() else []
    done = {m["id"] for m in meta}
    rng = np.random.default_rng(seed)
    for cond, s, d in sessions():
        ids_here = [m for m in done if m.startswith(f"{cond}_s{s}_")]
        if len(ids_here) >= per_session:
            continue
        y, _ = sf.read(d + "/record/raw_recording.wav", dtype="float32")
        x, _ = sf.read(d + "/clean/each_spk.wav", dtype="float32")
        info = read_info(d)
        A = clock_fit(y[:, 0], x.sum(1))
        for u in info:   # loudspeaker channel = channel with the most energy during the utterance (playback timeline)
            seg = x[int(u["start"] * FS):int(u["end"] * FS)]
            u["ch"] = int(np.argmax((seg ** 2).sum(0)))
        for i, u in enumerate(info):
            oth = [(v["start"], v["end"]) for j, v in enumerate(info) if j != i]
            ov = sum(max(0, min(u["end"], b) - max(u["start"], a)) for a, b in oth)
            u["ovl"] = ov / (u["end"] - u["start"])
        cand = [i for i, u in enumerate(info) if min_dur <= u["end"] - u["start"] <= max_dur
                and W + 1 < u["start"] and u["end"] < len(x) / FS - W - 1
                and any(v["spk"] == u["spk"] and v["uid"] != u["uid"] for v in info)]
        if cond != "0S":
            cand = [i for i in cand if info[i]["ovl"] > 0.05]   # overlapped targets only
        pick = sorted(rng.choice(cand, size=min(per_session, len(cand)), replace=False).tolist())
        for i in pick:
            u = info[i]
            iid = f"{cond}_s{s}_{u['uid']}"
            if iid in done:
                continue
            lag = np.polyval(A, (u["start"] + u["end"]) / 2)
            # refine to the target loudspeaker: lag of its dry feed vs mic 0 (includes its propagation delay)
            a, b = int(u["start"] * FS), int(u["end"] * FS)
            ra, rb = int(a + lag), int(b + lag)
            ro = sysid(y, x, (ra / FS) - W, (rb / FS) + W, A)
            if ro is None:
                continue
            Hh, res, sh = ro
            h = np.fft.irfft(Hh[:, :, u["ch"]], axis=0)   # (L,7) target loudspeaker RIRs (shifted by sh)
            pk = int(np.argmax(np.abs(h[:, 0])))
            ra, rb = a + sh + pk, b + sh + pk                # utterance span on the recording (direct path at mic 0)
            mix_mc = y[ra:rb].T.copy()
            # reverberant target image at mic 0 = dry target feed convolved with its estimated RIR
            src = x[ra - sh - 2 * NS:rb - sh, u["ch"]]
            img = np.convolve(src, h[:, 0])[2 * NS:2 * NS + (rb - ra)]
            early = np.convolve(src, h[: pk + int(0.05 * FS), 0])[2 * NS:2 * NS + (rb - ra)]
            tdoa = direct_tdoa(h)
            az, fres = fit_az(tdoa)
            # target-only intervals relative to the segment (from the transcript timing = oracle activity)
            busy = [(max(v["start"], u["start"]) - u["start"], min(v["end"], u["end"]) - u["start"])
                    for j, v in enumerate(info) if j != i and v["end"] > u["start"] and v["start"] < u["end"]]
            # enrolment: same speaker, other utterance, least overlapped, 3-15 s, from mic 0 of the recording
            en = [v for v in info if v["spk"] == u["spk"] and v["uid"] != u["uid"]]
            en.sort(key=lambda v: (v["ovl"], -min(v["end"] - v["start"], 15)))
            e = en[0]; el = np.polyval(A, (e["start"] + e["end"]) / 2)
            ea, eb = int(e["start"] * FS + el), int(min(e["end"], e["start"] + 15) * FS + el)
            dd = out / iid; dd.mkdir(exist_ok=True)
            sf.write(dd / "mix_mc.wav", mix_mc.T, FS, subtype="FLOAT")
            save(dd / "mix.wav", mix_mc[0]); save(dd / "ref.wav", img); save(dd / "ref_early.wav", early)
            save(dd / "enrol.wav", y[ea:eb, 0])
            # interferer image (everything that is not the target, at mic 0) for SIR bookkeeping
            m = dict(id=iid, cond=cond, snr=0, session=s, uid=u["uid"], spk=u["spk"], ch=u["ch"], text=u["text"],
                     dur=(rb - ra) / FS, ovl=round(u["ovl"], 3), busy=busy, enrol_uid=e["uid"], enrol_ovl=round(e["ovl"], 3),
                     sysid_res_db=[round(float(r), 2) for r in res], az_sysid=az, az_fit_us=round(fres, 2),
                     rt60_sysid=rt60_from_rir(h[pk:, 0]), direct_idx=int(pk + sh - np.round(lag)),
                     clock=[float(A[0]), float(A[1])], mic_xy=MIC_XY.tolist(),
                     sir_db=float(10 * np.log10(np.sum(img ** 2) / (np.sum((mix_mc[0] - img) ** 2) + 1e-12))))
            meta.append(m); done.add(iid)
            json.dump(meta, open(mp, "w"), indent=1)
            print(iid, f"ovl={m['ovl']:.2f} az={az:.1f} fit={fres:.1f}us res={res[0]:.1f}dB sir={m['sir_db']:.1f}", flush=True)
        del y, x
    return meta


if __name__ == "__main__":
    import sys
    build(*(sys.argv[1:2] or ["r5"]))


def read_win(d, t0, t1, margin=2.0):
    """Read only [t0-margin, t1+margin] s of the recording AND the dry feeds (same absolute sample range).
    Returns y, x, base_s; indices into y/x are absolute - base.  Keeps memory ~50 MB instead of ~600 MB."""
    base = max(int((t0 - margin) * FS), 0); end = int((t1 + margin) * FS)
    y, _ = sf.read(d + "/record/raw_recording.wav", dtype="float32", start=base, stop=end)
    x, _ = sf.read(d + "/clean/each_spk.wav", dtype="float32", start=base, stop=end)
    n = min(len(y), len(x))
    return y[:n], x[:n], base / FS


def shift_clock(A, base_s):
    """lag polynomial in window-relative seconds."""
    return np.array([A[0], A[1] + A[0] * base_s])
