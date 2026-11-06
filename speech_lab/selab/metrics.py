"""Objective metrics. SI-SDR is implemented here (Le Roux et al. 2019); STOI/ESTOI via pystoi;
PESQ-WB via the `pesq` wrapper of ITU-T P.862.2 reference code (research use only)."""
import numpy as np
from .common import FS


def si_sdr(ref, est):
    n = min(len(ref), len(est))
    r, e = ref[:n] - ref[:n].mean(), est[:n] - est[:n].mean()
    a = np.dot(e, r) / (np.dot(r, r) + 1e-12)
    t = a * r
    return float(10 * np.log10(np.dot(t, t) / (np.dot(e - t, e - t) + 1e-12) + 1e-12))


def stoi(ref, est, extended=False):
    from pystoi import stoi as _s
    n = min(len(ref), len(est))
    return float(_s(ref[:n], est[:n], FS, extended=extended))


def pesq_wb(ref, est):
    try:
        from pesq import pesq
        n = min(len(ref), len(est))
        return float(pesq(FS, ref[:n].astype(np.float64), est[:n].astype(np.float64), "wb"))
    except Exception as e:  # e.g. NoUtterancesError on silent output
        return float("nan")


def all_metrics(ref, est, mix=None):
    m = dict(si_sdr=si_sdr(ref, est), stoi=stoi(ref, est), estoi=stoi(ref, est, True), pesq=pesq_wb(ref, est))
    if mix is not None:
        m["si_sdri"] = m["si_sdr"] - si_sdr(ref, mix)
    return m
