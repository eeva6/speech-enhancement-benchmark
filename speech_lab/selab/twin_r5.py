"""Round 5 simulated TWIN of every real LibriCSS item (for a paired sim-vs-real comparison).

Same dry loudspeaker feeds, same timing/overlap, same 7-mic geometry, same azimuths (system-identification
reference), with the room replaced by a pyroomacoustics image-method shoebox whose parameters are fitted to the
real recordings:
  * RT60: median T20 of the system-identified target RIRs at mic 0 (noise-floor-limited estimate; see report)
  * per-loudspeaker distance: chosen so the simulated direct-to-reverberant ratio (DRR) at mic 0 matches the DRR
    of that loudspeaker's identified RIR (distance clipped to the corpus range 0.33-4.09 m)
  * background noise: the REAL 7-channel room noise from the first ~2.5 s of the same recording (before the
    first utterance), at its real level relative to the speech
  * room size 6.5 x 5 x 3 m, array at 0.75 m height near the centre: ASSUMED (not published)
What the twin keeps: geometry, overlap, levels, noise.  What it changes: the room (shoebox, frequency-flat
absorption, omnidirectional point sources, no loudspeaker directivity, no furniture).
python -m selab.twin_r5          (two passes: stats cache, then simulation; resumable)
"""
import json
import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve
from .common import MIX, FS, save
from . import libricss as L

ROOM = np.array([6.5, 5.0, 3.0]); ARR = np.array([3.1, 2.4, 0.75])


def drr(h, pk):
    w = int(0.0025 * FS)
    d = np.sum(h[max(pk - w, 0):pk + w] ** 2); r = np.sum(h[pk + w:] ** 2)
    return float(10 * np.log10(d / (r + 1e-12)))


def t20(h, pk):
    e = np.cumsum(h[pk:][::-1] ** 2)[::-1]; e = 10 * np.log10(e / e[0] + 1e-12)
    i5, i25 = np.argmax(e < -5), np.argmax(e < -25)
    return float(3 * (i25 - i5) / FS) if i25 > i5 else float("nan")


def t60_env(h, pk, t0=0.02, t1=0.15):
    """RT60 from the slope of the 10-ms energy envelope 20-150 ms after the direct path. The Schroeder T20 is
    biased long here because the LS-estimated RIR has an error floor ~35-45 dB down (checked by hand on one item)."""
    w = 160
    env = np.array([10 * np.log10(np.sum(h[pk + i:pk + i + w] ** 2) + 1e-20) for i in range(int(t0 * FS), int(t1 * FS), w)])
    t = (np.arange(len(env)) * w) / FS
    sl = np.polyfit(t, env, 1)[0]
    return float(-60 / sl) if sl < 0 else float("nan")


def rt60_calibration(meta):
    """median envelope-slope RT60 over one target RIR per recording (24 recordings)."""
    S = _sess_cache(); seen = set(); vals = []
    for m in meta:
        key = (m["cond"], m["session"])
        if key in seen:
            continue
        seen.add(key); d = S[key]
        info = L.read_info(d); A = np.array(m["clock"]); u = next(v for v in info if v["uid"] == m["uid"])
        lag = np.polyval(A, (u["start"] + u["end"]) / 2); a = u["start"] + lag / FS
        t0, t1 = max(a - 30, 3.0), a + m["dur"] + 30
        y, x, b0 = L.read_win(d, t0, t1)
        ro = L.sysid(y, x, t0 - b0, min(t1 - b0, len(x) / FS - 1.5), L.shift_clock(A, b0))
        if ro is None:
            continue
        Hh = ro[0]
        h = np.fft.irfft(Hh[:, :, m["ch"]], axis=0)[:, 0]
        vals.append(t60_env(h, int(np.argmax(np.abs(h)))))
        print("rt60", key, round(vals[-1], 3), flush=True)
    return vals


def quiet_noise(d, dur=1.5):
    """Quietest 1.5 s of the first 3 s of the recording (the files open with a ~1 s loud segment before the
    room goes quiet; the first utterance starts at 3.0 s)."""
    y = sf.read(d + "/record/raw_recording.wav", dtype="float32", start=0, stop=3 * FS)[0]
    n = int(dur * FS); best, bi = np.inf, 0
    for i in range(0, len(y) - n, FS // 10):
        e = np.mean(y[i:i + n, 0] ** 2)
        if e < best:
            best, bi = e, i
    return y[bi:bi + n]


def _sess_cache():
    S = {}
    for c, s, d in L.sessions():
        S[(c, s)] = d
    return S


def stats_pass(meta):
    cp = MIX / "r5sim" / "twin_stats.json"
    st = json.load(open(cp)) if cp.exists() else {}
    S = _sess_cache(); cur = None
    for m in meta:
        if m["id"] in st and "base" in st[m["id"]]:
            continue
        d = S[(m["cond"], m["session"])]
        info = L.read_info(d); A = np.array(m["clock"])
        u = next(v for v in info if v["uid"] == m["uid"])
        lag = np.polyval(A, (u["start"] + u["end"]) / 2)
        a, b = int(u["start"] * FS + lag), int(u["end"] * FS + lag)
        y, x, b0 = L.read_win(d, a / FS - 12, b / FS + 12, margin=3.0)
        B = int(round(b0 * FS))
        Hh, res, sh = L.sysid(y, x, a / FS - 12 - b0, b / FS + 12 - b0, L.shift_clock(A, b0))
        u = dict(u); u["start"] = u["start"] - b0   # window-relative playback time from here on
        chans = {}
        n = int(round(m["dur"] * FS))
        ht = np.fft.irfft(Hh[:, :, m["ch"]], axis=0)
        ra = int(u["start"] * FS) + sh + int(np.argmax(np.abs(ht[:, 0])))   # same segment start as the real item
        for k in range(x.shape[1]):
            h = np.fft.irfft(Hh[:, :, k], axis=0)
            if not np.any(h):
                continue
            pk = int(np.argmax(np.abs(h[:, 0])))
            az, fr = L.fit_az(L.direct_tdoa(h))
            src = x[ra - sh - 2 * L.NS: ra - sh + n, k]
            img = np.convolve(src, h[:, 0])[2 * L.NS: 2 * L.NS + n]
            chans[k] = dict(drr=drr(h[:, 0], pk), t20=t20(h[:, 0], pk), az=az, fit_us=fr, pk=pk,
                            img_rms=float(np.sqrt(np.mean(img ** 2))))
        st[m["id"]] = dict(sh=int(sh), chans=chans, base=B)
        json.dump(st, open(cp, "w"))
        print("stats", m["id"], {k: round(v["drr"], 1) for k, v in chans.items()}, flush=True)
    return st


def make_room(rt60, src_pos):
    import pyroomacoustics as pra
    e_abs, max_order = pra.inverse_sabine(rt60, ROOM)
    room = pra.ShoeBox(ROOM, fs=FS, materials=pra.Material(e_abs), max_order=min(max_order, 40), air_absorption=False)
    xy = np.asarray(L.MIC_XY)
    mics = np.vstack([xy.T + ARR[:2, None], np.full((1, 7), ARR[2])])
    room.add_microphone_array(mics)
    for p in src_pos:
        room.add_source(p)
    room.compute_rir()
    return room


def pos(az, dist):
    p = ARR + dist * np.array([np.cos(np.deg2rad(az)), np.sin(np.deg2rad(az)), 0.0])
    return np.clip(p, 0.2, ROOM - 0.2)


def drr_table(rt60):
    """DRR at mic 0 vs source distance in the twin room (averaged over 8 azimuths)."""
    ds = np.array([0.33, 0.5, 0.75, 1.0, 1.4, 1.8, 2.2, 2.6, 3.0])
    out = []
    for dd in ds:
        v = []
        for az in range(0, 360, 45):
            r = make_room(rt60, [pos(az, dd)]); h = r.rir[0][0]
            v.append(drr(h, int(np.argmax(np.abs(h)))))
        out.append(np.mean(v))
    return ds, np.array(out)


def main():
    meta = json.load(open(MIX / "r5" / "meta.json"))
    (MIX / "r5sim").mkdir(parents=True, exist_ok=True)
    st = stats_pass(meta)
    dref = json.load(open(MIX / "r5" / "doa_ref.json"))
    t = [st[m["id"]]["chans"][str(m["ch"])]["t20"] for m in meta if str(m["ch"]) in st[m["id"]]["chans"]]
    pp = MIX / "r5sim" / "room.json"
    if pp.exists():
        room_p = json.load(open(pp))
    else:
        tv = rt60_calibration(meta)
        rt60 = float(np.clip(np.nanmedian(tv), 0.2, 1.2))
        ds, dr = drr_table(rt60)
        room_p = dict(rt60=rt60, rt60_env_per_recording=tv, rt60_env_iqr=[float(v) for v in np.nanpercentile(tv, [25, 75])],
                      schroeder_t20_median_biased=float(np.nanmedian(t)),
                      room=ROOM.tolist(), array=ARR.tolist(), drr_dist=ds.tolist(), drr_db=dr.tolist())
        json.dump(room_p, open(pp, "w"), indent=1)
    ds, dr = np.array(room_p["drr_dist"]), np.array(room_p["drr_db"])
    dist_of = lambda v: float(np.clip(np.interp(-v, -dr, ds), 0.33, 4.09))   # dr decreasing with distance
    mp = MIX / "r5sim" / "meta.json"
    out = json.load(open(mp)) if mp.exists() else []
    done = {m["id"] for m in out}
    S = _sess_cache(); cur = None
    for m in meta:
        if m["id"] in done:
            continue
        d = S[(m["cond"], m["session"])]
        info = L.read_info(d)
        s = st[m["id"]]; sh = s["sh"]
        if "base" not in s:
            continue   # stats from an older (whole-file) pass: recompute
        B = s["base"]
        x = sf.read(d + "/clean/each_spk.wav", dtype="float32", start=B, stop=B + int((m["dur"] + 40) * FS))[0]
        ynoise = quiet_noise(d)
        dm = MIX / "r5" / m["id"]
        n = int(round(m["dur"] * FS))
        pk_t = s["chans"][str(m["ch"])]["pk"]
        ra = None
        # recover the segment start on the recording: segment = recording[ra:ra+n] with ra = a_play + sh + pk
        u = next(v for v in info if v["uid"] == m["uid"])
        a_play = int(u["start"] * FS) - B
        ra = a_play + sh + pk_t
        ctx = 3 * FS                                     # 3 s of preceding context so earlier tails are present
        chans, srcs, sigs = [], [], []
        for k, c in s["chans"].items():
            az = dref.get(f'{m["session"]}_{k}', c["az"]) if c["fit_us"] < 25 or f'{m["session"]}_{k}' in dref else c["az"]
            # dry feed aligned with this loudspeaker's REAL direct-path delay (keeps the real relative timing)
            sig = x[ra - sh - c["pk"] - ctx: ra - sh - c["pk"] + n, int(k)]
            if len(sig) < ctx + n or not np.any(sig[ctx:]) or c["img_rms"] <= 0:
                continue
            chans.append(int(k)); srcs.append(pos(az, dist_of(c["drr"]))); sigs.append(sig)
        room = make_room(room_p["rt60"], srcs)
        imgs = []
        for j, sig in enumerate(sigs):
            hs = [room.rir[mi][j] for mi in range(7)]
            d0 = int(np.argmax(np.abs(hs[0])))
            imgs.append(np.stack([fftconvolve(sig, h)[ctx + d0: ctx + d0 + n] for h in hs]))
        imgs = np.stack(imgs)                            # (S,7,n)
        jt = chans.index(m["ch"])
        # level match per loudspeaker: each simulated image at mic 0 gets the RMS of its real identified image
        gs = np.array([s["chans"][str(k)]["img_rms"] / (np.sqrt(np.mean(imgs[j, 0] ** 2)) + 1e-12) for j, k in enumerate(chans)])
        imgs = imgs * gs[:, None, None]; g = gs[jt]
        speech = imgs.sum(0)
        noise = ynoise.T
        reps = int(np.ceil(n / noise.shape[1]))
        noise = np.tile(noise, (1, reps))[:, :n]
        mix = speech + noise
        dd = MIX / "r5sim" / m["id"]; dd.mkdir(parents=True, exist_ok=True)
        sf.write(dd / "mix_mc.wav", mix.T, FS, subtype="FLOAT")
        save(dd / "mix.wav", mix[0]); save(dd / "ref.wav", imgs[jt, 0])
        # enrolment: same loudspeaker, enrolment span, simulated alone in the twin room (+ real noise)
        e = next(v for v in info if v["uid"] == m["enrol_uid"])
        es = sf.read(d + "/clean/each_spk.wav", dtype="float32", start=int(e["start"] * FS), stop=int(min(e["end"], e["start"] + 15) * FS))[0][:, m["ch"]]
        he = room.rir[0][jt]
        en = g * fftconvolve(es, he)[:len(es)] + np.tile(noise[0], int(np.ceil(len(es) / n)) + 1)[:len(es)]
        save(dd / "enrol.wav", en)
        mm = dict(m); mm.update(az_sysid=float(dref.get(f'{m["session"]}_{m["ch"]}', m["az_sysid"])),
                                twin_dist=[round(float(np.linalg.norm(p[:2] - ARR[:2])), 2) for p in srcs], twin_chans=chans,
                                sir_db=float(10 * np.log10(np.sum(imgs[jt, 0] ** 2) / (np.sum((mix[0] - imgs[jt, 0]) ** 2) + 1e-12))))
        out.append(mm); done.add(m["id"])
        json.dump(out, open(mp, "w"), indent=1)
        print("twin", m["id"], f"sir={mm['sir_db']:.1f}", mm["twin_dist"], flush=True)
    json.dump(dref, open(MIX / "r5sim" / "doa_ref.json", "w"))


if __name__ == "__main__":
    main()
