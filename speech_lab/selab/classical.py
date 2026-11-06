"""Classical single-channel enhancers, implemented from the original papers.

All share one STFT (32 ms sqrt-Hann, 8 ms hop @16 kHz) and one blind noise-PSD tracker
(simplified minimum statistics, Martin 2001), so differences come from the gain rule only.
Every method is frame-causal: algorithmic latency = 32 ms window (+ 0 lookahead).

  specsub   : power spectral subtraction with SNR-dependent over-subtraction + spectral floor (Berouti et al. 1979)
  wiener_dd : Wiener gain with decision-directed a-priori SNR (Ephraim & Malah 1984; Scalart & Vieira Filho 1996)
  mmse_lsa  : log-spectral-amplitude MMSE estimator (Ephraim & Malah 1985), same a-priori SNR estimator
  noisereduce : third-party spectral gating (noisereduce package, non-stationary mode) as an off-the-shelf baseline

`noise_psd="oracle"` lets round-2 experiments isolate gain rule from noise-estimation error.
"""
import numpy as np
from scipy.signal import stft, istft
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.special import exp1
from .common import FS

NFFT, HOP = 512, 128
WIN = np.sqrt(np.hanning(NFFT + 1)[:-1])
ALGO_LATENCY_MS = 1000 * NFFT / FS


def _stft(x):
    _, _, X = stft(x, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP, boundary="zeros", padded=True)
    return X


def _istft(X, n):
    _, x = istft(X, FS, window=WIN, nperseg=NFFT, noverlap=NFFT - HOP, boundary=True)
    return x[:n].astype(np.float32)


def min_stats_noise(P, alpha=0.85, win_s=1.5, bias=1.8):
    """Causal minimum-statistics noise PSD: recursive smoothing then running min over the past win_s seconds."""
    S = np.empty_like(P)
    acc = P[:, 0]
    for t in range(P.shape[1]):
        acc = alpha * acc + (1 - alpha) * P[:, t]
        S[:, t] = acc
    D = int(win_s * FS / HOP)
    # origin shifts the window entirely into the past -> causal
    Nmin = minimum_filter1d(S, size=D, axis=1, origin=(D - 1) // 2, mode="nearest")
    # smooth across frequency a little to reduce musical-noise-inducing variance
    return bias * uniform_filter1d(Nmin, 3, axis=0)


def _noise(X, noise_psd, noise_sig):
    P = np.abs(X) ** 2
    if noise_psd == "oracle":
        Nx = _stft(noise_sig)[:, : X.shape[1]]
        # oracle long-term PSD of the actual noise (still a smoothed estimate, not per-frame truth)
        Npow = np.abs(Nx) ** 2
        N = uniform_filter1d(Npow, size=int(0.5 * FS / HOP), axis=1, mode="nearest")
    else:
        N = min_stats_noise(P)
    return P, np.maximum(N, 1e-10)


def specsub(x, noise_psd="ms", noise_sig=None, beta=0.02, **_):
    X = _stft(x)
    P, N = _noise(X, noise_psd, noise_sig)
    seg_snr = 10 * np.log10(P.sum(0) / N.sum(0) + 1e-10)
    alpha = np.clip(4 - 3 * seg_snr / 20, 1, 5)[None, :]  # Berouti: alpha=4 at 0 dB -> 1 at 20 dB
    S = np.maximum(P - alpha * N, beta * N)
    G = np.sqrt(S / np.maximum(P, 1e-10))
    return _istft(G * X, len(x))


def _dd_gain(P, N, rule, a=0.98, gmin_db=-20):
    gamma = P / N
    G = np.ones_like(P)
    gmin = 10 ** (gmin_db / 20)
    prev = np.zeros(P.shape[0])
    for t in range(P.shape[1]):
        g = gamma[:, t]
        xi = a * prev + (1 - a) * np.maximum(g - 1, 0)
        xi = np.maximum(xi, 10 ** (-25 / 10))
        if rule == "wiener":
            gt = xi / (1 + xi)
        else:  # log-spectral amplitude
            v = np.minimum(xi / (1 + xi) * g, 500)
            gt = xi / (1 + xi) * np.exp(0.5 * exp1(np.maximum(v, 1e-8)))
        gt = np.clip(gt, gmin, 1.0)
        G[:, t] = gt
        prev = (gt ** 2) * g  # |S_hat|^2 / N of this frame
    return G


def wiener_dd(x, noise_psd="ms", noise_sig=None, **_):
    X = _stft(x)
    P, N = _noise(X, noise_psd, noise_sig)
    return _istft(_dd_gain(P, N, "wiener") * X, len(x))


def mmse_lsa(x, noise_psd="ms", noise_sig=None, **_):
    X = _stft(x)
    P, N = _noise(X, noise_psd, noise_sig)
    return _istft(_dd_gain(P, N, "lsa") * X, len(x))


def noisereduce_ng(x, **_):
    import noisereduce as nr
    return nr.reduce_noise(y=x, sr=FS, stationary=False).astype(np.float32)


METHODS = {"specsub": specsub, "wiener_dd": wiener_dd, "mmse_lsa": mmse_lsa, "noisereduce": noisereduce_ng}
