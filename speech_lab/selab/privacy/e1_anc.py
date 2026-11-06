"""E1: outward feedforward ANC of a talker's voice (free field, monopoles).
Causal multichannel FIR controller designed by speech-weighted time-domain least squares
to minimise the talker's pressure on a ring of 'eavesdropper' control points (r=2.5 m),
with a hard system latency D (controller taps start at D samples). Reference = the talker's
own close-talk mic (ideal, no acoustic lead), so ANY latency must be absorbed by prediction (E2).
Evaluates attenuation per octave band at held-out eavesdropper points (2/3/5 m), at the talker's
own ear and the partner's ear (spillover), and a spatial map.
Run: nice -n 19 env OMP_NUM_THREADS=1 python -m selab.privacy.e1_anc
"""
import numpy as np, json, sys
from scipy.signal import firwin2
from .common_p import FS, C, BANDS, BAND_NAMES, OUT, concat_speaker, speakers, ltass, save_json, load_json

NS = 64           # fractional-delay sinc half length
NTAP = 192        # controller taps per channel (12 ms)
MOUTH = np.array([-0.45, 0.0, 1.20])
PARTNER_EAR = np.array([0.45, 0.07, 1.25])
OWN_EAR = np.array([-0.45, 0.08, 1.25])


def fd_ir(src, rcv, T):
    r = np.linalg.norm(rcv - src); tau = r / C * FS
    n = np.arange(T); g = np.sinc(n - tau) * np.where(np.abs(n - tau) < NS, 0.5 + 0.5 * np.cos(np.pi * (n - tau) / NS), 0)
    return g / (4 * np.pi * r)


def ring(r, naz, z, off=0.0, ctr=(0, 0)):
    a = np.arange(naz) / naz * 2 * np.pi + off
    return np.stack([ctr[0] + r * np.cos(a), ctr[1] + r * np.sin(a), np.full(naz, z)], 1)


def configs():
    m = MOUTH
    return {
        "table_ring8": ring(0.30, 8, 0.78),
        "collar4": np.array([m + [0, 0.07, 0], m + [0, -0.07, 0], m + [0.06, 0, -0.06], m + [0, 0, -0.09]]),
        "single_mouth5cm": np.array([m + [0.04, 0, -0.03]]),
    }


def weight_fir():
    x = concat_speaker(speakers()[0], 60)
    f, P = ltass(x)
    mag = np.sqrt(P / P.max()); mag[0] = 0; mag[-1] = 0
    return firwin2(129, f / (FS / 2), mag)


def design(spk, ctrl_pts, D, h, bright=None, wb=10.0, beta_rel=1e-4):
    T = int(6.0 / C * FS) + 2 * NS + len(h) + 10
    L = len(spk); n = NTAP
    R = np.zeros((L * n, L * n)); b = np.zeros(L * n)
    pts = [(p, 1.0, False) for p in ctrl_pts] + ([(p, wb, True) for p in bright] if bright is not None else [])
    for p, wgt, is_b in pts:
        g = [np.convolve(h, fd_ir(s, p, T))[:T] * wgt for s in spk]
        q = np.zeros(T) if is_b else np.convolve(h, fd_ir(MOUTH, p, T))[:T] * wgt
        for l in range(L):
            cb = np.correlate(q, g[l], "full")[T - 1:]   # cb[a] = sum_u g_l[u] q[u+a]
            b[l * n:(l + 1) * n] -= cb[D:D + n]
            for l2 in range(l, L):
                c = np.correlate(g[l2], g[l], "full")   # c[tau+T-1] = sum_u g_l[u] g_l2[u+tau]
                idx = (np.arange(n)[:, None] - np.arange(n)[None, :])  # a-b with a=D+k (l), b=D+k' (l2)
                # R[(l,k),(l2,k')] = sum_u g_l[u-?]... = c_{l l2}(k'-k) per derivation: sum_n g_l[n-a] g_l2[n-b] = c(a-b)?
                blk = c[idx + T - 1]
                R[l * n:(l + 1) * n, l2 * n:(l2 + 1) * n] += blk
                if l2 != l:
                    R[l2 * n:(l2 + 1) * n, l * n:(l + 1) * n] += blk.T
    beta = beta_rel * np.trace(R) / len(R)
    w = np.linalg.solve(R + beta * np.eye(len(R)), b)
    return w.reshape(L, n)


FREQ = np.arange(60, 7900, 10.0)


def tf(src, rcv):
    r = np.linalg.norm(rcv - src)
    return np.exp(-2j * np.pi * FREQ * r / C) / (4 * np.pi * r)


def residual(spk, w, D, p):
    k = np.arange(w.shape[1]) + D
    W = np.exp(-2j * np.pi * FREQ[:, None] * k[None, :] / FS) @ w.T   # F x L
    S = np.stack([tf(s, p) for s in spk], 1)
    P = tf(MOUTH, p)
    return P, P + (S * W).sum(1)


def band_atten(P, E, Lw):
    out = []
    for lo, hi in BANDS + [(125, 7900)]:
        m = (FREQ >= lo) & (FREQ < hi)
        out.append(10 * np.log10((np.abs(E[m]) ** 2 * Lw[m]).sum() / (np.abs(P[m]) ** 2 * Lw[m]).sum()))
    return out


def main():
    res = load_json("e1_results.json") or {}
    h = weight_fir()
    Lw = np.abs(np.exp(-2j * np.pi * FREQ[:, None] * np.arange(len(h))[None, :] / FS) @ h) ** 2
    ctrl = np.concatenate([ring(2.5, 24, 1.2), ring(2.5, 24, 1.6, off=np.pi / 24)])
    val = {r: ring(r, 16, 1.4, off=np.pi / 16) for r in (2.0, 3.0, 5.0)}
    for cname, spk in configs().items():
        for bright in (False, True):
            for Dms in (0.0, 0.5, 1.0, 2.0, 5.0):
                key = f"{cname}|{'preserve_partner' if bright else 'free'}|D{Dms}"
                if key in res:
                    continue
                D = int(round(Dms * FS / 1000))
                w = design(spk, ctrl, D, h, bright=[PARTNER_EAR] if bright else None)
                row = {"bands": BAND_NAMES + ["speech_wtd"]}
                for r, pts in val.items():
                    A = np.array([band_atten(*residual(spk, w, D, p), Lw) for p in pts])
                    # energy-average over azimuths, and worst azimuth
                    row[f"eaves_{r}m_mean"] = (10 * np.log10(np.mean(10 ** (A / 10), 0))).round(2).tolist()
                    row[f"eaves_{r}m_worst"] = A.max(0).round(2).tolist()
                    row[f"eaves_{r}m_best"] = A.min(0).round(2).tolist()
                row["partner_ear"] = np.round(band_atten(*residual(spk, w, D, PARTNER_EAR), Lw), 2).tolist()
                row["own_ear"] = np.round(band_atten(*residual(spk, w, D, OWN_EAR), Lw), 2).tolist()
                row["effort_rel"] = float(np.sum(w ** 2))
                res[key] = row
                save_json(res, "e1_results.json")
                print(key, "3m mean", row["eaves_3.0m_mean"], "partner", row["partner_ear"], flush=True)
    # spatial map for two cases
    mp = load_json("e1_map.json") or {}
    xs = np.arange(-5, 5.01, 0.25)
    for cname, Dms in (("collar4", 0.0), ("collar4", 1.0), ("table_ring8", 0.0)):
        key = f"{cname}|D{Dms}"
        if key in mp:
            continue
        spk = configs()[cname]; D = int(round(Dms * FS / 1000))
        w = design(spk, ctrl, D, h)
        grid = np.zeros((len(xs), len(xs), 3))
        for i, x in enumerate(xs):
            for j, y in enumerate(xs):
                p = np.array([x, y, 1.2])
                if np.linalg.norm(p - MOUTH) < 0.12:
                    grid[i, j] = np.nan; continue
                a = band_atten(*residual(spk, w, D, p), Lw)
                grid[i, j] = [a[1], a[3], a[6]]
        mp[key] = {"xs": xs.tolist(), "b250_500": grid[..., 0].tolist(), "b1k_2k": grid[..., 1].tolist(), "speech": grid[..., 2].tolist()}
        save_json(mp, "e1_map.json"); print("map", key, flush=True)


if __name__ == "__main__":
    main()
