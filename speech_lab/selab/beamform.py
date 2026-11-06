"""Multi-microphone beamformers for the simulated 4-mic linear array (4 cm spacing).

  bf_ds            : delay-and-sum, free-field steering to the known target azimuth
  bf_mvdr_oracle   : Souden MVDR with ORACLE speech/noise spatial covariances (upper bound, not deployable)
  bf_mvdr_ff       : MVDR with free-field steering vector + noise covariance estimated from frames the
                     Wiener-DD mask (classical, blind) marks as noise-dominated
  bf_mvdr_mask     : Souden MVDR with covariances weighted by a DNN mask (Demucs DNS64 run on mic 0),
                     i.e. mask-based beamforming (Heymann et al. 2016 style, different mask estimator)
  bf_mvdr_mask_pf  : bf_mvdr_mask followed by Demucs DNS64 single-channel post-filter
All STFT 32 ms / 8 ms; batch (utterance-level covariance) -> offline, not streaming as implemented.
"""
import numpy as np
from scipy.signal import stft, istft
from .common import FS, load
from .classical import NFFT, HOP, WIN

C = 343.0


def mstft(X):
    return np.stack([stft(x, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP)[2] for x in X])  # (M,F,T)


def mistft(Y, n):
    return istft(Y, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP)[1][:n].astype(np.float32)


def steering(mic_x, az_deg):
    f = np.fft.rfftfreq(NFFT, 1 / FS)
    tau = -np.asarray(mic_x) * np.cos(np.deg2rad(az_deg)) / C
    return np.exp(-2j * np.pi * f[:, None] * tau[None, :])  # (F,M)


def cov(X, w=None):
    # X (M,F,T) -> (F,M,M)
    if w is None:
        w = np.ones(X.shape[1:])
    R = np.einsum("ft,mft,nft->fmn", w, X, X.conj()) / (w.sum(1)[:, None, None] + 1e-9)
    return R


def _load_mc(d):
    mc = load_mc(d / "mix_mc.wav")
    return mc


def load_mc(p):
    import soundfile as sf
    x, sr = sf.read(str(p), dtype="float32")
    return x.T


def mvdr_souden(Rs, Rn, ref=0, load_=1e-3):
    M = Rs.shape[-1]
    W = np.zeros(Rs.shape[:2], complex)
    for f in range(Rs.shape[0]):
        Rn_f = Rn[f] + load_ * np.trace(Rn[f]).real / M * np.eye(M)
        num = np.linalg.solve(Rn_f, Rs[f])
        W[f] = num[:, ref] / (np.trace(num) + 1e-9)
    return W


def mvdr_steer(d, Rn, load_=1e-3):
    M = d.shape[1]
    W = np.zeros(d.shape, complex)
    for f in range(d.shape[0]):
        Rn_f = Rn[f] + load_ * np.trace(Rn[f]).real / M * np.eye(M)
        a = np.linalg.solve(Rn_f, d[f])
        W[f] = a / (d[f].conj() @ a + 1e-9)
    return W


def apply(W, X):
    return np.einsum("fm,mft->ft", W.conj(), X)


def bf_ds(d, meta, **_):
    X = mstft(load_mc(d / "mix_mc.wav"))
    D = steering(meta["mic_x"], meta["tgt_az"])
    Y = apply(D / D.shape[1], X)
    return mistft(Y, X.shape[-1] * HOP)


def _n(d):
    return load_mc(d / "mix_mc.wav").shape[1]


def bf_mvdr_oracle(d, meta, **_):
    x = load_mc(d / "mix_mc.wav"); n = x.shape[1]
    X = mstft(x)
    Rs = cov(mstft(load_mc(d / "target_mc.wav")))
    Rn = cov(mstft(load_mc(d / "noise_mc.wav")))
    return mistft(apply(mvdr_souden(Rs, Rn), X), n)


def _dnn_mask(x0):
    from .neural import run_demucs
    s = run_demucs(x0)
    S = stft(s, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP)[2]
    Y = stft(x0, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP)[2]
    N = Y - S
    m = np.abs(S) ** 2 / (np.abs(S) ** 2 + np.abs(N) ** 2 + 1e-10)
    return m


def bf_mvdr_mask(d, meta, **_):
    x = load_mc(d / "mix_mc.wav"); n = x.shape[1]
    X = mstft(x)
    m = _dnn_mask(x[0])[:, : X.shape[2]]
    W = mvdr_souden(cov(X, m), cov(X, 1 - m))
    return mistft(apply(W, X), n)


def bf_mvdr_ff(d, meta, **_):
    from .classical import _stft, min_stats_noise, _dd_gain
    x = load_mc(d / "mix_mc.wav"); n = x.shape[1]
    X = mstft(x)
    Y0 = _stft(x[0])[:, : X.shape[2]]
    P = np.abs(Y0) ** 2
    G = _dd_gain(P, np.maximum(min_stats_noise(P), 1e-10), "wiener")
    w = (G < 0.5).astype(float)  # noise-dominated TF bins
    D = steering(meta["mic_x"], meta["tgt_az"])
    return mistft(apply(mvdr_steer(D, cov(X, w)), X), n)


def bf_mvdr_mask_pf(d, meta, **_):
    from .neural import run_demucs
    return run_demucs(bf_mvdr_mask(d, meta))


METHODS = {"bf_ds": bf_ds, "bf_mvdr_oracle": bf_mvdr_oracle, "bf_mvdr_ff": bf_mvdr_ff,
           "bf_mvdr_mask": bf_mvdr_mask, "bf_mvdr_mask_pf": bf_mvdr_mask_pf}
