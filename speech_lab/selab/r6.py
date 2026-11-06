"""Round 6: causal, low-latency multichannel front-ends for the LibriCSS 7-mic circle (and its twin).

Everything here runs frame by frame on past samples only.

STEERING (tracker; runs on 32 ms frames every 16 ms; frame j uses x[:, j*256 : j*256+512] and is available
at sample j*256+512, so it never looks ahead.  The steering it produces only selects filter weights, it adds
no delay to the audio path):
  r5t   round-5 causal tracker: argmax of a running SRP-PHAT map with forgetting 0.97 (baseline).
  rtn   track-based, hysteretic SRP-PHAT WITHOUT a speaker check: frame-dominant SRP peaks are clustered
        into up to 4 direction tracks (20 deg gate, circular EMA of the azimuth); the steered track is the one
        with the most (decayed) dominant frames, and it changes only if another track has 1.3x more.
  rt    same tracks + ENROLMENT SPEAKER CHECK: each track keeps the last 1.5 s of mic-0 audio from frames it
        dominated; every 256 ms an ECAPA-TDNN embedding of that buffer (>= 0.5 s, >= 0.25 s new) is compared
        (cosine) with the enrolment embedding; the steered track is the best-scoring one, switching only when
        it beats the current one by a margin (hysteresis).  Before any track has a score: falls back to rtn.
  ref   reference (system-identification) azimuth, constant: an ORACLE-geometry upper bound.
  blind whole-segment SRP-PHAT argmax (non-causal steering; round-5 ds_est used this).
Per frame the tracker also emits target-activity flags (target-dominant / other-dominant / inactive), which
the RTF-MVDR uses to decide when it may update its noise covariance.

FILTERS (algorithmic latency = delay from an input sample to the output sample that represents it):
  ds_td   time-domain delay-and-sum: 21-tap Kaiser-windowed-sinc fractional delays, 2 ms blocks, 2 ms
          crossfade on steering changes.  Latency 8 + r/c*fs = 9.98 samples = 0.62 ms.
  sd{4,8} superdirective MVDR (diffuse-field coherence) with a white-noise-gain floor (diagonal loading found
          by bisection per bin), sqrt-Hann WOLA STFT, window 4 ms / hop 2 ms (latency 4 ms) or 8 / 4 ms (8 ms).
  gm{4,8} adaptive MVDR, free-field steering, noise covariance updated recursively on bins whose smoothed
          spatial coherence with the steering vector is low and on frames the tracker marks not-target;
          diagonal loading + the WNG floor enforced by a closed-form blend toward delay-and-sum.
  rtf{4,8} online RTF-MVDR: Rx updated while the target is active, Rn only while it is inactive (tracker flags,
          48 ms hangover); RTF = Rn * principal generalised eigenvector of (Rx, Rn) normalised to mic 0
          (GEVD / covariance whitening), per-bin fallback to the free-field steering vector when the estimate is
          immature or inconsistent with the tracked direction; MVDR + loading + WNG floor (blend toward h/|h|^2).
"""
import time
import numpy as np
from .common import FS
from . import r5methods as R

C = 343.0
TN, TH = 512, 256            # tracker frame / hop (32 / 16 ms)
TWIN = np.sqrt(np.hanning(TN + 1)[:-1])
AZ = np.arange(360.0)


def angdiff(a, b):
    return (np.asarray(a) - np.asarray(b) + 180) % 360 - 180


def circ_ema(a, b, alpha):
    """move angle a toward b by fraction alpha."""
    return float((a + alpha * angdiff(b, a)) % 360)


# ---------------------------------------------------------------------------------------------- tracker
class Tracker:
    """Causal multi-candidate SRP-PHAT tracker (see module doc).
    Per 32 ms frame: PHAT SRP over the 30% highest-energy bins (200-5000 Hz) of mic 0, normalised to sum 1;
    a long map (forgetting lam_long) gives up to 3 candidate source directions (local maxima >= rel_min of the
    maximum, >= 25 deg apart); candidates are associated with persistent tracks (20 deg gate); a short map
    (forgetting lam_short) decides which track dominates the current frame (ratio >= dom)."""

    def __init__(self, xy, enrol=None, mode="rt", gate=20.0, max_cand=3, sep=25.0, rel_min=0.35, lam_long=0.99,
                 lam_short=0.8, top=0.3, dom=1.2, embed_every=16, buf_s=1.5, min_s=0.5, new_s=0.25, margin=0.1,
                 hyst=1.3, drop_s=1.0, act_db=3.0, refine=0.0):
        self.xy = np.asarray(xy); self.M = len(xy); self.mode = mode
        f = np.fft.rfftfreq(TN, 1 / FS); self.k = (f >= 200) & (f <= 5000)
        self.D = R.steer2d(self.xy, AZ, f)[:, self.k, :]               # (A,Fk,M)
        self.gate, self.max_cand, self.sep, self.rel_min = gate, max_cand, sep, rel_min
        self.lam_long, self.lam_short, self.top, self.dom = lam_long, lam_short, top, dom
        self.embed_every = embed_every
        self.buf_n, self.min_n, self.new_n = int(buf_s * FS), int(min_s * FS), int(new_s * FS)
        self.margin, self.hyst, self.drop = margin, hyst, int(drop_s * FS / TH)
        self.act = 10 ** (act_db / 10); self.refine = refine
        self.tracks = []; self.lock = None; self.j = 0
        self.r5acc = np.zeros(360); self.L = np.zeros(360); self.S = np.zeros(360); self.E = []
        self.enrol_e = None
        if mode == "rt":
            from . import neural
            self.embed = neural.embed
            self.enrol_e = neural.embed(enrol.astype(np.float32))
        self.t_embed = 0.0; self.n_embed = 0

    def srp(self, frame):
        X = np.fft.rfft(frame * TWIN, axis=1)[:, self.k]                  # (M,Fk)
        Xn = X / (np.abs(X) + 1e-9)
        Pfull = np.abs(np.einsum("afm,mf->a", self.D.conj(), Xn)) ** 2   # round-5 style (all bins)
        e = np.abs(X[0]); keep = e >= np.quantile(e, 1 - self.top)
        P = np.abs(np.einsum("afm,mf->a", self.D[:, keep].conj(), Xn[:, keep])) ** 2
        return Pfull, P / (P.sum() + 1e-30), float(np.mean(frame[0, -TH:] ** 2))

    def candidates(self):
        Lm = self.L; mx = Lm.max()
        loc = np.where((Lm >= np.roll(Lm, 1)) & (Lm >= np.roll(Lm, -1)) & (Lm >= self.rel_min * mx))[0]
        loc = loc[np.argsort(-Lm[loc])]
        out = []
        for a in loc:
            if all(abs(angdiff(a, b)) >= self.sep for b in out):
                out.append(float(a))
            if len(out) == self.max_cand:
                break
        return out

    def step(self, frame):
        """frame (M,TN) = the newest 32 ms. Returns (steer_az, flag): 1 target-dominant, 2 other-dominant,
        3 active but ambiguous, 0 inactive."""
        Pfull, P, E = self.srp(frame)
        self.r5acc = 0.97 * self.r5acc + Pfull
        if self.mode == "r5t":
            self.j += 1
            return float(AZ[np.argmax(self.r5acc)]), 1
        self.L = self.lam_long * self.L + P; self.S = self.lam_short * self.S + (1 - self.lam_short) * P
        self.E = (self.E + [E])[-int(1.5 * FS / TH):]
        active = E > self.act * min(self.E) if len(self.E) > 8 else True
        # associate candidates with tracks
        for a in self.candidates():
            dists = [abs(angdiff(t["az"], a)) for t in self.tracks]
            if dists and min(dists) <= self.gate:
                t = self.tracks[int(np.argmin(dists))]; t["seen"] = self.j
                if not self.refine:
                    t["az"] = a
            else:
                self.tracks.append(dict(az=a, seen=self.j, cnt=0.0, buf=np.zeros(0, np.float32), new=0, score=None))
        keep = [i for i, t in enumerate(self.tracks) if self.j - t["seen"] <= self.drop or i == self.lock]
        if self.lock is not None:
            self.lock = keep.index(self.lock)
        self.tracks = [self.tracks[i] for i in keep]
        # which track dominates this frame (short map at the track azimuth, +-3 deg)
        flag, k = (3 if active else 0), None
        for t in self.tracks:
            t["cnt"] *= 0.99
        if active and self.tracks:
            v = np.array([max(self.S[(int(t["az"]) + o) % 360] for o in range(-3, 4)) for t in self.tracks])
            o = np.argsort(-v); k0 = int(o[0])
            if len(v) == 1 or v[o[0]] >= self.dom * v[o[1]]:
                k = k0; t = self.tracks[k]; t["cnt"] += 1.0
                if self.refine:   # refine the track azimuth from frames it dominates (short-map local peak)
                    loc = [(int(t["az"]) + o) % 360 for o in range(-int(self.gate), int(self.gate) + 1)]
                    t["az"] = circ_ema(t["az"], float(loc[int(np.argmax(self.S[loc]))]), self.refine)
                if self.mode == "rt":
                    t["buf"] = np.concatenate([t["buf"], frame[0, -TH:].astype(np.float32)])[-self.buf_n:]
                    t["new"] += TH
        # speaker check
        if self.mode == "rt" and self.j % self.embed_every == 0:
            for t in self.tracks:
                if len(t["buf"]) >= self.min_n and t["new"] >= self.new_n:
                    t0 = time.perf_counter()
                    e = self.embed(t["buf"])
                    self.t_embed += time.perf_counter() - t0; self.n_embed += 1
                    c = float((e * self.enrol_e).sum())
                    t["score"] = c if t["score"] is None else 0.5 * t["score"] + 0.5 * c
                    t["new"] = 0
        # lock decision
        if self.tracks:
            cnt = [t["cnt"] for t in self.tracks]
            scored = [i for i, t in enumerate(self.tracks) if t["score"] is not None]
            if self.mode == "rt" and scored:
                best = max(scored, key=lambda i: self.tracks[i]["score"])
                cur = self.lock
                if cur is None or self.tracks[cur]["score"] is None or \
                        self.tracks[best]["score"] > self.tracks[cur]["score"] + self.margin:
                    self.lock = best
            else:
                best = int(np.argmax(cnt))
                if self.lock is None or cnt[best] > self.hyst * cnt[self.lock]:
                    self.lock = best
        if k is not None:
            flag = 1 if k == self.lock else 2
        self.j += 1
        az = self.tracks[self.lock]["az"] if self.lock is not None else float(AZ[np.argmax(self.r5acc)])
        sc = self.tracks[self.lock]["score"] if self.lock is not None else None
        self.last_score = np.nan if sc is None else float(sc)
        return az, flag


def track(x, xy, mode, enrol=None, **kw):
    """Run the tracker over x (M,n). Returns dict(az, flag, avail) per tracker frame (avail = sample index at
    which the frame's output becomes available) plus timing."""
    tr = Tracker(xy, enrol, mode=mode, **kw)
    n = x.shape[1]; az, fl, av, sc = [], [], [], []
    t0 = time.perf_counter()
    for j in range(0, (n - TN) // TH + 1):
        a, f = tr.step(x[:, j * TH: j * TH + TN]); az.append(a); fl.append(f); av.append(j * TH + TN)
        sc.append(getattr(tr, "last_score", np.nan))
    dt = time.perf_counter() - t0
    return dict(az=np.array(az), flag=np.array(fl), avail=np.array(av), score=np.array(sc), sec=dt, embed_sec=tr.t_embed,
                n_embed=tr.n_embed, n_frames=len(az))


def const_track(x, az):
    n = x.shape[1]; J = (n - TN) // TH + 1
    return dict(az=np.full(J, float(az)), flag=np.ones(J, int), avail=np.arange(J) * TH + TN, sec=0.0,
                embed_sec=0.0, n_embed=0, n_frames=J)


def ref_flags(x, xy, az_ref, **kw):
    """Target-activity flags when the target direction is KNOWN (for the reference-direction RTF-MVDR): same
    candidate/track machinery as rtn, but the 'target' is whichever track lies within 20 deg of the reference."""
    tr = Tracker(xy, mode="rtn", **kw)
    n = x.shape[1]; J = (n - TN) // TH + 1; fl = np.zeros(J, int)
    for j in range(J):
        _, f = tr.step(x[:, j * TH: j * TH + TN])
        if f in (1, 2):   # re-label relative to the reference direction
            # the dominant track is the one that got the count this frame; recover it via the short map
            v = [max(tr.S[(int(t["az"]) + o) % 360] for o in range(-3, 4)) for t in tr.tracks]
            kd = int(np.argmax(v))
            f = 1 if abs(angdiff(tr.tracks[kd]["az"], az_ref)) <= 20 else 2
        fl[j] = f
    d = const_track(x, az_ref); d["flag"] = fl
    return d


def steer_at(trk, s):
    """latest tracker output available at sample s (causal). Before the first frame: index -1 -> None."""
    j = np.searchsorted(trk["avail"], s, side="right") - 1
    return j


# ---------------------------------------------------------------------------------------------- filters
def frac_delay_taps(delay, L=21, beta=6.0):
    n = np.arange(L)
    h = np.sinc(n - delay)
    # Kaiser window centred on the (fractional) delay
    u = (n - delay) / (L / 2)
    w = np.where(np.abs(u) < 1, np.i0(beta * np.sqrt(np.clip(1 - u ** 2, 0, 1))) / np.i0(beta), 0.0)
    h = h * w
    return h / h.sum()


class DSTime:
    """Time-domain delay-and-sum, block of 32 samples (2 ms)."""
    L = 21; BULK = 8

    def __init__(self, xy, block=32):
        self.xy = np.asarray(xy); self.M = len(xy); self.B = block
        self.r = float(np.max(np.linalg.norm(self.xy, axis=1)))
        self.hist = np.zeros((self.M, self.L - 1)); self.az = None; self.h = None; self.h_old = None
        self.latency_samples = self.BULK + self.r / C * FS
        self.cache = {}

    def taps(self, az):
        key = int(round(az)) % 360
        if key not in self.cache:
            u = np.array([np.cos(np.deg2rad(key)), np.sin(np.deg2rad(key))])
            tau = -(self.xy @ u) / C * FS                  # arrival delay vs origin (samples)
            dl = self.BULK + self.r / C * FS - tau             # align all to the latest possible arrival
            self.cache[key] = np.stack([frac_delay_taps(d, self.L) for d in dl]) / self.M
        return self.cache[key]

    def process_hop(self, xh, az, flag=1):
        h_new = self.taps(az)
        buf = np.concatenate([self.hist, xh], 1)
        def filt(h):
            return sum(np.convolve(buf[m], h[m], mode="valid") for m in range(self.M))
        if self.h is None or h_new is self.h:
            y = filt(h_new)
        else:   # crossfade old -> new weights over the block
            r = np.linspace(0, 1, self.B, endpoint=False)
            y = (1 - r) * filt(self.h) + r * filt(h_new)
        self.h = h_new; self.hist = buf[:, -(self.L - 1):]
        return y


def diffuse_gamma(xy, f):
    d = np.linalg.norm(np.asarray(xy)[:, None] - np.asarray(xy)[None], axis=-1)
    return np.sinc(2 * f[:, None, None] * d[None] / C)          # (F,M,M)


def wng_blend(w, w0, d, wng_min):
    """w, w0 (F,M) both distortionless w.r.t. d.  Blend w <- a w + (1-a) w0 (still distortionless) with the
    largest a in [0,1] such that WNG = |w^H d|^2 / |w|^2 >= wng_min.  Requires WNG(w0) >= wng_min."""
    g = np.abs(np.einsum("fm,fm->f", w.conj(), d)) ** 2
    lim = g / wng_min                                              # max allowed |w|^2
    nw = np.sum(np.abs(w) ** 2, 1)
    bad = nw > lim
    if not bad.any():
        return w
    # |a(w-w0) + w0|^2 = lim  -> quadratic in a
    dlt = w - w0
    A = np.sum(np.abs(dlt) ** 2, 1); B = 2 * np.real(np.sum(dlt * w0.conj(), 1)); Cc = np.sum(np.abs(w0) ** 2, 1) - lim
    disc = np.clip(B ** 2 - 4 * A * Cc, 0, None)
    a = np.clip((-B + np.sqrt(disc)) / (2 * A + 1e-30), 0, 1)
    a = np.where(bad, a, 1.0)
    return a[:, None] * w + (1 - a[:, None]) * w0


class STFTBF:
    """sqrt-Hann WOLA, window N, hop N/2: latency N samples."""

    def __init__(self, xy, win_ms=4, kind="sd", wng_db=0.0, lam_n=None, coh_thr=0.5, load=1e-2,
                 update_every=None, tau_ms=500.0, hang=3):
        self.xy = np.asarray(xy); self.M = len(xy)
        self.N = int(win_ms * FS / 1000); self.H = self.N // 2
        self.win = np.sqrt(np.hanning(self.N + 1)[:-1])
        self.f = np.fft.rfftfreq(self.N, 1 / FS); self.F = len(self.f)
        self.kind, self.wng = kind, 10 ** (wng_db / 10)
        self.G = diffuse_gamma(self.xy, self.f)
        self.lam = np.exp(-1000 * self.H / FS / tau_ms)
        self.coh_thr, self.load = coh_thr, load
        self.k = update_every or max(1, int(round(8e-3 * FS / self.H)))    # weights every ~8 ms
        self.inbuf = np.zeros((self.M, self.N)); self.outbuf = np.zeros(self.N)
        self.az = None; self.d = None; self.W = None; self.t = 0
        self.Rn = None; self.Rx = None; self.nn = 0; self.nx = 0; self.hang = hang; self.since_tgt = 99
        self.cs_num = np.zeros(self.F); self.cs_den = np.full(self.F, 1e-12)
        self.sd_cache = {}
        self.latency_samples = self.N

    # --- fixed superdirective weights for a direction (cached on the 1-degree grid)
    def sd_weights(self, az):
        key = int(round(az)) % 360
        if key in self.sd_cache:
            return self.sd_cache[key]
        d = R.steer2d(self.xy, float(key), self.f)                  # (F,M)
        lo = np.full(self.F, 1e-6); hi = np.full(self.F, 1e3)
        I = np.eye(self.M)
        def w_of(mu):
            a = np.linalg.solve(self.G + mu[:, None, None] * I, d[..., None])[..., 0]
            return a / np.einsum("fm,fm->f", d.conj(), a)[:, None]
        for _ in range(40):                                          # bisection on log(mu)
            mid = np.sqrt(lo * hi); w = w_of(mid)
            ok = 1.0 / np.sum(np.abs(w) ** 2, 1) >= self.wng
            hi = np.where(ok, mid, hi); lo = np.where(ok, lo, mid)
        w = w_of(hi)
        self.sd_cache[key] = (d, w)
        return d, w

    def _set_az(self, az):
        if self.az is None or abs(angdiff(az, self.az)) > 0.5:
            self.az = az; self.d, self.wsd = self.sd_weights(az)
            return True
        return False

    def _fb(self, fallback):
        """fallback weights (distortionless for the steering vector, since d[mic0] = 1): delay-and-sum, or the
        unprocessed reference microphone (e0)."""
        if fallback == "mic0":
            w = np.zeros_like(self.d); w[:, 0] = 1.0; return w
        return self.d / self.M

    def _adapt_weights(self):
        M, I = self.M, np.eye(self.M)
        d = self.d
        if self.Rn is None or self.nn < 25:
            return self.wsd
        tr = np.real(np.trace(self.Rn, axis1=1, axis2=2))[:, None, None]
        Rl = self.Rn + self.load * tr / M * I
        h = d
        if self.kind == "rtf" and self.nx >= 25:
            L = np.linalg.cholesky(Rl)                                 # Rl = L L^H
            Li = np.linalg.inv(L)
            A = Li @ self.Rx @ np.conj(np.swapaxes(Li, 1, 2))
            A = 0.5 * (A + np.conj(np.swapaxes(A, 1, 2)))
            ev, U = np.linalg.eigh(A)
            u = U[:, :, -1]
            he = np.einsum("fmn,fn->fm", L, u)                        # = Rn v
            he = he / (he[:, :1] + 1e-12)
            rho = np.abs(np.einsum("fm,fm->f", d.conj(), he)) ** 2 / (M * np.sum(np.abs(he) ** 2, 1) + 1e-12)
            good = (rho > 0.6) & np.isfinite(he).all(1) & (ev[:, -1] > 2.0)
            h = np.where(good[:, None], he, d)
            self.rtf_good = float(good.mean())
        a = np.linalg.solve(Rl, h[..., None])[..., 0]
        w = a / (np.einsum("fm,fm->f", h.conj(), a)[:, None] + 1e-12)
        w0 = h / np.sum(np.abs(h) ** 2, 1, keepdims=True)              # matched filter, WNG = |h|^2
        return wng_blend(w, w0, h, self.wng)

    def process_hop(self, xh, az, flag=1, conf=1.0, fallback="ds"):
        changed = self._set_az(az)
        self.inbuf = np.concatenate([self.inbuf[:, self.H:], xh], 1)
        Y = np.fft.rfft(self.inbuf * self.win, axis=1).T                # (F,M)
        if self.kind == "sd":
            W = self.wsd if conf >= 1.0 else conf * self.wsd + (1 - conf) * self._fb(fallback)
        else:
            upd = np.einsum("fm,fn->fmn", Y, Y.conj())
            if self.Rn is None:
                p = np.mean(np.abs(Y) ** 2) + 1e-12
                self.Rn = 1e-3 * p * (self.G + 0.1 * np.eye(self.M)); self.Rx = self.Rn.copy()
            self.since_tgt = 0 if flag in (1, 3) else self.since_tgt + 1
            tgt_on = self.since_tgt <= self.hang * (TH // self.H)      # target (possibly) active, + hangover
            if self.kind == "gm":
                num = np.abs(np.einsum("fm,fm->f", self.d.conj(), Y)) ** 2
                den = self.M * np.sum(np.abs(Y) ** 2, 1)
                self.cs_num = 0.6 * self.cs_num + 0.4 * num; self.cs_den = 0.6 * self.cs_den + 0.4 * den + 1e-20
                noise = (self.cs_num / self.cs_den < self.coh_thr) | (not tgt_on)
                m = noise[:, None, None]
                self.Rn = np.where(m, self.lam * self.Rn + (1 - self.lam) * upd, self.Rn)
                self.nn += int(noise.mean() > 0.3)
            else:   # rtf
                if flag == 1:
                    self.Rx = self.lam * self.Rx + (1 - self.lam) * upd; self.nx += 1
                elif not tgt_on:
                    self.Rn = self.lam * self.Rn + (1 - self.lam) * upd; self.nn += 1
            self.t += 1
            if self.W is None or changed or self.t % self.k == 0:
                self.W = self._adapt_weights()
            W = self.W if conf >= 1.0 else conf * self.W + (1 - conf) * self._fb(fallback)
        S = np.einsum("fm,fm->f", W.conj(), Y)
        y = np.fft.irfft(S, self.N) * self.win
        self.outbuf = np.concatenate([self.outbuf[self.H:], np.zeros(self.H)]) + y
        return self.outbuf[: self.H].copy()


def make_filter(name, xy, **kw):
    if name == "ds_td":
        return DSTime(xy)
    kind = "".join(c for c in name if c.isalpha()); ms = int("".join(c for c in name if c.isdigit()))
    return STFTBF(xy, win_ms=ms, kind=kind, **kw)


def lock_age(az, jump=10.0):
    """frames since the steering last JUMPED (> jump deg between consecutive tracker frames = a lock switch;
    track-azimuth refinements are smaller).  Counted from the first frame at the start of the input."""
    age = np.zeros(len(az), int)
    for j in range(1, len(az)):
        age[j] = 0 if abs(angdiff(az[j], az[j - 1])) > jump else age[j - 1] + 1
    return age


def run_filter(name, x, xy, trk, ramp_ms=0.0, fallback="ds", verify=None, smooth_ms=250.0, **kw):
    """Stream x (M,n) through filter `name` hop by hop with causal steering from trk.  Returns the output
    aligned to mic 0 (algorithmic latency compensated, as in round 5) and timing."""
    p = make_filter(name, xy, **kw)
    H = p.B if isinstance(p, DSTime) else p.H
    n = x.shape[1]; lat = p.latency_samples
    pad = np.concatenate([x, np.zeros((x.shape[0], int(np.ceil(lat)) + 2 * H))], 1)
    # CONFIDENCE RAMP (ramp_ms > 0): after the start and after every lock switch the STFT filters blend from
    # delay-and-sum weights (broad, harmless if mis-steered) to their own weights over ramp_ms (causal: uses
    # only the steering history).  Reference-direction (constant) tracks are always fully confident.
    const = bool(np.all(trk["az"] == trk["az"][0])) and trk.get("sec", 1) == 0.0
    age_ms = lock_age(trk["az"]) * 1000.0 * TH / FS
    # VERIFICATION GATE (verify = cosine threshold): the filter's own weights only while the steered track's
    # ECAPA score (vs the enrolment) is >= verify; otherwise the fallback weights; the blend factor moves at
    # most hop/smooth_ms per hop (no clicks).  Uses only past audio (scores are causal).
    sc = trk.get("score")
    cv = 0.0; step = H / (smooth_ms * FS / 1000)
    out = []; t0 = time.perf_counter()
    for i in range(0, pad.shape[1] - H + 1, H):
        j = steer_at(trk, i + H)            # tracker output available once this hop has arrived
        az = trk["az"][j] if j >= 0 else trk["az"][0] * 0.0
        fl = int(trk["flag"][j]) if j >= 0 else 0
        if verify is not None and not isinstance(p, DSTime):
            tgt = 1.0 if const else (1.0 if (j >= 0 and sc is not None and np.isfinite(sc[j]) and sc[j] >= verify) else 0.0)
            cv = float(np.clip(cv + np.clip(tgt - cv, -step, step), 0, 1))
            out.append(p.process_hop(pad[:, i:i + H], float(az), fl, cv, fallback))
        elif ramp_ms > 0 and not isinstance(p, DSTime):
            cf = 1.0 if const else (float(np.clip(age_ms[j] / ramp_ms, 0, 1)) if j >= 0 else 0.0)
            out.append(p.process_hop(pad[:, i:i + H], float(az), fl, cf, fallback))
        else:
            out.append(p.process_hop(pad[:, i:i + H], float(az), fl))
    dt = time.perf_counter() - t0
    y = np.concatenate(out)
    if isinstance(p, DSTime):
        sh = int(round(lat))       # integer part; the residual fractional delay (<0.5 sample) is left in
    else:
        sh = p.N - p.H
    info = dict(per_hop_ms=1000 * dt / len(out), hop_ms=1000 * H / FS, latency_ms=1000 * lat / FS, sec=dt,
                n_hops=len(out), rtf_good=getattr(p, "rtf_good", None))
    return y[sh: sh + n].astype(np.float32), info


LATENCY_MS = {"ds_td": 1000 * (DSTime.BULK + 0.0425 / C * FS) / FS, "sd4": 4, "sd8": 8, "gm4": 4, "gm8": 8,
              "rtf4": 4, "rtf8": 8}
