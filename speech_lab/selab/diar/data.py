"""Dataset adapters for diarization evaluation.

LibriCSS (real 7-mic recordings, round 5): conditions 0S/OV10/OV20/OV40, sessions 0-5 that have
record/raw_recording.wav. Reference = meeting_info.txt (playback clock), mapped to the recording clock with
the round-5 global offset/drift fit (libricss.clock_fit). Tune sessions 0-2, test 3-5.

EasyCom (CC-BY-NC, research only; NEVER export audio): sessions 4/12 tune, 10/11 test. A session is the
concatenation of its 1-minute files (gaps between files are simply dropped). Reference = per-participant
transcription frames at 20 fps (wearer = participant 2). Mono channel = array ch2 (index 1, the round-7
reference mic); spatial = frame mics ch1-4.
"""
import json, re
import numpy as np
import soundfile as sf
from ..common import RES, FS

CACHE = RES / "diar" / "cache"


def norm_text(s):
    from ..run_r7 import norm_text as nt
    return nt(s)


# ----------------------------------------------------------------------------------------------- LibriCSS
def libricss_list(sessions, conds=("0S", "OV10", "OV20", "OV40")):
    from ..libricss import sessions as ls
    return [dict(ds="libricss", uri=f"lc_{c}_s{s}", cond=c, sess=s, dir=d) for c, s, d in ls(conds, sessions)]


def libricss_clock(item):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{item['uri']}.clock.json"
    if p.exists():
        return np.array(json.load(open(p)))
    from ..libricss import clock_fit
    y, _ = sf.read(item["dir"] + "/record/raw_recording.wav", dtype="float32")
    x, _ = sf.read(item["dir"] + "/clean/each_spk.wav", dtype="float32")
    A = clock_fit(y[:, 0], x.sum(1))
    json.dump(list(map(float, A)), open(p, "w"))
    return A


def libricss_load(item, channels="mono"):
    y, sr = sf.read(item["dir"] + "/record/raw_recording.wav", dtype="float32", always_2d=True)
    assert sr == FS
    return y[:, 0] if channels == "mono" else y.T


def libricss_ref(item):
    from ..libricss import read_info
    A = libricss_clock(item)
    rows = read_info(item["dir"])
    m = lambda t: t + np.polyval(A, t) / FS
    segs = [(m(r["start"]), m(r["end"]), r["spk"]) for r in rows]
    words = {}
    for r in sorted(rows, key=lambda r: r["start"]):
        words.setdefault(r["spk"], []).extend(norm_text(r["text"]).split())
    return segs, words


def libricss_streams(item):
    """'Platform' per-participant streams: the 8 dry loudspeaker feeds moved to the recording clock (energy VAD)."""
    x, _ = sf.read(item["dir"] + "/clean/each_spk.wav", dtype="float32", always_2d=True)
    A = libricss_clock(item)
    lag = int(round(np.polyval(A, len(x) / FS / 2)))
    return x.T, lag


# ----------------------------------------------------------------------------------------------- EasyCom
def easycom_list(sessions):
    return [dict(ds="easycom", uri=f"ec_s{s}", sess=s) for s in sessions]


def _ec():
    from .. import ec_r7 as E
    return E


def easycom_segs(item):
    return _ec().segs(item["sess"])


def easycom_load(item, channels="mono"):
    E = _ec(); out = []
    for seg in easycom_segs(item):
        x = E.load_array16(item["sess"], seg)
        out.append(x[1] if channels == "mono" else x[:4])
    return np.concatenate(out, -1)


def easycom_ref(item):
    E = _ec(); segs = []; utts = []; off = 0.0
    for seg in easycom_segs(item):
        n = sf.info(str(E.CACHE / f"Session_{item['sess']}" / f"{seg}.wav")).frames / FS
        for u in E.transcripts(item["sess"], seg):
            a, b = off + u["start"], off + min(u["end"], n)
            if b > a:
                segs.append((a, b, f"P{u['pid']}"))
                utts.append((a, f"P{u['pid']}", u["text"]))
        off += n
    words = {}
    for a, p, t in sorted(utts):
        words.setdefault(p, []).extend(norm_text(t).split())
    return segs, words


def easycom_yaw(item):
    """head yaw (deg) per 50 ms pose frame over the concatenated session, from the round-7 doa cache
    (fwd_world = head forward unit vector in world coordinates). NaN where the wearer pose is invalid."""
    E = _ec(); ys = []
    for seg in easycom_segs(item):
        d = np.load(E.CACHE / f"Session_{item['sess']}" / f"{seg}.doa.npz")
        n = int(round(sf.info(str(E.CACHE / f"Session_{item['sess']}" / f"{seg}.wav")).frames / FS * E.POSE_FPS))
        fw = d["fwd_world"][:n]
        y = np.degrees(np.arctan2(fw[:, 0], fw[:, 2]))
        y[~d["wearer_valid"][:n]] = np.nan
        if len(y) < n:
            y = np.r_[y, np.full(n - len(y), np.nan)]
        ys.append(y)
    return np.concatenate(ys)


def easycom_streams(item):
    """'Platform' per-participant streams: aligned close mics (16 kHz cache) per participant id, concatenated."""
    E = _ec(); segl = easycom_segs(item)
    pids = sorted({p for seg in segl for p in E.close_ids(item["sess"], seg)})
    out = {p: [] for p in pids}
    for seg in segl:
        n = sf.info(str(E.CACHE / f"Session_{item['sess']}" / f"{seg}.wav")).frames
        have = E.close_ids(item["sess"], seg)
        for p in pids:
            out[p].append(E.load_close16(item["sess"], seg, p)[:n] if p in have else np.zeros(n, np.float32))
            if len(out[p][-1]) < n:
                out[p][-1] = np.pad(out[p][-1], (0, n - len(out[p][-1])))
    return {p: np.concatenate(v) for p, v in out.items()}


# ----------------------------------------------------------------------------------------------- generic
def load(item, channels="mono"):
    return libricss_load(item, channels) if item["ds"] == "libricss" else easycom_load(item, channels)


def ref(item):
    return libricss_ref(item) if item["ds"] == "libricss" else easycom_ref(item)


def items(split):
    if split == "lc_tune":
        return libricss_list(range(0, 3))
    if split == "lc_test":
        return libricss_list(range(3, 6))
    if split == "ec_tune":
        return easycom_list([4, 12])
    if split == "ec_test":
        return easycom_list([10, 11])
    raise ValueError(split)
