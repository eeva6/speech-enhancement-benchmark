"""Spatial features for diarization: SRP-PHAT azimuth maps on 0.5 s blocks.

LibriCSS: 7-mic circular array (centre + 6 on r = 4.25 cm), free-field far-field steering.
EasyCom: 4 frame mics of the glasses, measured ATF steering (el = 0 row), az convention of
results/r7/atf_convention.md (az = atan2(x, z), + = left, 0 = array forward).
"""
import numpy as np
from scipy.signal import stft

FS = 16000
NFFT, HOP = 512, 256
BLOCK = 0.5


def _blocks_cov(x, band):
    """x (M, N) -> per-0.5 s-block PHAT-normalised spatial covariance (B, F, M, M) and block energy (B,)."""
    _, _, X = stft(x, FS, nperseg=NFFT, noverlap=NFFT - HOP, boundary=None, padded=False)   # (M, F, T)
    X = X[:, band, :]
    E = (np.abs(X[0]) ** 2).sum(0)
    Xn = X / (np.abs(X) + 1e-12)
    tf = (np.arange(X.shape[2]) * HOP + NFFT / 2) / FS
    nb = int(np.ceil(x.shape[1] / FS / BLOCK))
    bi = np.minimum((tf / BLOCK).astype(int), nb - 1)
    M, F = X.shape[0], X.shape[1]
    R = np.zeros((nb, F, M, M), np.complex64)
    en = np.zeros(nb)
    for b in range(nb):
        sel = bi == b
        if sel.any():
            Z = Xn[:, :, sel]
            R[b] = np.einsum("mft,nft->fmn", Z, Z.conj()) / sel.sum()
            en[b] = E[sel].mean()
    return R, en


def srp_blocks(x, steer, band):
    """steer (D, F, M) unit-modulus steering on the band bins. Returns SRP map per block (B, D) and energy."""
    out = []; ens = []
    step = int(60 * FS)                          # process per minute to bound memory
    for s in range(0, x.shape[1], step):
        R, en = _blocks_cov(x[:, s:s + step], band)
        P = np.einsum("dfm,bfmn,dfn->bd", steer.conj(), R, steer, optimize=True).real
        out.append(P); ens.append(en)
    return np.concatenate(out, 0), np.concatenate(ens)


def libricss_steer(az_step=5.0):
    from ..libricss import MIC_XY, C
    f = np.fft.rfftfreq(NFFT, 1 / FS); band = (f >= 200) & (f <= 6000)
    az = np.arange(0, 360, az_step)
    u = np.stack([np.cos(np.deg2rad(az)), np.sin(np.deg2rad(az))], 1)          # (D, 2)
    tau = -(u @ MIC_XY.T) / C                                                  # (D, M) arrival delay vs centre
    steer = np.exp(-2j * np.pi * f[band][None, :, None] * tau[:, None, :])     # (D, F, M)
    return az, steer.astype(np.complex64), band


def easycom_steer():
    from .. import ec_r7 as E
    az_g, el_g, H = E.load_atf(chans=(0, 1, 2, 3))
    k = np.argmin(np.abs(el_g)); row = np.abs(el_g - el_g[k]) < 1e-6
    f = np.fft.rfftfreq(NFFT, 1 / FS); band = (f >= 300) & (f <= 6000)
    Hs = H[row][:, band, :]
    Hs = Hs / (np.abs(Hs) + 1e-12)
    az = az_g[row]
    o = np.argsort(az)
    return az[o], Hs[o].astype(np.complex64), band


def window_doa(P, wins, az):
    """SRP block maps -> per window: summed map, peak azimuth (deg) and peak sharpness (max/mean)."""
    nb = len(P)
    Pw = np.zeros((len(wins), P.shape[1]))
    for i, (a, b) in enumerate(wins):
        i0, i1 = int(round(a / BLOCK)), min(nb, int(round(b / BLOCK)))
        Pw[i] = P[i0:max(i1, i0 + 1)].sum(0)
    pk = az[np.argmax(Pw, 1)]
    sharp = Pw.max(1) / (Pw.mean(1) + 1e-12)
    return Pw, pk, sharp


def angle_affinity(az1, az2=None, sigma=20.0):
    """von Mises kernel on azimuth differences mapped to [-1, 1] (same scale as cosine similarity)."""
    az2 = az1 if az2 is None else az2
    d = np.deg2rad(np.asarray(az1)[:, None] - np.asarray(az2)[None, :])
    k = np.exp((np.cos(d) - 1.0) / np.deg2rad(sigma) ** 2)
    return 2 * k - 1
