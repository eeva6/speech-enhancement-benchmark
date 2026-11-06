"""Shared paths, I/O and STFT helpers."""
import os
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MIX = ROOT / "mixtures"
OUT = ROOT / "outputs"
RES = ROOT / "results"
MODELS = ROOT / "models"
FS = 16000

# keep model caches on the persistent workspace, not the small root disk
os.environ.setdefault("HF_HOME", str(MODELS / "hf"))
os.environ.setdefault("TORCH_HOME", str(MODELS / "torch"))


def load(path, fs=FS):
    x, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if x.ndim > 1:
        x = x.mean(axis=1) if x.shape[1] < x.shape[0] else x.mean(axis=0)
    if sr != fs:
        g = np.gcd(int(sr), int(fs))
        x = resample_poly(x, fs // g, sr // g).astype(np.float32)
    return x


def save(path, x, fs=FS):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(x, dtype=np.float32)
    peak = np.max(np.abs(x)) if x.size else 0
    if peak > 0.999:  # avoid wrap-around clipping in int16; record that it happened
        x = x * (0.999 / peak)
    sf.write(str(path), x.T if x.ndim > 1 else x, fs, subtype="PCM_16")


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-12))


def match_len(x, n):
    if len(x) >= n:
        return x[:n]
    return np.pad(x, (0, n - len(x)))
