"""Truly frame-by-frame (streaming) implementations for the latency-budget experiment.

Each processor consumes one hop of input at a time, keeps only past state, and emits one hop of output
via weighted overlap-add. Algorithmic latency = window length N (sqrt-Hann analysis+synthesis, hop N/2).
Nothing here looks at future samples or at utterance-level statistics.

  wiener_stream{8,16,32}  : decision-directed Wiener gain + online minimum-statistics noise tracker,
                            window 8 / 16 / 32 ms -> algorithmic latency 8 / 16 / 32 ms
  bf_online_ff            : 4-mic MVDR, free-field steering to the known azimuth, noise covariance updated
                            recursively from bins the (streaming) Wiener gain marks noise-dominated
  bf_online_ff_rnnoise    : bf_online_ff -> RNNoise post-filter (latency adds: 32 + 20 ms)
"""
import time
import numpy as np
from .common import FS
from .beamform import load_mc, steering

C = 343.0


class OnlineMinStats:
    """Martin-2001-style minimum tracking with U sub-windows of V frames (O(F) per frame)."""

    def __init__(self, F, hop, win_s=1.5, alpha=0.85, bias=1.8, U=8):
        D = max(int(win_s * FS / hop), U)
        self.V = max(D // U, 1); self.U = U
        self.alpha, self.bias = alpha, bias
        self.P = None; self.cur = np.full(F, np.inf); self.mins = []; self.count = 0

    def update(self, p):
        self.P = p.copy() if self.P is None else self.alpha * self.P + (1 - self.alpha) * p
        self.cur = np.minimum(self.cur, self.P); self.count += 1
        if self.count >= self.V:
            self.mins.append(self.cur); self.mins = self.mins[-self.U:]
            self.cur = np.full_like(self.cur, np.inf); self.count = 0
        m = np.minimum.reduce(self.mins + [self.cur]) if self.mins else self.cur
        m = np.where(np.isfinite(m), m, self.P)
        return np.maximum(self.bias * m, 1e-10)


class StreamWiener:
    def __init__(self, win_ms=32, a=0.98, gmin_db=-20):
        self.N = int(win_ms * FS / 1000); self.H = self.N // 2
        self.win = np.sqrt(np.hanning(self.N + 1)[:-1])
        F = self.N // 2 + 1
        self.ns = OnlineMinStats(F, self.H)
        self.a, self.gmin = a, 10 ** (gmin_db / 20)
        self.prev = np.zeros(F); self.inbuf = np.zeros(self.N); self.outbuf = np.zeros(self.N)

    def gain(self, Y):
        p = np.abs(Y) ** 2
        n = self.ns.update(p)
        g = p / n
        xi = np.maximum(self.a * self.prev + (1 - self.a) * np.maximum(g - 1, 0), 10 ** (-2.5))
        G = np.clip(xi / (1 + xi), self.gmin, 1)
        self.prev = G ** 2 * g
        return G

    def process_hop(self, x_hop):
        self.inbuf = np.concatenate([self.inbuf[self.H:], x_hop])
        Y = np.fft.rfft(self.inbuf * self.win)
        y = np.fft.irfft(self.gain(Y) * Y, self.N) * self.win
        self.outbuf = np.concatenate([self.outbuf[self.H:], np.zeros(self.H)]) + y
        return self.outbuf[: self.H].copy()


def stream_run(proc, x, H):
    """Feed x hop by hop; output is delayed by (N - H) + H = N samples relative to input; re-align for scoring."""
    n = len(x); pad = np.concatenate([x, np.zeros(2 * proc.N)])
    out = []
    t0 = time.perf_counter()
    for i in range(0, len(pad) - H + 1, H):
        out.append(proc.process_hop(pad[i:i + H]))
    dt = time.perf_counter() - t0
    y = np.concatenate(out)
    delay = proc.N - H  # OLA output for samples [i-N+H, i+H) is complete once hop i arrives
    return y[delay:delay + n].astype(np.float32), dt / (len(out))


LAST_STATS = {}


def _wiener(ms):
    def f(x, **_):
        p = StreamWiener(ms)
        y, per_hop = stream_run(p, x, p.H)
        LAST_STATS.update(per_hop_ms=1000 * per_hop, hop_ms=1000 * p.H / FS, latency_ms=1000 * p.N / FS)
        return y
    return f


class StreamMVDR:
    """Online MVDR with free-field steering; Rn recursively averaged over noise-dominated bins."""

    def __init__(self, mic_x, az, win_ms=32, lam=0.98, load_=1e-2, update_every=2):
        self.N = int(win_ms * FS / 1000); self.H = self.N // 2
        self.win = np.sqrt(np.hanning(self.N + 1)[:-1])
        self.M = len(mic_x)
        f = np.fft.rfftfreq(self.N, 1 / FS)
        tau = -np.asarray(mic_x) * np.cos(np.deg2rad(az)) / C
        self.d = np.exp(-2j * np.pi * f[:, None] * tau[None, :])           # (F,M)
        F = len(f)
        self.Rn = np.tile(np.eye(self.M, dtype=complex), (F, 1, 1)) * 1e-6
        self.W = self.d / self.M                                            # start as delay-and-sum
        self.lam, self.load, self.k, self.t = lam, load_, update_every, 0
        self.vad = StreamWiener(win_ms)
        self.inbuf = np.zeros((self.M, self.N)); self.outbuf = np.zeros(self.N)

    def process_hop(self, X_hop):  # (M, H)
        self.inbuf = np.concatenate([self.inbuf[:, self.H:], X_hop], 1)
        Y = np.fft.rfft(self.inbuf * self.win, axis=1).T                   # (F,M)
        G = self.vad.gain(Y[:, 0])
        w = (G < 0.5).astype(float)[:, None, None]
        upd = np.einsum("fm,fn->fmn", Y, Y.conj())
        self.Rn = np.where(w > 0, self.lam * self.Rn + (1 - self.lam) * upd, self.Rn)
        self.t += 1
        if self.t % self.k == 0:
            tr = np.real(np.trace(self.Rn, axis1=1, axis2=2))[:, None, None]
            R = self.Rn + self.load * tr / self.M * np.eye(self.M)
            a = np.linalg.solve(R, self.d[..., None])[..., 0]
            self.W = a / (np.einsum("fm,fm->f", self.d.conj(), a)[:, None] + 1e-12)
        S = np.einsum("fm,fm->f", self.W.conj(), Y)
        y = np.fft.irfft(S, self.N) * self.win
        self.outbuf = np.concatenate([self.outbuf[self.H:], np.zeros(self.H)]) + y
        return self.outbuf[: self.H].copy()


def bf_online_ff(d, meta, **_):
    x = load_mc(d / "mix_mc.wav"); n = x.shape[1]
    p = StreamMVDR(meta["mic_x"], meta["tgt_az"])
    pad = np.concatenate([x, np.zeros((x.shape[0], 2 * p.N))], 1)
    out = []; t0 = time.perf_counter()
    for i in range(0, pad.shape[1] - p.H + 1, p.H):
        out.append(p.process_hop(pad[:, i:i + p.H]))
    dt = time.perf_counter() - t0
    LAST_STATS.update(per_hop_ms=1000 * dt / len(out), hop_ms=1000 * p.H / FS, latency_ms=1000 * p.N / FS)
    y = np.concatenate(out)
    return y[p.N - p.H: p.N - p.H + n].astype(np.float32)


def bf_online_ff_rnnoise(d, meta, **_):
    from .neural import run_rnnoise
    return run_rnnoise(bf_online_ff(d, meta))


SC_METHODS = {"wiener_stream8": _wiener(8), "wiener_stream16": _wiener(16), "wiener_stream32": _wiener(32)}
BF_METHODS = {"bf_online_ff": bf_online_ff, "bf_online_ff_rnnoise": bf_online_ff_rnnoise}
