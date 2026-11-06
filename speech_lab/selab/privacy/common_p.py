"""Shared helpers for the privacy-bubble experiments (venture: Conversation Bubble).
New file; does not modify existing lab code."""
import os, glob, json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import firwin2, lfilter, butter, sosfilt, welch

FS = 16000
C = 343.0
LAB = Path(__file__).resolve().parents[2]
LIBRI = LAB / "data" / "LibriSpeech" / "dev-clean-2"
OUT = Path("/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS/privacy_bubble")
OUT.mkdir(parents=True, exist_ok=True)
BANDS = [(125, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 7900)]
BAND_NAMES = ["125-250", "250-500", "500-1k", "1k-2k", "2k-4k", "4k-8k"]


def speakers():
    return sorted(os.listdir(LIBRI))


def utterances(spk):
    fl = sorted(glob.glob(str(LIBRI / spk / "*" / "*.flac")))
    return fl


def transcript(flac):
    p = Path(flac); uid = p.stem
    tr = list(p.parent.glob("*.trans.txt"))[0]
    for line in open(tr):
        k, t = line.strip().split(" ", 1)
        if k == uid:
            return t
    return ""


def load(f):
    x, sr = sf.read(f, dtype="float32")
    assert sr == FS
    return x


def concat_speaker(spk, secs, skip=0):
    xs, n = [], 0
    for f in utterances(spk)[skip:]:
        x = load(f); xs.append(x); n += len(x)
        if n >= secs * FS:
            break
    return np.concatenate(xs)[: int(secs * FS)]


def bandpass(x, lo, hi, order=6):
    sos = butter(order, [lo, min(hi, FS / 2 - 50)], btype="band", fs=FS, output="sos")
    return sosfilt(sos, x)


def ltass(x, nfft=1024):
    f, P = welch(x, fs=FS, nperseg=nfft)
    return f, P


def save_json(obj, name):
    with open(OUT / name, "w") as fh:
        json.dump(obj, fh, indent=1)


def load_json(name):
    p = OUT / name
    return json.load(open(p)) if p.exists() else None
