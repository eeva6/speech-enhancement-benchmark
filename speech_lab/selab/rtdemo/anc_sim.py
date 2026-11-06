"""SIMULATED noise-cut track: applies the portfolio's SIMULATED ANC attenuation spectra as fixed filters.

Nothing here is real ANC, and nothing was measured on a head. Sources of the attenuation curves (all simulations
from the ANC pass-by / restaurant lab, /workspace/projects/378dbbe1-.../lab):
  traffic    per-1/3-octave reduction of the best glasses config (c1_glasses_4mic7_causal: 7.8 dB(A) LAeq on the
             synthetic pass-by) computed here from its saved ear signals d (ANC off) and e (ANC on), 1-9 s.
  companion  octave-band change of the companions' level under plain open-ear ANC in the simulated restaurant
             (anc_plain_causal: -5.2 dB(A) on companions).
  babble     octave-band babble reduction under the same plain ANC (-3.7 dB(A)).
Each curve becomes a 512-tap minimum-phase FIR at 16 kHz (cepstral method), applied causally block by block.

Use per scene:
  simulated scenes (talker and noise images known): talkers get the 'companion' curve; noise gets 'traffic'
     (street) or 'babble' (restaurant); the competing talker counts as noise (it is cut by the babble curve).
  real recordings (EasyCom, LibriCSS: sources NOT separable): the whole front-mic signal gets the 'companion'
     curve, i.e. everything is cut the way plain ANC cut the companions.  The sim's SNR loss (babble cut 1.5 dB
     less than companions) is therefore NOT reproduced on real recordings.
"""
import json
import numpy as np
from ..common import FS, RES

LAB = "/workspace/projects/378dbbe1-3473-4845-9672-c34611d3997a/lab"
NT = 512


def _third_oct_reduction():
    z = np.load(f"{LAB}/results/anc_passby/runs/c1_glasses_4mic7_causal.npz")
    fs0 = 44100; d = z["d"][fs0:9 * fs0].astype(np.float64); e = z["e"][fs0:9 * fs0].astype(np.float64)
    fc = 1000 * 2.0 ** (np.arange(-13, 10) / 3)            # 50 Hz .. 8 kHz
    D = np.abs(np.fft.rfft(d)) ** 2; Ee = np.abs(np.fft.rfft(e)) ** 2; f = np.fft.rfftfreq(len(d), 1 / fs0)
    red = []
    for c in fc:
        k = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        red.append(10 * np.log10(Ee[k].sum() / D[k].sum()))   # dB change (negative = quieter)
    return fc, np.array(red)


def _restaurant_curves():
    r = json.load(open(f"{LAB}/results/anc_restaurant/results.json"))["anc_plain_causal"]
    fc = np.array([125, 250, 500, 1000, 2000, 4000], float)
    comp = np.array([r["oct"][str(int(c))]["comp_change"] for c in fc])          # dB change (negative = cut)
    bab = np.array([-r["oct"][str(int(c))]["babble_red"] for c in fc])
    return fc, comp, bab, dict(comp_dBA=r["comp_change_dBA"], babble_dBA=-r["babble_red_dBA"])


def curves():
    fc_t, tr = _third_oct_reduction()
    fc_r, comp, bab, dba = _restaurant_curves()
    return dict(traffic=(fc_t, tr), companion=(fc_r, comp), babble=(fc_r, bab), dba=dba)


def minphase_fir(fc, gdb, ntaps=NT, nfft=8192):
    f = np.fft.rfftfreq(nfft, 1 / FS)
    lf = np.log2(np.clip(f, fc[0], fc[-1]))
    g = np.interp(lf, np.log2(fc), gdb)                    # hold the end values outside the band
    mag = 10 ** (g / 20)
    # cepstral minimum phase
    logm = np.log(np.maximum(mag, 1e-6))
    cep = np.fft.irfft(logm, nfft)
    w = np.zeros(nfft); w[0] = 1; w[1:nfft // 2] = 2; w[nfft // 2] = 1
    H = np.exp(np.fft.rfft(cep * w))
    h = np.fft.irfft(H, nfft)[:ntaps]
    h *= np.hanning(2 * ntaps)[ntaps:]                     # gentle fade of the tail
    return h


class StreamFIR:
    """causal block FIR (overlap-save style history), exact equivalent of lfilter(h, 1, x)."""

    def __init__(self, h):
        self.h = np.asarray(h, float); self.hist = np.zeros(len(h) - 1)

    def process(self, xb):
        buf = np.concatenate([self.hist, xb])
        y = np.convolve(buf, self.h, mode="valid")
        self.hist = buf[-(len(self.h) - 1):]
        return y


def filters():
    c = curves()
    return {k: minphase_fir(*c[k]) for k in ("traffic", "companion", "babble")}, c


def a_weight_db(f):
    f = np.maximum(f, 1e-3)
    ra = (12194 ** 2 * f ** 4) / ((f ** 2 + 20.6 ** 2) * np.sqrt((f ** 2 + 107.7 ** 2) * (f ** 2 + 737.9 ** 2)) * (f ** 2 + 12194 ** 2))
    return 20 * np.log10(ra) + 2.0


def dba_change(x, y):
    """A-weighted level change (dB) from x to y (same length), FFT-domain weighting."""
    f = np.fft.rfftfreq(len(x), 1 / FS); w = 10 ** (a_weight_db(f) / 10)
    X = np.sum(w * np.abs(np.fft.rfft(x)) ** 2); Y = np.sum(w * np.abs(np.fft.rfft(y)) ** 2)
    return float(10 * np.log10(Y / X))
