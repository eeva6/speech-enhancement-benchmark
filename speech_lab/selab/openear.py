"""Round 4: 'hear your friend in a loud bar' simulation across form factors.

Physics model
-------------
A listener sits at a table in a reverberant bar (RT60 ~0.7 s). A friend talks from 1.0 m across the table.
Noise = 8 point-source babble talkers at 1.6-5 m + 2 far loudspeakers playing recorded crowd babble
(MS-SNSD) to make the field partly diffuse. Everything is simulated with pyroomacoustics (image method),
so we know each component exactly at every microphone and at the listener's ear.

What reaches the eardrum (no head model, free-field ear position = limitation):
    open delivery      ear = direct_ear + g * delay(device_out, D)
    occluded (in-ear)  ear = a * direct_ear + g * delay(device_out, D)      (a = passive+ANC isolation)
The device can only ADD sound for open delivery; the direct noise is still there.  D = algorithmic +
converter (1 ms) + wireless / propagation delay.  g is set so the device's TARGET level at the ear is
`gain_db` above the direct target level.

Capture geometries (listener head at origin, facing +x; mic coordinates in metres):
    glasses   6 mics on a frame (front hinges, bridge-ish, temples)
    neckband  6 mics on a U around the neck, 20 cm below ear level
    tabletop  8-mic ring (r = 5 cm) at the table centre, 0.5 m in front of the listener
    remote    1 mic on the friend's chest / a phone right in front of the friend (streamed)
    ear_amp   1 mic at the ear, no beamforming (a plain 'sound amplifier')
Processing: fixed superdirective (diffuse-noise MVDR, diagonal loading) beamformer steered to the friend
with near-field steering, realised as a causal FIR (latency = N/2), optionally followed by the streaming
Wiener post-filter (8 ms).  Plus an IDEAL device that emits the clean friend signal (physics ceiling) and
an offline TSE proxy (hypothetical future causal TSE, labelled as such).

Metrics: ESTOI vs the friend's early (direct + 50 ms) image at the ear, and the 'equivalent SNR benefit':
the change in unaided input SNR that would give the same ESTOI (per-scene psychometric curve), which is
directly comparable to the dB benefits reported for hearing devices.
"""
import json, sys, glob, time, argparse
from pathlib import Path
import numpy as np
import pandas as pd
import pyroomacoustics as pra
from scipy.signal import fftconvolve
from pystoi import stoi
from .common import FS, DATA, RES, MIX, load, save, rms, match_len

C = 343.0
OUTD = RES / "r4"
EAR = np.array([0.0, 0.075, 0.0])  # left ear relative to head centre

GEOM = {
    "glasses": np.array([[0.09, 0.07, 0.03], [0.09, -0.07, 0.03], [0.095, 0.025, 0.035],
                         [0.095, -0.025, 0.035], [0.04, 0.078, 0.03], [0.04, -0.078, 0.03]]),
    "neckband": np.array([[0.1 * np.cos(a), 0.1 * np.sin(a), -0.2] for a in np.deg2rad([-90, -45, -15, 15, 45, 90])]),
    "ear_amp": EAR[None] + np.array([[0.005, 0.0, 0.0]]),
}


def tabletop_geom():
    c = np.array([0.5, 0.0, -0.45])  # table centre: 0.5 m ahead, 45 cm below ear level
    return np.array([c + 0.05 * np.array([np.cos(a), np.sin(a), 0]) for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)])


GEOM["tabletop"] = tabletop_geom()
FRIEND = np.array([1.0, 0.0, 0.0])
GEOM["remote"] = (FRIEND + np.array([-0.15, 0.0, -0.3]))[None]


def speech_pool():
    tgt = sorted(glob.glob(str(DATA / "arctic/cmu_us_{awb,clb,ksp,slt}_arctic/wav/*.wav")))
    tgt = [p for s in ["awb", "clb", "ksp", "slt"] for p in sorted(glob.glob(str(DATA / f"arctic/cmu_us_{s}_arctic/wav/*.wav")))]
    itf = sorted(glob.glob(str(DATA / "LibriSpeech/dev-clean-2/*/*/*.flac")))
    itf += [p for s in ["bdl", "jmk", "rms", "aew"] for p in sorted(glob.glob(str(DATA / f"arctic/cmu_us_{s}_arctic/wav/*.wav")))]
    bab = sorted(glob.glob(str(DATA / "mssnsd/noise_test/Babble*.wav")))
    return tgt, itf, bab


def long_speech(rng, pool, n):
    out = []
    while sum(len(x) for x in out) < n:
        x = load(pool[rng.integers(len(pool))]); out.append(x / (rms(x) + 1e-9)); out.append(np.zeros(int(0.1 * FS)))
    return np.concatenate(out)[:n].astype(np.float32)


def build_scene(rng, tgt, itf, bab):
    s = load(tgt[rng.integers(len(tgt))]); s = s / rms(s)
    s = np.concatenate([np.zeros(int(0.3 * FS)), s, np.zeros(int(0.3 * FS))]).astype(np.float32)
    n = len(s)
    dims = np.array([rng.uniform(10, 14), rng.uniform(8, 11), 3.5])
    rt60 = rng.uniform(0.55, 0.85)
    e_abs, mo = pra.inverse_sabine(rt60, dims)
    room = pra.ShoeBox(dims, fs=FS, materials=pra.Material(e_abs), max_order=min(mo, 14), use_rand_ism=True,
                       max_rand_disp=0.05)
    head = np.array([rng.uniform(4, dims[0] - 5), rng.uniform(3.5, dims[1] - 3.5), 1.2])
    srcs = [(head + FRIEND, s)]
    for k in range(8):
        az = rng.uniform(0, 2 * np.pi); r = rng.uniform(1.6, 5.0)
        p = head + np.array([r * np.cos(az), r * np.sin(az), rng.uniform(0.0, 0.4)])
        p = np.clip(p, [0.3, 0.3, 0.5], dims - 0.3)
        srcs.append((p, long_speech(rng, itf, n) * 10 ** (rng.uniform(-3, 3) / 20)))
    for corner in ([0.5, 0.5, 2.8], [dims[0] - 0.5, dims[1] - 0.5, 2.8]):
        b = load(bab[rng.integers(len(bab))]); st = rng.integers(max(1, len(b) - n))
        b = match_len(b[st:], n); srcs.append((np.array(corner), 1.5 * b / (rms(b) + 1e-9)))
    mics = {k: head[None] + v for k, v in GEOM.items()}
    mics["ear"] = (head + EAR)[None]
    order = list(mics)
    allm = np.concatenate([mics[k] for k in order]).T
    for p, sig in srcs:
        room.add_source(p, signal=sig)
    room.add_microphone_array(allm)
    room.compute_rir()
    M = allm.shape[1]
    T = np.zeros((M, n), np.float32); N = np.zeros((M, n), np.float32)
    for m in range(M):
        for k in range(len(srcs)):
            y = fftconvolve(srcs[k][1], room.rir[m][k])[:n]
            if k == 0: T[m] = y
            else: N[m] += y
    # early (direct + 50 ms) target at ear = scoring reference
    me = M - 1; h = room.rir[me][0]; d = int(np.argmax(np.abs(h)))
    early = fftconvolve(s, h[: d + int(0.05 * FS)])[:n].astype(np.float32)
    idx, i = {}, 0
    for k in order:
        idx[k] = slice(i, i + len(mics[k])); i += len(mics[k])
    return dict(T=T, N=N, early=early, idx=idx, rt60=rt60, n=n)


def sd_fir(mic_pos, src_pos, Nfir=128, mu=0.05):
    """Superdirective (diffuse-noise MVDR) FIR, near-field steering to src_pos; returns (M, Nfir) causal filters."""
    M = len(mic_pos)
    if M == 1:
        h = np.zeros((1, Nfir)); h[0, Nfir // 2] = 1.0; return h
    f = np.fft.rfftfreq(Nfir, 1 / FS)
    r = np.linalg.norm(mic_pos - src_pos[None], axis=1)
    dij = np.linalg.norm(mic_pos[:, None] - mic_pos[None], axis=2)
    W = np.zeros((len(f), M), complex)
    for k, fk in enumerate(f):
        d = np.exp(-2j * np.pi * fk * (r - r[0]) / C) * (r[0] / r)
        G = np.sinc(2 * fk * dij / C) + mu * np.eye(M)
        Gi = np.linalg.solve(G, d)
        W[k] = Gi / (d.conj() @ Gi)
    h = np.fft.irfft(W.conj(), Nfir, axis=0).T  # (M, Nfir), y = sum_m h_m * x_m
    h = np.roll(h, Nfir // 2, axis=1) * np.hanning(Nfir + 2)[1:-1][None]
    return h


def apply_fir(h, X):
    return np.sum([fftconvolve(X[m], h[m])[: X.shape[1]] for m in range(len(h))], axis=0).astype(np.float32)


def delay(x, D):
    D = int(round(D))
    return np.concatenate([np.zeros(D, np.float32), x[: len(x) - D]]) if D > 0 else x


def estoi(ref, x):
    return float(stoi(ref, x, FS, extended=True))


def equiv_curve(sc, snrs=np.arange(-25, 25.1, 2.5)):
    """Unaided ESTOI at the ear as a function of input SNR (noise rescaled); used to map ESTOI -> dB."""
    t, nn, e = sc["T"][-1], sc["N"][-1], sc["early"]
    base = 20 * np.log10(rms(t) / rms(nn))
    vals = []
    for s in snrs:
        vals.append(estoi(e, t + nn * 10 ** ((base - s) / 20)))
    return snrs, np.maximum.accumulate(np.array(vals))


def to_equiv(snrs, curve, v):
    if v <= curve[0]: return float(snrs[0])
    if v >= curve[-1]: return float(snrs[-1])
    return float(np.interp(v, curve + 1e-9 * np.arange(len(curve)), snrs))


def run(nscenes=20, snrs_in=(-5, 0), seed=7, tse=False, out=OUTD, tag='', start=0):
    from .streaming import StreamWiener, stream_run
    out.mkdir(parents=True, exist_ok=True)
    tgt, itf, bab = speech_pool()
    rows = []
    firs = {}
    for g in ["glasses", "neckband", "tabletop", "remote", "ear_amp"]:
        for Nf in (64, 256):
            firs[(g, Nf)] = sd_fir(GEOM[g], FRIEND, Nf)
    configs = []
    # (name, geometry, Nfir, postfilter, delivery, extra_delay_ms)
    for g in ["glasses", "neckband", "tabletop", "ear_amp"]:
        configs.append((f"{g}_sd2ms", g, 64, False))
        configs.append((f"{g}_sd8ms", g, 256, False))
        configs.append((f"{g}_sd2ms_pf", g, 64, True))
    configs.append(("remote_mic", "remote", 64, False))
    configs.append(("remote_mic_pf", "remote", 64, True))
    extra = {"glasses": [1, 4, 8, 15, 30], "neckband": [1, 4, 8, 15, 30], "ear_amp": [1, 4, 8, 15],
             "tabletop": [2.5, 5, 10, 20, 30], "remote": [5, 10, 20, 30, 50]}
    gains = [0, 10, 20]
    t0 = time.time()
    for si in range(start, start + nscenes):
        rng = np.random.default_rng(seed * 1000 + si)
        sc0 = build_scene(rng, tgt, itf, bab)
        for snr in snrs_in:
            sc = dict(sc0)
            t_ear, n_ear = sc0["T"][-1], sc0["N"][-1]
            k = rms(t_ear) / rms(n_ear) / 10 ** (snr / 20)
            sc["N"] = sc0["N"] * k
            e = sc["early"]; mix_ear = t_ear + sc["N"][-1]
            snrs, curve = equiv_curve(sc)
            base_estoi = estoi(e, mix_ear)
            base_eq = to_equiv(snrs, curve, base_estoi)
            rows.append(dict(scene=si, snr_in=snr, config="unaided", geom="-", delivery="-", D_ms=0, gain_db=0,
                             estoi=base_estoi, eq_snr=base_eq, benefit_db=0.0, snr_dev_db=np.nan, rt60=sc["rt60"]))
            # in-ear isolation reference: 25 dB passive+ANC, no device signal except pass-through of ear mic
            outs = {}
            for name, g, Nf, pf in configs:
                X_t, X_n = sc0["T"][sc0["idx"][g]], sc["N"][sc0["idx"][g]]
                h = firs[(g, Nf)]
                yt, yn = apply_fir(h, X_t), apply_fir(h, X_n)
                lat = Nf / 2 / FS * 1000
                if pf:
                    y_mix = yt + yn
                    p = StreamWiener(8); y, _ = stream_run(p, y_mix, p.H)
                    lat += 8.0
                    outs[name] = (g, None, None, y, lat)
                else:
                    outs[name] = (g, yt, yn, yt + yn, lat)
            # ideal device: emits the clean friend signal at the ear (physics ceiling for open delivery)
            outs["ideal_clean"] = ("ideal", t_ear, np.zeros_like(t_ear), t_ear.copy(), 0.0)
            for name, (g, yt, yn, y, lat) in outs.items():
                # remove FIR bulk delay so 'lat' is the only extra delay applied
                Nf = 0 if g == "ideal" else ([c for c in configs if c[0] == name][0][2])
                if Nf:
                    y = np.concatenate([y[Nf // 2:], np.zeros(Nf // 2, np.float32)])
                    if yt is not None:
                        yt = np.concatenate([yt[Nf // 2:], np.zeros(Nf // 2, np.float32)])
                # target level of device output (estimate from linear part, else from projection)
                if yt is None:
                    a = float(np.dot(y, t_ear) / (np.dot(t_ear, t_ear) + 1e-9)); tl = abs(a) * rms(t_ear)
                    snr_dev = np.nan
                else:
                    tl = rms(yt); snr_dev = 20 * np.log10(rms(yt) / (rms(y - yt) + 1e-9))
                dlist = extra.get(g, [1, 4, 8, 15, 30])
                combos = [(Dx, 10) for Dx in dlist] + [(dlist[0], gd) for gd in gains if gd != 10]
                for Dx, gd in combos:
                    Dtot = lat + Dx if g != "ideal" else Dx
                    if True:
                        gl = rms(t_ear) * 10 ** (gd / 20) / (tl + 1e-9)
                        dev = delay(y * gl, Dtot * FS / 1000)
                        for deliv, att in (("open", 1.0), ("in_ear", 10 ** (-25 / 20))):
                            if deliv == "in_ear" and gd != 10:
                                continue
                            ear = att * mix_ear + dev
                            ref = e
                            v = estoi(ref, ear)
                            eq = to_equiv(snrs, curve, v)
                            rows.append(dict(scene=si, snr_in=snr, config=name, geom=g, delivery=deliv,
                                             D_ms=round(Dtot, 2), gain_db=gd, estoi=v, eq_snr=eq,
                                             benefit_db=eq - base_eq, snr_dev_db=snr_dev, rt60=sc["rt60"]))
            if si < 2 and start == 0:  # keep audio examples
                ad = out / "audio" / f"scene{si}_snr{snr}"
                ad.mkdir(parents=True, exist_ok=True)
                save(ad / "00_unaided_at_ear.wav", mix_ear)
                save(ad / "01_friend_clean_at_ear.wav", e)
                for name in ["glasses_sd2ms", "neckband_sd2ms", "tabletop_sd2ms", "remote_mic"]:
                    g, yt, yn, y, lat = outs[name]
                    Nf = [c for c in configs if c[0] == name][0][2]
                    y = np.concatenate([y[Nf // 2:], np.zeros(Nf // 2, np.float32)])
                    tl = rms(yt[Nf // 2:]) if yt is not None else rms(y)
                    Dx = 1 if g in ("glasses", "neckband") else (2.5 if g == "tabletop" else 20)
                    gl = rms(t_ear) * 10 ** (10 / 20) / (tl + 1e-9)
                    save(ad / f"{name}_device_only.wav", y * gl)
                    save(ad / f"{name}_open_ear_mix_+10dB.wav", mix_ear + delay(y * gl, (lat + Dx) * FS / 1000))
        print(f"scene {si} done {time.time() - t0:.0f}s", flush=True)
        pd.DataFrame(rows).to_csv(out / f"openear_raw{tag}.csv", index=False)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=20); ap.add_argument("--seed", type=int, default=7); ap.add_argument("--tag", default="")
    ap.add_argument("--start", type=int, default=0)
    a = ap.parse_args()
    run(a.n, seed=a.seed, tag=a.tag or f"_{a.start:03d}", start=a.start)
