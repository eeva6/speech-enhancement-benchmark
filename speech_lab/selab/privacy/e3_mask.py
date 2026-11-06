"""E3: AI-adaptive masking for a 'privacy bubble' table device (room simulation).
Room 14x12x3.2 m, RT60 0.5 s (pyroomacoustics ISM). Talker A and partner B at a table; masker
emitted from a table-centre device (co-located with talkers -> eavesdropper cannot separate it spatially).
Speech calibrated to 60 dB at 1 m (normal effort, direct path); diffuse ambient 42 dB (quiet office).
Maskers: ssn (talker long-term spectrum), babble6 (6 other voices), adapt_lag20 (noise following talker's
short-time spectrum, 20 ms causal lag), adapt_oracle (same, zero lag = perfect prediction),
samevoice3 (3 streams of the SAME talker's other utterances: proxy for a voice-cloned/predicted-speech masker).
Masker source level relative to speech source level: off, -10, -5, 0, +5, +10 dB.
Metrics at eavesdroppers 2/3/5 m (2 azimuths): STOI, ESTOI (human proxy), SII proxy (octave band SNR),
Whisper base.en word-correct (machine eavesdropper; subset). Talker cost: STOI at partner B's ear and masker
level there, with/without earbud known-masker cancellation (LS FIR 1024 taps fitted on separate segment).
Extra: whisper/quiet-voice + near-field mic + earbud relay leakage (level/SII estimate).
Run (resumable): nice -n 19 env OMP_NUM_THREADS=1 python -m selab.privacy.e3_mask [rir|obj|asr|cost|whisper]
"""
import sys, time, numpy as np
from pystoi import stoi
from scipy.signal import fftconvolve, stft, istft
from .common_p import FS, OUT, speakers, utterances, load, transcript, bandpass, save_json, load_json, concat_speaker

ROOM = [14.0, 12.0, 3.2]; RT60 = 0.5
TAB = np.array([6.0, 6.0])
A_POS = [5.55, 6.0, 1.2]; B_POS = [6.45, 6.0, 1.2]; MASK_POS = [6.0, 6.0, 0.80]
B_EAR = [6.45, 6.07, 1.25]
EAVES = {f"{r}m_az{az}": [6 + r * np.cos(np.radians(az)), 6 + r * np.sin(np.radians(az)), 1.4]
         for r in (2.0, 3.0, 5.0) for az in (30, 120)}
LEVELS = [None, -10, -5, 0, 5, 10]
MASKERS = ["ssn", "babble6", "adapt_lag20", "adapt_oracle", "samevoice3"]
TALKERS = speakers()[20:24]
OCT = [(250, 0.0617), (500, 0.1671), (1000, 0.2373), (2000, 0.2648), (4000, 0.2142), (7000, 0.0549)]
SPEECH_DB_1M = 60.0; AMB_DB = 42.0


def rirs():
    p = OUT / "e3_rirs.npz"
    if p.exists():
        d = np.load(p); return {k: d[k] for k in d.files}
    import pyroomacoustics as pra
    e_abs, max_order = pra.inverse_sabine(RT60, ROOM)
    out = {}
    for sname, spos in (("A", A_POS), ("M", MASK_POS)):
        room = pra.ShoeBox(ROOM, fs=FS, materials=pra.Material(e_abs), max_order=min(max_order, 17))
        room.add_source(spos)
        rcv = list(EAVES.values()) + [B_EAR, [A_POS[0] + 1.0, 6.0, 1.2]]
        room.add_microphone_array(np.array(rcv).T)
        room.compute_rir()
        names = list(EAVES) + ["B_ear", "ref1m"]
        for i, n in enumerate(names):
            out[f"{sname}|{n}"] = np.array(room.rir[i][0], dtype=np.float32)
    np.savez(p, **out)
    return out


def direct_gain(h):
    """amplitude of strongest (direct) tap -> used for 1 m calibration."""
    return np.abs(h).max()


def rms(x):
    return np.sqrt(np.mean(x ** 2) + 1e-20)


def active_rms(x, frame=320):
    n = len(x) // frame; e = np.array([np.mean(x[i * frame:(i + 1) * frame] ** 2) for i in range(n)])
    return np.sqrt(np.mean(e[e > e.max() * 1e-4]))


_ITEM = {}


def speech_item(spk, k=0):
    """first utterance of the talker between 6 and 14 s long (no truncation -> transcript matches audio)."""
    if spk not in _ITEM:
        for f in utterances(spk):
            x = load(f)
            if 6 * FS <= len(x) <= 14 * FS:
                _ITEM[spk] = (x, transcript(f), f); break
    x, t, f = _ITEM[spk]; return x, t


def make_masker(kind, x, spk, n, rng):
    if kind == "ssn":
        X = np.fft.rfft(x, 2 * n); ph = np.exp(2j * np.pi * rng.random(len(X)))
        from scipy.signal import welch
        f, P = welch(x, FS, nperseg=1024)
        Fx = np.fft.rfftfreq(2 * n, 1 / FS); mag = np.sqrt(np.interp(Fx, f, P))
        m = np.fft.irfft(mag * ph)[:n]
    elif kind == "babble6":
        others = [s for s in speakers() if s not in TALKERS][:6]
        m = np.zeros(n)
        for j, s in enumerate(others):
            y = concat_speaker(s, n / FS + 1, skip=1)[:n]; y = np.pad(y, (0, n - len(y)))
            m += y / active_rms(y)
    elif kind == "samevoice3":
        used = _ITEM[spk][2]; utts = [u for u in utterances(spk) if u != used]; m = np.zeros(n)
        for j in range(3):
            y = np.concatenate([load(f) for f in utts[j::3][:6]])
            st = int(rng.integers(0, max(1, len(y) - n))); y = y[st:st + n]; y = np.pad(y, (0, n - len(y)))
            m += y / active_rms(y)
    elif kind.startswith("adapt"):
        lag = 0 if kind == "adapt_oracle" else int(0.020 * FS)
        nper = 512; f, t, Z = stft(x, FS, nperseg=nper, noverlap=nper * 3 // 4)
        mag = np.abs(Z)
        # smooth spectral envelope across frequency (~ 1/3 oct-ish) to avoid re-synthesising the talker
        k = np.ones(9) / 9; env = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 0, mag)
        env = np.maximum(env, env.max() * 1e-3)   # keep a noise floor in pauses (masker never fully silent)
        sh = int(round(lag / (nper // 4)))
        if sh:
            env = np.concatenate([np.repeat(env[:, :1], sh, 1), env[:, :-sh]], 1)
        Zm = env * np.exp(2j * np.pi * rng.random(env.shape))
        _, m = istft(Zm, FS, nperseg=nper, noverlap=nper * 3 // 4); m = np.pad(m, (0, max(0, n - len(m))))[:n]
    return m / active_rms(m)


def sii_proxy(s, nz):
    tot = 0.0
    for fc, w in OCT:
        lo, hi = fc / np.sqrt(2), min(fc * np.sqrt(2), 7900)
        snr = 10 * np.log10(np.mean(bandpass(s, lo, hi) ** 2) / (np.mean(bandpass(nz, lo, hi) ** 2) + 1e-20))
        tot += w * np.clip((snr + 15) / 30, 0, 1)
    return tot


def ambient(n, rng):
    # quiet-office ambient: pink-ish noise (-3 dB/oct), independent per position (diffuse approximation)
    X = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / FS); X[1:] /= np.sqrt(f[1:] / 100); X[0] = 0
    a = np.fft.irfft(X, n); return a / rms(a)


def scene(R, spk, mkind, lvl, rcv, seed=0, effort_db=0.0):
    """returns (speech_at_rcv, interference_at_rcv) in Pa-like units where 1.0 rms = 0 dB re calibration."""
    rng = np.random.default_rng(seed)
    x, _ = speech_item(spk)
    g1 = direct_gain(R["A|ref1m"]) / 1.0      # direct-path amplitude at 1 m
    # scale dry speech so that its direct-path active rms at 1 m equals 10^(60/20) (units: dB re arbitrary)
    xs = x / active_rms(x) * 10 ** ((SPEECH_DB_1M + effort_db) / 20) / g1
    s = fftconvolve(xs, R[f"A|{rcv}"])[: len(x)]
    nz = ambient(len(x), rng) * 10 ** (AMB_DB / 20)
    if lvl is not None:
        m = make_masker(mkind, x, spk, len(x), rng)
        gm = direct_gain(R["A|ref1m"])  # same calibration convention: masker source level re speech source level
        ms = m * 10 ** ((SPEECH_DB_1M + lvl) / 20) / gm
        nz = nz + fftconvolve(ms, R[f"M|{rcv}"])[: len(x)]
    return xs, s, nz


def obj():
    R = rirs(); res = load_json("e3_obj.json") or {}
    t0 = time.time()
    for mk in MASKERS:
        for lvl in LEVELS:
            if lvl is None and mk != MASKERS[0]:
                continue
            for rcv in EAVES:
                key = f"{mk if lvl is not None else 'none'}|{lvl}|{rcv}"
                if key in res:
                    continue
                vals = []
                for i, spk in enumerate(TALKERS):
                    xs, s, nz = scene(R, spk, mk, lvl, rcv, seed=i)
                    y = s + nz
                    vals.append([stoi(s, y, FS), stoi(s, y, FS, extended=True), sii_proxy(s, nz),
                                 10 * np.log10(active_rms(s) ** 2), 10 * np.log10(rms(nz) ** 2)])
                res[key] = np.mean(vals, 0).round(3).tolist()
                save_json(res, "e3_obj.json")
                if time.time() - t0 > 100:
                    print("partial save; rerun", flush=True); return
    print("obj done", flush=True)


ASR_RCV = ["2.0m_az30", "5.0m_az120"]
ASR_LV = [None, -5, 0, 5]


def asr():
    from faster_whisper import WhisperModel
    from ..common import MODELS
    from ..score_r5 import asr_score
    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=1, num_workers=1,
                         download_root=str(MODELS / "whisper"))
    R = rirs(); res = load_json("e3_asr.json") or {}; t0 = time.time()
    for mk in MASKERS:
        for lvl in ASR_LV:
            if lvl is None and mk != MASKERS[0]:
                continue
            for rcv in ASR_RCV:
                for i, spk in enumerate(TALKERS):
                    key = f"{mk if lvl is not None else 'none'}|{lvl}|{rcv}|{spk}"
                    if key in res:
                        continue
                    xs, s, nz = scene(R, spk, mk, lvl, rcv, seed=i)
                    y = (s + nz).astype(np.float32); y = y * 0.05 / rms(y)
                    segs, _ = model.transcribe(y, language="en", beam_size=1, condition_on_previous_text=False,
                                               without_timestamps=True, vad_filter=False, temperature=0.0)
                    hyp = " ".join(sg.text for sg in segs)
                    res[key] = asr_score(speech_item(spk)[1], hyp)["word_correct"]
                    save_json(res, "e3_asr.json")
                    if time.time() - t0 > 95:
                        print("partial asr; rerun", len(res), flush=True); return
    print("asr done", len(res), flush=True)


def cost():
    """talker cost at partner B's ear: masker level, STOI without and with earbud known-masker cancellation.
    Cancellation model (ESTIMATE): the earbud knows the masker waveform exactly (it is generated by the device)
    and runs an adaptive FIR of L taps; residual = masker through the RIR tail beyond L taps + misadjustment
    noise at -25 dB re the masker at the ear. L = 1024 (64 ms) and 4096 (256 ms)."""
    R = rirs(); res = {}
    h = R["M|B_ear"]
    for mk in MASKERS:
        for lvl in LEVELS:
            key = f"{mk}|{lvl}"
            if lvl is None and mk != MASKERS[0]:
                continue
            vals = []
            for i, spk in enumerate(TALKERS[:2]):
                rng = np.random.default_rng(100 + i)
                xs, s, nz0 = scene(R, spk, mk, None, "B_ear", seed=i)   # speech + ambient only
                row = [10 * np.log10(active_rms(s) ** 2)]
                if lvl is None:
                    row += [stoi(s, s + nz0, FS), 10 * np.log10(rms(nz0) ** 2), stoi(s, s + nz0, FS), stoi(s, s + nz0, FS), 0, 0]
                else:
                    x, _ = speech_item(spk)
                    m = make_masker(mk, x, spk, len(x), rng) * 10 ** ((SPEECH_DB_1M + lvl) / 20) / direct_gain(R["A|ref1m"])
                    mb = fftconvolve(m, h)[: len(x)]
                    row += [stoi(s, s + nz0 + mb, FS), 10 * np.log10(rms(nz0 + mb) ** 2)]
                    for L in (1024, 4096):
                        tail = np.concatenate([np.zeros(L), h[L:]])
                        resid = fftconvolve(m, tail)[: len(x)]
                        mis = rng.standard_normal(len(x)); mis = bandpass(mis, 100, 7900)
                        mis = mis / rms(mis) * rms(mb) * 10 ** (-25 / 20)
                        resid = resid + mis
                        row += [stoi(s, s + nz0 + resid, FS)]
                    row += [10 * np.log10(np.mean(mb ** 2) / np.mean((fftconvolve(m, np.concatenate([np.zeros(1024), h[1024:]]))[: len(x)]) ** 2 + np.mean(mb ** 2) * 10 ** (-2.5))),
                            10 * np.log10(np.mean(mb ** 2) / np.mean((fftconvolve(m, np.concatenate([np.zeros(4096), h[4096:]]))[: len(x)]) ** 2 + np.mean(mb ** 2) * 10 ** (-2.5)))]
                vals.append(row)
            res[key] = np.mean(vals, 0).round(3).tolist()
            print(key, res[key], flush=True)
    res["_cols"] = ["speech_db_at_B", "stoi_B", "noise_db_at_B", "stoi_B_cancel1024", "stoi_B_cancel4096", "supp_db_1024", "supp_db_4096"]
    save_json(res, "e3_cost.json")


def whisper():
    """vocal-effort leakage: normal (0 dB), 'quietly' (-12 dB), whispering (-18 dB) re normal-relaxed sound power
    (Datakustik/IEC 60268-16 table). Spectrum kept = normal LTASS (ESTIMATE: real whisper has less LF energy and
    no voicing, so intelligibility at equal SII is likely LOWER -> conservative for privacy claims).
    Partner hears via near-field mic (~2.5 cm) + earbud relay."""
    R = rirs(); res = {}
    for eff_name, eff in (("normal", 0.0), ("quiet", -12.0), ("whisper", -18.0)):
        for rcv in list(EAVES) + ["B_ear"]:
            vals = []
            for i, spk in enumerate(TALKERS):
                xs, s, nz = scene(R, spk, "ssn", None, rcv, seed=i, effort_db=eff)
                vals.append([10 * np.log10(active_rms(s) ** 2), stoi(s, s + nz, FS), sii_proxy(s, nz)])
            res[f"{eff_name}|{rcv}"] = np.mean(vals, 0).round(3).tolist()
        # near-field mic level: inverse-square from 1 m to 2.5 cm => +32 dB re 1 m direct level
        res[f"{eff_name}|nearfield_mic_level_db"] = round(SPEECH_DB_1M + eff + 20 * np.log10(1 / 0.025), 1)
    # combo: whisper + low masker
    for lvl in (-20, -15, -10):
        for rcv in EAVES:
            vals = []
            for i, spk in enumerate(TALKERS):
                xs, s, nz = scene(R, spk, "babble6", lvl, rcv, seed=i, effort_db=-18.0)
                vals.append([stoi(s, s + nz, FS), sii_proxy(s, nz), 10 * np.log10(rms(nz) ** 2)])
            res[f"whisper+babble{lvl}|{rcv}"] = np.mean(vals, 0).round(3).tolist()
    save_json(res, "e3_whisper.json"); print("whisper done", flush=True)


def asr_effort():
    """Whisper word-correct for vocal-effort scenarios (quiet/whisper level, optional low babble masker)."""
    from faster_whisper import WhisperModel
    from ..common import MODELS
    from ..score_r5 import asr_score
    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=1, num_workers=1,
                         download_root=str(MODELS / "whisper"))
    R = rirs(); res = load_json("e3_asr_effort.json") or {}; t0 = time.time()
    for name, eff, lvl in (("quiet", -12.0, None), ("whisper", -18.0, None), ("whisper+babble-10", -18.0, -10), ("whisper+babble-15", -18.0, -15)):
        for rcv in ASR_RCV:
            for i, spk in enumerate(TALKERS):
                key = f"{name}|{rcv}|{spk}"
                if key in res:
                    continue
                xs, s, nz = scene(R, spk, "babble6", lvl, rcv, seed=i, effort_db=eff)
                y = (s + nz).astype(np.float32); y = y * 0.05 / rms(y)
                segs, _ = model.transcribe(y, language="en", beam_size=1, condition_on_previous_text=False,
                                           without_timestamps=True, vad_filter=False, temperature=0.0)
                res[key] = asr_score(speech_item(spk)[1], " ".join(sg.text for sg in segs))["word_correct"]
                save_json(res, "e3_asr_effort.json")
                if time.time() - t0 > 95:
                    print("partial; rerun", flush=True); return
    print("asr_effort done", flush=True)


if __name__ == "__main__":
    {"rir": rirs, "obj": obj, "asr": asr, "cost": cost, "whisper": whisper, "asr_effort": asr_effort}[sys.argv[1] if len(sys.argv) > 1 else "obj"]()
