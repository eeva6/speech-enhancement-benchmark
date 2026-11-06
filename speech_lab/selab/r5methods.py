"""Round 5 methods for 2-D arrays (LibriCSS 7-mic circle, its simulated twin, and app uploads).

DOA estimation (no oracle information):
  srp_frames      PHAT-weighted steered response power per STFT frame on a 1-degree azimuth grid
                  (equivalent to SRP-PHAT up to a constant); band 200-5000 Hz.
  doa_blind       argmax of the SRP map summed over the whole segment (offline)
  doa_causal      running SRP map with exponential forgetting -> one azimuth per hop (online, causal)
Beamformers:
  ds_est          delay-and-sum steered to doa_blind (offline DOA, causal filter)
  mvdr_online_est online MVDR (round-3 StreamMVDR generalised to 2-D geometry); steering follows doa_causal;
                  noise covariance updated recursively on bins the streaming Wiener gain marks noise-dominated
  mvdr_online_dir_est  same, but Rn is ALSO updated on bins whose spatial coherence with the current steering
                  vector is low (directional gating: interfering talkers enter Rn, not just stationary noise)
  mvdr_online_ref / mvdr_online_dir_ref   same filters steered to the system-identification reference DOA
                  (an ORACLE-geometry control that isolates the cost of DOA errors)
  mvdr_mask_demucs offline Souden MVDR, masks from Demucs DNS64 on mic 0 (round-1 method, for comparability)
  mvdr_mask_tse   offline Souden MVDR, target mask from the TSE output on mic 0 (Conv-TasNet + ECAPA)
Single channel on the reference mic 0: rnnoise, deepfilternet3, tse (Conv-TasNet + ECAPA, enrolment = another
utterance of the same speaker recorded by the same array).  Cascades: mvdr_online_est_dfn3, mvdr_online_est_tse,
mvdr_online_dir_est_tse.
"""
import time
import numpy as np
from scipy.signal import stft, istft
from .common import FS

C = 343.0
NFFT, HOP = 512, 256
WIN = np.sqrt(np.hanning(NFFT + 1)[:-1])
AZ = np.arange(360.0)
LAST = {}


def steer2d(xy, az_deg, f):
    u = np.stack([np.cos(np.deg2rad(az_deg)), np.sin(np.deg2rad(az_deg))], -1)   # (...,2)
    tau = -(u @ np.asarray(xy).T) / C                                             # (...,M) arrival vs origin
    return np.exp(-2j * np.pi * f[:, None] * tau[..., None, :])                   # (...,F,M)


def mstft(x):
    return np.stack([stft(c, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP)[2] for c in x])  # (M,F,T)


def mistft(Y, n):
    return istft(Y, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP)[1][:n].astype(np.float32)


_SV = {}


def _sv(xy, f):
    key = (np.asarray(xy).tobytes(), len(f))
    if key not in _SV:
        _SV[key] = steer2d(xy, AZ, f)            # (A,F,M)
    return _SV[key]


def srp_frames(X, xy, band=(200, 5000)):
    """X (M,F,T) -> (T,A) PHAT steered power."""
    f = np.fft.rfftfreq(NFFT, 1 / FS)
    k = (f >= band[0]) & (f <= band[1])
    Xn = X[:, k, :] / (np.abs(X[:, k, :]) + 1e-9)
    D = _sv(xy, f)[:, k, :]                                    # (A,Fk,M)
    out = np.zeros((X.shape[2], len(AZ)))
    for t0 in range(0, X.shape[2], 64):                         # chunked: keeps memory < 100 MB
        B = np.einsum("afm,mft->aft", D.conj(), Xn[:, :, t0:t0 + 64])
        out[t0:t0 + 64] = (np.abs(B) ** 2).sum(1).T
    return out                                                  # (T,A)


def doa_blind(P):
    return float(AZ[np.argmax(P.sum(0))])


def doa_from_frames(P, mask):
    return float(AZ[np.argmax(P[mask].sum(0))]) if mask.any() else doa_blind(P)


def doa_causal(P, lam=0.97):
    acc = np.zeros(P.shape[1]); out = np.zeros(P.shape[0])
    for t in range(P.shape[0]):
        acc = lam * acc + P[t]; out[t] = AZ[np.argmax(acc)]
    return out


def angerr(a, b):
    return float(np.abs((np.asarray(a) - np.asarray(b) + 180) % 360 - 180))


class StreamMVDR2D:
    """Online MVDR, hop-by-hop, sqrt-Hann 32 ms / 16 ms, steering may change every hop. Latency 32 ms."""

    def __init__(self, xy, win_ms=32, lam=0.98, load_=1e-2, update_every=2, directional=False, coh_thr=0.5):
        from .streaming import StreamWiener
        self.N = int(win_ms * FS / 1000); self.H = self.N // 2
        self.win = np.sqrt(np.hanning(self.N + 1)[:-1])
        self.xy = np.asarray(xy); self.M = len(xy)
        self.f = np.fft.rfftfreq(self.N, 1 / FS); F = len(self.f)
        self.Rn = np.tile(np.eye(self.M, dtype=complex), (F, 1, 1)) * 1e-6
        self.lam, self.load, self.k, self.t = lam, load_, update_every, 0
        self.vad = StreamWiener(win_ms)
        self.directional, self.coh_thr = directional, coh_thr
        self.inbuf = np.zeros((self.M, self.N)); self.outbuf = np.zeros(self.N)
        self.az = None; self.d = None; self.W = None

    def set_az(self, az):
        if self.az is None or angerr(az, self.az) > 0.5:
            self.az = az; self.d = steer2d(self.xy, az, self.f)
            self._solve()

    def _solve(self):
        tr = np.real(np.trace(self.Rn, axis1=1, axis2=2))[:, None, None]
        R = self.Rn + self.load * tr / self.M * np.eye(self.M)
        a = np.linalg.solve(R, self.d[..., None])[..., 0]
        self.W = a / (np.einsum("fm,fm->f", self.d.conj(), a)[:, None] + 1e-12)

    def process_hop(self, X_hop):
        self.inbuf = np.concatenate([self.inbuf[:, self.H:], X_hop], 1)
        Y = np.fft.rfft(self.inbuf * self.win, axis=1).T                    # (F,M)
        G = self.vad.gain(Y[:, 0])
        noise = G < 0.5
        if self.directional:
            coh = np.abs(np.einsum("fm,fm->f", self.d.conj(), Y)) ** 2 / (self.M * np.sum(np.abs(Y) ** 2, 1) + 1e-12)
            noise = noise | (coh < self.coh_thr)
        w = noise.astype(float)[:, None, None]
        upd = np.einsum("fm,fn->fmn", Y, Y.conj())
        self.Rn = np.where(w > 0, self.lam * self.Rn + (1 - self.lam) * upd, self.Rn)
        self.t += 1
        if self.t % self.k == 0:
            self._solve()
        S = np.einsum("fm,fm->f", self.W.conj(), Y)
        y = np.fft.irfft(S, self.N) * self.win
        self.outbuf = np.concatenate([self.outbuf[self.H:], np.zeros(self.H)]) + y
        return self.outbuf[: self.H].copy()


def run_online(x, xy, az_track, directional=False):
    """x (M,n); az_track: scalar or per-hop array (hop = 16 ms). Returns aligned output, per-hop ms."""
    p = StreamMVDR2D(xy, directional=directional)
    n = x.shape[1]
    pad = np.concatenate([x, np.zeros((x.shape[0], 2 * p.N))], 1)
    out = []; t0 = time.perf_counter(); j = 0
    for i in range(0, pad.shape[1] - p.H + 1, p.H):
        az = az_track if np.isscalar(az_track) else az_track[min(j, len(az_track) - 1)]
        p.set_az(float(az)); out.append(p.process_hop(pad[:, i:i + p.H])); j += 1
    dt = time.perf_counter() - t0
    LAST.update(per_hop_ms=1000 * dt / len(out), hop_ms=1000 * p.H / FS, latency_ms=1000 * p.N / FS)
    y = np.concatenate(out)
    return y[p.N - p.H: p.N - p.H + n].astype(np.float32)


def causal_track(x, xy):
    """Causal DOA per 16-ms hop from the running SRP map (the SRP frame at hop j uses samples up to hop j)."""
    X = mstft(x)
    P = srp_frames(X, xy)
    return doa_causal(P), P


# ------------------------------------------------------------------ method wrappers
def _mvdr_mask(x, m):
    from .beamform import cov, mvdr_souden
    X = mstft(x)
    m = m[:, : X.shape[2]]
    W = mvdr_souden(cov(X, m), cov(X, 1 - m))
    return mistft(np.einsum("fm,mft->ft", W.conj(), X), x.shape[1])


def _mask_from(est, x0):
    S = stft(est, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP)[2]
    Y = stft(x0, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP)[2]
    T = min(S.shape[1], Y.shape[1]); S, Y = S[:, :T], Y[:, :T]
    N = Y - S
    return np.clip(np.abs(S) ** 2 / (np.abs(S) ** 2 + np.abs(N) ** 2 + 1e-10), 0, 1)


LEVEL_RMS = 0.05   # -26 dBFS: input gain staging for the neural models (see _lv)


def _lv(fn, *a, **k):
    """Gain-stage the input to LEVEL_RMS before a level-dependent neural model and undo the gain afterwards.
    Round-5 finding: the LibriCSS recordings sit at about -53 dBFS (rounds 1-4 mixtures: about -17 dBFS);
    DeepFilterNet3 fed the raw level attenuated almost everything (Whisper WER 0.98).  A device would have
    an AGC / fixed preamp gain in front of the model; this is that gain (a scalar per utterance)."""
    x = a[0]; g = LEVEL_RMS / (float(np.sqrt(np.mean(x ** 2))) + 1e-9)
    return fn(x * g, *a[1:], **k) / g


def get_methods():
    from . import neural

    def ds_est(x, xy, ctx):
        X = mstft(x); az = ctx.setdefault("az_blind", doa_blind(srp_frames(X, xy)))
        D = steer2d(xy, az, np.fft.rfftfreq(NFFT, 1 / FS))
        return mistft(np.einsum("fm,mft->ft", D.conj() / len(xy), X), x.shape[1])

    def track(x, xy, ctx):
        if "track" not in ctx:
            ctx["track"], _ = causal_track(x, xy)
        return ctx["track"]

    def _mv(x, xy, ctx):
        c = ctx.get("mvdr_cached")
        return c if c is not None else run_online(x, xy, track(x, xy, ctx))

    M = {
        "noisy": lambda x, xy, ctx: x[0].copy(),
        "rnnoise": lambda x, xy, ctx: _lv(neural.run_rnnoise, x[0]),
        "deepfilternet3": lambda x, xy, ctx: _lv(neural.run_deepfilternet, x[0]),
        "tse": lambda x, xy, ctx: ctx.get("tse_cached") if ctx.get("tse_cached") is not None else neural.run_tse_ecapa(x[0], enrol=ctx["enrol"], info=ctx.setdefault("info", {})),
        "ds_est": ds_est,
        "mvdr_online_est": lambda x, xy, ctx: run_online(x, xy, track(x, xy, ctx)),
        "mvdr_online_dir_est": lambda x, xy, ctx: run_online(x, xy, track(x, xy, ctx), directional=True),
        "mvdr_online_ref": lambda x, xy, ctx: run_online(x, xy, ctx["az_ref"]),
        "mvdr_online_dir_ref": lambda x, xy, ctx: run_online(x, xy, ctx["az_ref"], directional=True),
        "mvdr_mask_demucs": lambda x, xy, ctx: _mvdr_mask(x, _mask_from(neural.run_demucs(x[0]), x[0])),
        "mvdr_mask_tse": lambda x, xy, ctx: _mvdr_mask(x, _mask_from(M["tse"](x, xy, ctx), x[0])),
        "tse_dryenrol": lambda x, xy, ctx: neural.run_tse_ecapa(x[0], enrol=ctx["enrol_dry"]),
        "mvdr_online_est_dfn3": lambda x, xy, ctx: _lv(neural.run_deepfilternet, _mv(x, xy, ctx)),
        "mvdr_online_est_tse": lambda x, xy, ctx: neural.run_tse_ecapa(_mv(x, xy, ctx), enrol=ctx["enrol"]),
        "mvdr_online_dir_est_tse": lambda x, xy, ctx: neural.run_tse_ecapa(run_online(x, xy, track(x, xy, ctx), directional=True), enrol=ctx["enrol"]),
    }
    return M


LATENCY = {  # algorithmic latency (documented / by construction), deployability
    "noisy": "0", "rnnoise": "10 ms frame (+20 ms measured delay)", "deepfilternet3": "40 ms (config)",
    "tse": "non-causal (utterance)", "ds_est": "filter causal; DOA offline (whole segment)",
    "mvdr_online_est": "32 ms, fully causal incl. DOA", "mvdr_online_dir_est": "32 ms, fully causal incl. DOA",
    "mvdr_online_ref": "32 ms; ORACLE geometry", "mvdr_online_dir_ref": "32 ms; ORACLE geometry",
    "mvdr_mask_demucs": "offline (utterance covariances)", "mvdr_mask_tse": "offline",
    "mvdr_online_est_dfn3": "72 ms, causal", "mvdr_online_est_tse": "non-causal TSE stage",
    "mvdr_online_dir_est_tse": "non-causal TSE stage", "tse_dryenrol": "non-causal (utterance); studio-clean enrolment",
}
