"""Round 7: EasyCom readers and geometry helpers (shared by prep_r7, onset_r7, track_r7).

Conventions (see results/r7/atf_convention.md, derived from the measured ATFs):
  head frame = tracked-pose rigid-body frame, X left, Y up, Z forward;
  az = atan2(x, z) (0 = array forward, +90 = left), el = atan2(y, hypot(x, z));
  ATF Phi == az, ATF Theta == 90 - el.
"""
import json, re
from pathlib import Path
import numpy as np
import soundfile as sf
from .common import DATA, MIX, RES, FS

EC = DATA / "easycom"
MAIN = EC / "Main"
CACHE = EC / "r7_16k"
ATF_H5 = EC / "Calibration" / "Array Transfer Functions" / "Device_ATFs.h5"
SPLIT = {4: "val", 12: "val", 10: "test", 11: "test"}
SESSIONS = (4, 12, 10, 11)
POSE_FPS = 20.0
MIC_POS = np.array([[82, -5, -29], [-1, -1, 30], [-77, -2, 11], [-83, -5, -60]], float) / 1000.0  # ch1-4, m
C = 343.0
CLOSE_FS_NOMINAL = 48008.6


def segs(sess):
    """1-minute segment names (mm-ss-SSS) that have glasses audio."""
    return sorted(p.stem for p in (MAIN / "Glasses_Microphone_Array_Audio" / f"Session_{sess}").glob("??-??-???.wav"))


def seg_start_s(seg):
    m, s, ms = seg.split("-")
    return int(m) * 60 + int(s) + int(ms) / 1000.0


def close_ids(sess, seg):
    out = []
    for p in (MAIN / "Close_Microphone_Audio" / f"Session_{sess}").glob(f"{seg}_Participant_ID_*.wav"):
        out.append(int(re.search(r"ID_(\d+)\.wav$", p.name).group(1)))
    return sorted(out)


def read_json(kind, sess, seg):
    p = MAIN / kind / f"Session_{sess}" / f"{seg}.json"
    if not p.exists():
        return None
    b = p.read_bytes()
    try:
        return json.loads(b.decode("utf-8"))
    except UnicodeDecodeError:          # some transcription files are cp1252 (e.g. accented letters)
        return json.loads(b.decode("cp1252"))


def transcripts(sess, seg):
    """list of dict(pid, start, end (s, segment time), text, target) from Speech_Transcriptions.
    Start_Frame/End_Frame are 20 fps video frames; frame f covers [f/20, (f+1)/20)."""
    j = read_json("Speech_Transcriptions", sess, seg)
    if j is None:
        return []
    out = []
    for u in j:
        tgt = u.get("Target_of_Speech")
        if tgt is None:
            tgt = []
        if not isinstance(tgt, list):
            tgt = [tgt]
        out.append(dict(pid=int(u["Participant_ID"]), start=u["Start_Frame"] / POSE_FPS,
                        end=(u["End_Frame"] + 1) / POSE_FPS, text=u.get("Transcription", ""),
                        target=[str(t) for t in tgt]))
    return out


def poses(sess, seg):
    """dict pid -> (pos (T,3) m, quat (T,4) xyzw, upside (T,) bool, valid (T,) bool); T = number of pose frames."""
    j = read_json("Tracked_Poses", sess, seg)
    if j is None:
        return None, 0
    T = len(j)
    ids = sorted({int(p["Participant_ID"]) for fr in j for p in fr.get("Participants", [])})
    out = {i: (np.full((T, 3), np.nan), np.full((T, 4), np.nan), np.zeros(T, bool)) for i in ids}
    for t, fr in enumerate(j):
        for p in fr.get("Participants", []):
            i = int(p["Participant_ID"])
            out[i][0][t] = [p["Position_X"], p["Position_Y"], p["Position_Z"]]
            out[i][1][t] = [p["Quaternion_X"], p["Quaternion_Y"], p["Quaternion_Z"], p["Quaternion_W"]]
            out[i][2][t] = bool(p.get("isUpSideDown", False))
    res = {}
    for i, (P, Q, U) in out.items():
        v = np.isfinite(P).all(1) & np.isfinite(Q).all(1) & ~U
        res[i] = (P, Q, U, v)
    return res, T


def quat_to_R(q):
    """q (...,4) as x,y,z,w -> rotation matrices (...,3,3) mapping body-frame vectors to world."""
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    x, y, z, w = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    R = np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
        np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
        np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], -2)
    return R


def to_head(Pw, Qw, Pt, inverse=False):
    """direction of Pt as seen from the wearer pose (Pw, Qw), in the head frame. inverse=True uses R instead of
    R^T (alternative quaternion convention, used only for the convention test)."""
    R = quat_to_R(Qw)
    d = Pt - Pw
    if inverse:
        return np.einsum("tij,tj->ti", R, d)
    return np.einsum("tji,tj->ti", R, d)


def az_el(v):
    v = np.asarray(v)
    az = np.degrees(np.arctan2(v[..., 0], v[..., 2]))
    el = np.degrees(np.arctan2(v[..., 1], np.hypot(v[..., 0], v[..., 2])))
    return az, el


def unit(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.stack([np.cos(e) * np.sin(a), np.sin(e), np.cos(e) * np.cos(a)], -1)


def ang3(az1, el1, az2, el2):
    u, v = unit(az1, el1), unit(az2, el2)
    return np.degrees(np.arccos(np.clip((u * v).sum(-1), -1, 1)))


def wrap(a):
    return (np.asarray(a) + 180) % 360 - 180


def load_atf(fs=FS, chans=(0, 1, 2, 3), nfft=512):
    """ATF steering at fs: returns (az (D,), el (D,), H (D, F, M)) with F = nfft//2+1 bins.
    IRs are resampled 48k -> fs (resample_poly) and zero-padded to nfft."""
    import h5py
    from scipy.signal import resample_poly
    f = h5py.File(ATF_H5, "r")
    IR = f["IR"][()]                          # (768, 1020, 6)
    th = np.degrees(f["Theta"][()].ravel()); ph = np.degrees(f["Phi"][()].ravel())
    ir = resample_poly(IR[:, :, list(chans)], 1, 48000 // fs, axis=0)   # (256, D, M)
    H = np.fft.rfft(ir, nfft, axis=0)         # (F, D, M)
    return wrap(ph), 90.0 - th, np.transpose(H, (1, 0, 2))


def load_array16(sess, seg):
    x, sr = sf.read(str(CACHE / f"Session_{sess}" / f"{seg}.wav"), dtype="float32", always_2d=True)
    assert sr == FS
    return x.T


def load_close16(sess, seg, pid):
    x, sr = sf.read(str(CACHE / f"Session_{sess}" / f"{seg}_P{pid}.wav"), dtype="float32")
    return x
