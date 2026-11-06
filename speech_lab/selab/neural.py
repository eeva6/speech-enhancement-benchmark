"""Pretrained neural enhancers / separators (CPU inference, no fine-tuning).

  demucs_dns64      : facebookresearch/denoiser, causal Demucs trained on DNS data (Defossez et al. 2020)
  metricgan_plus    : SpeechBrain MetricGAN+ (VoiceBank-DEMAND), BLSTM mask, non-causal (Fu et al. 2021)
  sepformer_enh     : SpeechBrain SepFormer trained for enhancement on WHAM! 16 kHz, non-causal transformer
  tse_convtasnet_ecapa : "separate-then-select" target-speaker extraction:
                      Asteroid Conv-TasNet (Libri2Mix sep_noisy 16k) -> 2 streams, pick the one whose ECAPA-TDNN
                      speaker embedding is closest (cosine) to an enrolment utterance of the target speaker.
  tse_convtasnet_oracle : same separator, stream picked by max SI-SDR vs reference (ORACLE: upper bound only)
"""
import numpy as np
import torch
from .common import MODELS, FS

torch.set_num_threads(2)
_cache = {}


def _sb_dir(name):
    return str(MODELS / "speechbrain" / name.split("/")[-1])


def demucs_dns64():
    if "dns64" not in _cache:
        from denoiser import pretrained
        m = pretrained.dns64().eval()
        _cache["dns64"] = m
    return _cache["dns64"]


def run_demucs(x, **_):
    m = demucs_dns64()
    with torch.no_grad():
        y = m(torch.from_numpy(x)[None, None])[0, 0].numpy()
    return y[: len(x)]


def run_metricgan(x, **_):
    if "mgan" not in _cache:
        from speechbrain.inference.enhancement import SpectralMaskEnhancement
        _cache["mgan"] = SpectralMaskEnhancement.from_hparams("speechbrain/metricgan-plus-voicebank",
                                                              savedir=_sb_dir("metricgan-plus-voicebank"))
    with torch.no_grad():
        y = _cache["mgan"].enhance_batch(torch.from_numpy(x)[None], lengths=torch.tensor([1.0]))[0].numpy()
    return y[: len(x)]


def run_sepformer_enh(x, **_):
    if "sepf" not in _cache:
        from speechbrain.inference.separation import SepformerSeparation
        _cache["sepf"] = SepformerSeparation.from_hparams("speechbrain/sepformer-wham16k-enhancement",
                                                          savedir=_sb_dir("sepformer-wham16k-enhancement"))
    with torch.no_grad():
        y = _cache["sepf"].separate_batch(torch.from_numpy(x)[None])[0, :, 0].numpy()
    return y[: len(x)]


def convtasnet():
    if "ctn" not in _cache:
        from asteroid.models import ConvTasNet
        _cache["ctn"] = ConvTasNet.from_pretrained("JorisCos/ConvTasNet_Libri2Mix_sepnoisy_16k").eval()
    return _cache["ctn"]


def ecapa():
    if "ecapa" not in _cache:
        from speechbrain.inference.speaker import EncoderClassifier
        _cache["ecapa"] = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb",
                                                         savedir=_sb_dir("spkrec-ecapa-voxceleb"))
    return _cache["ecapa"]


def embed(x):
    with torch.no_grad():
        e = ecapa().encode_batch(torch.from_numpy(np.asarray(x, np.float32))[None])[0, 0]
    return torch.nn.functional.normalize(e, dim=0)


def separate2(x):
    with torch.no_grad():
        return convtasnet()(torch.from_numpy(x)[None])[0].numpy()[:, : len(x)]


def run_tse_ecapa(x, enrol=None, info=None, **_):
    srcs = separate2(x)
    e = embed(enrol)
    sims = [float(embed(s) @ e) for s in srcs]
    k = int(np.argmax(sims))
    if info is not None:
        info.update(sims=sims, picked=k)
    return srcs[k]


def run_tse_oracle(x, ref=None, info=None, **_):
    from .metrics import si_sdr
    srcs = separate2(x)
    sc = [si_sdr(ref, s) for s in srcs]
    k = int(np.argmax(sc))
    if info is not None:
        info.update(picked=k)
    return srcs[k]


def run_demucs_then_tse(x, enrol=None, info=None, **_):
    """Round-2 hybrid: denoise first (removes non-speech noise), then separate-and-select."""
    return run_tse_ecapa(run_demucs(x), enrol=enrol, info=info)


METHODS = {
    "demucs_dns64": run_demucs,
    "metricgan_plus": run_metricgan,
    "sepformer_enh": run_sepformer_enh,
    "tse_convtasnet_ecapa": run_tse_ecapa,
    "tse_convtasnet_oracle": run_tse_oracle,
    "demucs_then_tse": run_demucs_then_tse,
}

ALGO_LATENCY = {  # documented, not measured: model-intrinsic lookahead + frame
    "demucs_dns64": "causal; ~40 ms per Defossez et al. 2020 streaming setup (measured below via DemucsStreamer)",
    "metricgan_plus": "non-causal (bidirectional LSTM over whole utterance)",
    "sepformer_enh": "non-causal (full-sequence transformer)",
    "tse_convtasnet_ecapa": "non-causal Conv-TasNet checkpoint + utterance-level speaker embedding",
    "tse_convtasnet_oracle": "oracle (not deployable)",
    "demucs_then_tse": "non-causal",
}


def n_params(method):
    try:
        if method.startswith("demucs") and method != "demucs_then_tse":
            return sum(p.numel() for p in demucs_dns64().parameters())
        if method == "metricgan_plus":
            return sum(p.numel() for p in _cache["mgan"].mods.parameters())
        if method == "sepformer_enh":
            return sum(p.numel() for p in _cache["sepf"].mods.parameters())
        if method.startswith("tse"):
            return sum(p.numel() for p in convtasnet().parameters()) + sum(p.numel() for p in ecapa().mods.parameters())
        if method == "demucs_then_tse":
            return n_params("demucs_dns64") + n_params("tse_convtasnet_ecapa")
    except Exception:
        return None


# ---- Round 3 additions: low-latency causal models -------------------------------------------------
from scipy.signal import resample_poly


def _rnnoise_raw(x16):
    """RNNoise (Valin 2018) via pyrnnoise: 48 kHz, 10 ms frames, frame-causal. Returns 16 kHz output, uncompensated."""
    from pyrnnoise import RNNoise
    x48 = resample_poly(x16, 3, 1)
    pcm = np.clip(x48 * 32767, -32768, 32767).astype(np.int16)
    den = RNNoise(48000)
    frames = [f for _, f in den.denoise_chunk(pcm[None, :], partial=True)]
    y48 = np.concatenate([np.atleast_2d(f) for f in frames], axis=1)[0].astype(np.float32) / 32767
    return resample_poly(y48, 1, 3).astype(np.float32)


RNNOISE_DELAY = None  # samples @16k, measured once on a probe signal (impulse-free: cross-correlation)


def rnnoise_delay():
    global RNNOISE_DELAY
    if RNNOISE_DELAY is None:
        rng = np.random.default_rng(0)
        # probe: a speech-like modulated noise burst; delay = argmax cross-correlation of output vs input
        t = np.arange(3 * FS) / FS
        probe = (rng.standard_normal(len(t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)) * 0.1).astype(np.float32)
        y = _rnnoise_raw(probe)
        c = np.correlate(y[:FS * 2], probe[:FS * 2], "full")
        RNNOISE_DELAY = int(np.argmax(c) - (FS * 2 - 1))
    return RNNOISE_DELAY


def run_rnnoise(x, **_):
    y = _rnnoise_raw(x)
    d = max(rnnoise_delay(), 0)  # compensate the model's intrinsic delay so sample-aligned metrics are fair
    y = np.concatenate([y[d:], np.zeros(d, np.float32)])
    return y[: len(x)]


def run_deepfilternet(x, **_):
    """DeepFilterNet3 (Schroeter et al. 2023), 48 kHz; df.enhance(pad=True) compensates its STFT/lookahead delay."""
    if "df" not in _cache:
        from df.enhance import init_df
        m, st, _ = init_df(model_base_dir=str(MODELS / "df" / "DeepFilterNet3"), log_level="ERROR")
        _cache["df"] = (m, st)
    from df.enhance import enhance
    m, st = _cache["df"]
    x48 = torch.from_numpy(resample_poly(x, 3, 1).astype(np.float32))[None]
    with torch.no_grad():
        y48 = enhance(m, st, x48, pad=True)[0].numpy()
    return resample_poly(y48, 1, 3).astype(np.float32)[: len(x)]


METHODS.update({"rnnoise": run_rnnoise, "deepfilternet3": run_deepfilternet})
ALGO_LATENCY.update({"rnnoise": "causal, 10 ms frames (measured delay in results/latency_r3.json)",
                     "deepfilternet3": "causal with 2-frame lookahead; ~40 ms per Schroeter et al. 2023"})
