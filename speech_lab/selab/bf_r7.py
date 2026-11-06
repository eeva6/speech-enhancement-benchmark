"""Round 7 phase 2: ATF-steered causal low-latency front-ends for the EasyCom glasses (frame mics ch1-4).

Steering vectors come from the measured Device_ATFs.h5 (selab/ec_r7.load_atf; 16 kHz, 512-point grid).
Interpolation: the ATF divided by its free-field phase (README mic positions) is smooth over direction; that
residual is interpolated bilinearly in (el, az) on the 17 x 60 measurement grid and the free-field phase is put back.
Relative transfer functions d = h / h[ref] (ref = reference mic, tuned on val) make every filter distortionless
with respect to the target at the reference mic, so all outputs are aligned to the reference mic.

FILTERS (all causal; algorithmic latency as in round 6):
  ds_td  time-domain delay-and-sum: per-mic fractional delays from the ATF (GCC peak of h_m h_ref^* over
         200-6000 Hz, 1/32-sample grid), 21-tap Kaiser sinc, 2 ms blocks, crossfade on steering changes.
         Latency = BULK (8) + max relative arrival delay over the grid (samples).
  sd4/sd8 superdirective MVDR with ATF steering and DIFFUSE coherence computed from the ATF sphere
         (sum over the 1020 measured directions with sin(theta) weights, normalised), white-noise-gain floor by
         per-bin diagonal-loading bisection (round-6 code), sqrt-Hann WOLA 4/2 ms or 8/4 ms (latency 4 / 8 ms).
  r5ds   round-5 reference baseline: delay-and-sum (matched filter of the ATF RTF) on a 32 ms / 16 ms STFT,
         direction = whole-utterance blind SRP-PHAT argmax over the ATF el=0 grid (non-causal steering).

STEERING (one direction per tracker frame, 16 ms hop, or per 50 ms pose frame for REF):
  hs     head-steered: az 0, el 0 in the head frame (fixed).
  trk    round-6 tracker (track+hyst, rtn) with ATF steering (selab.onset_r7.make_tracker('atf')), from item start.
  hyb    head-prior hybrid: the same tracker state, restricted to tracks within +-X deg of az 0; the in-window
         track with the largest decayed dominance count is locked (hysteresis 1.3); when no in-window track has a
         count >= thr the steering falls back to az 0.  Computed causally from the per-frame track states.
  ref    oracle: pose-derived reference DOA (az, el) of the target talker, per 50 ms frame (not deployable).
"""
import time
import numpy as np
from .common import FS
from . import ec_r7 as E
from . import r6

NF = 512
_ATF = {}


def angd(a, b):
    return (np.asarray(a) - np.asarray(b) + 180) % 360 - 180


def ff_phase(az, el, f):
    u = E.unit(np.asarray(az, float), np.asarray(el, float))             # (...,3)
    tau = -(u @ E.MIC_POS.T) / E.C                                       # (...,M)
    return np.exp(-2j * np.pi * f[..., None] * tau[..., None, :]) if np.ndim(az) == 0 else \
        np.exp(-2j * np.pi * f[None, :, None] * tau[:, None, :])


class ATF:
    """Measured ATF of frame mics ch1-4 at 16 kHz (512-point grid) with interpolation."""

    def __init__(self):
        azg, elg, H = E.load_atf(nfft=NF)                                # (D,), (D,), (D,257,4)
        self.f = np.fft.rfftfreq(NF, 1 / FS)
        els = np.unique(np.round(elg, 6))[::-1]                            # descending el (Theta ascending)
        self.els = els[::-1]                                               # ascending el
        self.azs = np.arange(0, 360, 6.0)
        A, Ee = len(self.azs), len(self.els)
        self.H = np.zeros((Ee, A, len(self.f), 4), complex)
        for i in range(len(azg)):
            ie = int(np.argmin(np.abs(self.els - elg[i]))); ia = int(round((azg[i] % 360) / 6)) % 60
            self.H[ie, ia] = H[i]
        ffp = np.zeros_like(self.H)
        for ie, e in enumerate(self.els):
            ffp[ie] = ff_phase(self.azs, np.full(A, e), self.f)
        self.Rres = self.H / ffp                                           # smooth residual
        self.Hraw = H; self.azg, self.elg = azg, elg
        self._cache = {}

    def h(self, az, el):
        """interpolated absolute ATF (257,4)."""
        az = float(az) % 360; el = float(np.clip(el, self.els[0], self.els[-1]))
        ia = az / 6.0; i0 = int(np.floor(ia)) % 60; i1 = (i0 + 1) % 60; wa = ia - np.floor(ia)
        ie = int(np.clip(np.searchsorted(self.els, el) - 1, 0, len(self.els) - 2)); we = (el - self.els[ie]) / (self.els[ie + 1] - self.els[ie])
        R = ((1 - we) * ((1 - wa) * self.Rres[ie, i0] + wa * self.Rres[ie, i1]) +
             we * ((1 - wa) * self.Rres[ie + 1, i0] + wa * self.Rres[ie + 1, i1]))
        return R * ff_phase(az, el, self.f)

    def rtf(self, az, el, ref, nfft):
        """relative TF d = h / h[ref] on the bins of an nfft-point FFT (nfft divides 512). (F,4)."""
        key = (int(round(az)) % 360, int(round(el / 2.0)) * 2, ref, nfft)
        if key not in self._cache:
            h = self.h(key[0], key[1])[:: NF // nfft]
            self._cache[key] = h / (h[:, [ref]] + 1e-12 * (np.abs(h[:, [ref]]) == 0))
        return self._cache[key]

    def diffuse(self, nfft):
        """normalised diffuse-field coherence (F,4,4) from all measured directions, sin(theta) weights."""
        H = self.Hraw[:, :: NF // nfft]                                     # (D,F,M)
        w = np.cos(np.radians(self.elg))                                    # sin(theta)
        G = np.einsum("d,dfm,dfn->fmn", w, H, H.conj())
        dg = np.sqrt(np.real(np.einsum("fmm->fm", G)))
        return G / (dg[:, :, None] * dg[:, None, :] + 1e-20)

    def delays(self, az, el, ref):
        """relative arrival delay (samples) of each mic vs ref from the GCC peak of the RTF, 200-6000 Hz."""
        key = ("tau", int(round(az)) % 360, int(round(el / 2.0)) * 2, ref)
        if key not in self._cache:
            d = self.rtf(key[1], key[2], ref, NF); k = (self.f >= 200) & (self.f <= 6000)
            lags = np.arange(-24, 24, 1 / 32.0)
            P = d[k] / (np.abs(d[k]) + 1e-12)                               # (Fk,M), phase of h_m/h_ref
            # d_m = exp(-j 2 pi f tau_m) for a pure delay tau_m: maximise Re sum P exp(+j 2 pi f lag)
            S = np.real(np.exp(2j * np.pi * np.outer(lags, self.f[k]) / FS) @ P)   # (L,M)
            self._cache[key] = lags[np.argmax(S, 0)]
        return self._cache[key]


def atf():
    if "a" not in _ATF:
        _ATF["a"] = ATF()
    return _ATF["a"]


# ------------------------------------------------------------------------------------------------ filters
class DSTimeATF(r6.DSTime):
    def __init__(self, ref, block=32, fixed=None):
        self.M = 4; self.B = block; self.ref = ref; self.A = atf()
        self.hist = np.zeros((self.M, self.L - 1)); self.h = None
        if fixed is not None:      # fixed steering (head-steered): latency set by that direction only
            self.tmax = float(max(self.A.delays(fixed[0], fixed[1], ref).max(), 0))
        else:                      # steerable: worst case over the grid, + margin for off-plane directions
            allt = np.array([self.A.delays(a, 0, ref) for a in range(0, 360, 6)])
            self.tmax = float(max(allt.max(), 0)) + 2.0
        self.latency_samples = self.BULK + self.tmax
        self.cache = {}

    def taps(self, az, el=0.0):
        key = (int(round(az)) % 360, int(round(el / 2.0)) * 2)
        if key not in self.cache:
            tau = np.clip(self.A.delays(key[0], key[1], self.ref), -self.tmax, self.tmax)
            dl = self.BULK + self.tmax - tau
            self.cache[key] = np.stack([r6.frac_delay_taps(x, self.L) for x in dl]) / self.M
        return self.cache[key]

    def hop(self, xh, az, el):
        h_new = self.taps(az, el)
        buf = np.concatenate([self.hist, xh], 1)
        filt = lambda h: sum(np.convolve(buf[m], h[m], mode="valid") for m in range(self.M))
        if self.h is None or h_new is self.h:
            y = filt(h_new)
        else:
            r = np.linspace(0, 1, self.B, endpoint=False)
            y = (1 - r) * filt(self.h) + r * filt(h_new)
        self.h = h_new; self.hist = buf[:, -(self.L - 1):]
        return y


class SDATF:
    """superdirective MVDR (ATF steering, ATF diffuse coherence, WNG floor), sqrt-Hann WOLA, latency N."""

    def __init__(self, win_ms, ref, wng_db=0.0):
        self.A = atf(); self.M = 4; self.ref = ref
        self.N = int(win_ms * FS / 1000); self.H = self.N // 2
        self.win = np.sqrt(np.hanning(self.N + 1)[:-1])
        self.F = self.N // 2 + 1; self.wng = 10 ** (wng_db / 10)
        self.G = self.A.diffuse(self.N)
        self.inbuf = np.zeros((self.M, self.N)); self.outbuf = np.zeros(self.N)
        self.key = None; self.W = None; self.cache = {}
        self.latency_samples = self.N

    def weights(self, key):
        if key in self.cache:
            return self.cache[key]
        d = self.A.rtf(key[0], key[1], self.ref, self.N)                # (F,M), d[ref] = 1
        I = np.eye(self.M); lo = np.full(self.F, 1e-6); hi = np.full(self.F, 1e3)

        def w_of(mu):
            a = np.linalg.solve(self.G + mu[:, None, None] * I, d[..., None])[..., 0]
            return a / np.einsum("fm,fm->f", d.conj(), a)[:, None]
        for _ in range(40):
            mid = np.sqrt(lo * hi); w = w_of(mid)
            ok = np.abs(np.einsum("fm,fm->f", w.conj(), d)) ** 2 / np.sum(np.abs(w) ** 2, 1) >= self.wng
            hi = np.where(ok, mid, hi); lo = np.where(ok, lo, mid)
        w = w_of(hi)
        self.cache[key] = w
        return w

    def hop(self, xh, az, el):
        key = (int(round(az)) % 360, int(round(el / 2.0)) * 2)
        if key != self.key:
            self.W = self.weights(key); self.key = key
        self.inbuf = np.concatenate([self.inbuf[:, self.H:], xh], 1)
        Y = np.fft.rfft(self.inbuf * self.win, axis=1).T
        S = np.einsum("fm,fm->f", self.W.conj(), Y)
        y = np.fft.irfft(S, self.N) * self.win
        self.outbuf = np.concatenate([self.outbuf[self.H:], np.zeros(self.H)]) + y
        return self.outbuf[: self.H].copy()


def make(filt, ref, wng_db=0.0, fixed=None):
    if filt == "ds_td":
        return DSTimeATF(ref, fixed=fixed)
    return SDATF(int(filt[2:]), ref, wng_db)


def run(filt, x4, steer, ref, wng_db=0.0):
    """x4 (4,n) frame mics; steer = dict(az, el, avail) (latest available steering used per hop).
    Returns output aligned to the reference mic (latency compensated) and per-hop timings (s)."""
    fixed = (float(steer["az"][0]), float(steer["el"][0])) if len(steer["az"]) == 1 else None
    p = make(filt, ref, wng_db, fixed)
    H = p.B if isinstance(p, DSTimeATF) else p.H
    n = x4.shape[1]; lat = p.latency_samples
    pad = np.concatenate([x4, np.zeros((4, int(np.ceil(lat)) + 2 * H))], 1)
    av, AZ, EL = steer["avail"], steer["az"], steer["el"]
    out, tt = [], []
    for i in range(0, pad.shape[1] - H + 1, H):
        j = np.searchsorted(av, i + H, side="right") - 1
        a, e = (float(AZ[j]), float(EL[j])) if j >= 0 else (0.0, 0.0)
        t0 = time.perf_counter(); out.append(p.hop(pad[:, i:i + H], a, e)); tt.append(time.perf_counter() - t0)
    y = np.concatenate(out)
    sh = int(round(lat)) if isinstance(p, DSTimeATF) else p.N - p.H
    return y[sh: sh + n].astype(np.float32), np.array(tt), dict(hop_ms=1000 * H / FS, latency_ms=1000 * lat / FS)


def r5ds(x4, ref, span):
    """round-5 DS: 32 ms STFT, blind whole-utterance SRP-PHAT over the ATF el=0 grid; matched-filter weights."""
    from . import r5methods as R
    A = atf(); X = R.mstft(x4)                                            # (M,F,T), 512 / 256
    f = np.fft.rfftfreq(512, 1 / FS); k = (f >= 200) & (f <= 5000)
    D = np.stack([A.rtf(a, 0, ref, 512) for a in range(360)])             # (A,F,M)
    Dn = D[:, k] / (np.abs(D[:, k]) + 1e-12)
    t0, t1 = span[0] // 256, X.shape[2]
    Xn = X[:, k, t0:t1] / (np.abs(X[:, k, t0:t1]) + 1e-9)
    P = np.zeros(360)
    for c in range(0, Xn.shape[2], 64):
        P += (np.abs(np.einsum("afm,mft->aft", Dn.conj(), Xn[:, :, c:c + 64])) ** 2).sum((1, 2))
    az = int(np.argmax(P)); d = D[az]
    w = d / np.sum(np.abs(d) ** 2, 1, keepdims=True)
    return R.mistft(np.einsum("fm,mft->ft", w.conj(), X), x4.shape[1]), float(az)


# ------------------------------------------------------------------------------------------------ steering
def track_states(x4, maxk=8):
    """run the round-6 rtn tracker (ATF steering) over x4; returns per frame: lock az and the track states
    (uid, az, cnt) padded to maxk, plus timing."""
    from .onset_r7 import make_tracker
    tr = make_tracker("atf")
    n = x4.shape[1]; J = (n - r6.TN) // r6.TH + 1
    az = np.zeros(J); av = np.arange(J) * r6.TH + r6.TN
    U = np.full((J, maxk), -1, int); TA = np.full((J, maxk), np.nan); TC = np.zeros((J, maxk))
    uid = 0; tt = np.zeros(J)
    for j in range(J):
        t0 = time.perf_counter()
        a, _ = tr.step(x4[:, j * r6.TH: j * r6.TH + r6.TN]); tt[j] = time.perf_counter() - t0
        az[j] = a
        for t in tr.tracks:
            if "uid" not in t:
                t["uid"] = uid; uid += 1
        for q, t in enumerate(sorted(tr.tracks, key=lambda t: -t["cnt"])[:maxk]):
            U[j, q], TA[j, q], TC[j, q] = t["uid"], t["az"], t["cnt"]
    return dict(az=az, avail=av, uid=U, taz=TA, tcnt=TC, sec=tt)


def hybrid(ts, X, thr, hyst=1.3):
    """head-prior hybrid steering from per-frame track states (causal)."""
    J = len(ts["az"]); out = np.zeros(J); lock = None; conf = np.zeros(J, bool)
    for j in range(J):
        ok = (ts["uid"][j] >= 0) & (np.abs(angd(ts["taz"][j], 0)) <= X)
        if not ok.any():
            lock = None; continue
        u, a, c = ts["uid"][j][ok], ts["taz"][j][ok], ts["tcnt"][j][ok]
        b = int(np.argmax(c))
        if lock not in list(u) or c[b] > hyst * c[list(u).index(lock)]:
            lock = int(u[b])
        q = list(u).index(lock)
        if c[q] >= thr:
            out[j] = a[q]; conf[j] = True
    return out, conf


def const_steer(n, az=0.0, el=0.0):
    return dict(az=np.array([az]), el=np.array([el]), avail=np.array([0]))


def ref_steer(doa):
    """per-50 ms reference DOA; frame k (centre t_k) is used from t_k - 25 ms on; NaN -> previous (or 0)."""
    az = np.array(doa["az"], float); el = np.array(doa["el"], float)
    for v in (az, el):
        for k in range(len(v)):
            if not np.isfinite(v[k]):
                v[k] = v[k - 1] if k else 0.0
    av = np.maximum(np.round((np.array(doa["t"]) - 0.025) * FS).astype(int), 0)
    return dict(az=az, el=el, avail=av)
