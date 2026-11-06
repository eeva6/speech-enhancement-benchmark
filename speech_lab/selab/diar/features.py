"""Heavy, cached, resumable per-recording features for the diarization evaluation.

python -m selab.diar.features <split> [<split> ...] [--asr]
splits: lc_tune lc_test ec_tune ec_test. Cache: results/diar/cache/<uri>.<stage>.(npz|json).
Stages: vad (Silero on the mono channel), emb (ECAPA on 1.5 s / 0.5 s windows), srp (SRP-PHAT 0.5 s blocks),
asr (faster-whisper base.en word timestamps; --asr), plat (per-participant stream activity), timing json.
"""
import json, sys, time
import numpy as np
from . import core, data, spatial
from .data import CACHE

WIN, HOP = 1.5, 0.5


def _t(item, stage, sec, dur):
    p = CACHE / f"{item['uri']}.timing.json"
    d = json.load(open(p)) if p.exists() else {}
    d[stage] = dict(sec=sec, dur=dur, rtf=sec / dur)
    json.dump(d, open(p, "w"), indent=1)


def frame_energy_db(y, fr=0.01, fs=16000):
    n = len(y) // int(fr * fs)
    e = (np.asarray(y[: n * int(fr * fs)], np.float64).reshape(n, -1) ** 2).mean(1)
    return 10 * np.log10(e + 1e-12)


def run_item(item, do_asr=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    u = item["uri"]
    y = None

    def mono():
        nonlocal y
        if y is None:
            y = data.load(item, "mono")
        return y
    if not (CACHE / f"{u}.vad.npz").exists():
        t = time.time(); p, hop = core.silero_probs(mono())
        np.savez(CACHE / f"{u}.vad.npz", p=p, hop=hop, n=len(mono()), edb=frame_energy_db(mono()))
        _t(item, "vad", time.time() - t, len(mono()) / 16000); print(u, "vad", flush=True)
    if not (CACHE / f"{u}.emb.npz").exists():
        t = time.time(); w = core.window_grid(len(mono()), WIN, HOP)
        e = core.embed_windows(mono(), w)
        np.savez(CACHE / f"{u}.emb.npz", wins=w, emb=e.astype(np.float32))
        _t(item, "emb", time.time() - t, len(mono()) / 16000); print(u, "emb", flush=True)
    if not (CACHE / f"{u}.srp.npz").exists():
        t = time.time()
        x = data.load(item, "mc")
        az, steer, band = spatial.libricss_steer() if item["ds"] == "libricss" else spatial.easycom_steer()
        P, en = spatial.srp_blocks(x, steer, band)
        np.savez(CACHE / f"{u}.srp.npz", P=P.astype(np.float32), en=en, az=az)
        _t(item, "srp", time.time() - t, x.shape[1] / 16000); del x; print(u, "srp", flush=True)
    if item["ds"] == "easycom" and not (CACHE / f"{u}.yaw.npy").exists():
        np.save(CACHE / f"{u}.yaw.npy", data.easycom_yaw(item))
    if not (CACHE / f"{u}.plat.npz").exists():
        t = time.time()
        if item["ds"] == "libricss":
            x, lag = data.libricss_streams(item)
            edb = np.stack([frame_energy_db(c) for c in x])
            np.savez(CACHE / f"{u}.plat.npz", edb=edb, lag=lag, kind="energy")
        else:
            st = data.easycom_streams(item)
            pids = sorted(st)
            pr = np.stack([core.silero_probs(st[p])[0] for p in pids])
            edb = np.stack([frame_energy_db(st[p]) for p in pids])
            np.savez(CACHE / f"{u}.plat.npz", pids=np.array(pids), probs=pr, edb=edb, kind="closemic")
        _t(item, "plat", time.time() - t, len(mono()) / 16000); print(u, "plat", flush=True)
    if do_asr and not (CACHE / f"{u}.asr.json").exists():
        t = time.time(); words = core.transcribe_words(mono())
        json.dump(words, open(CACHE / f"{u}.asr.json", "w"))
        _t(item, "asr", time.time() - t, len(mono()) / 16000); print(u, "asr", len(words), flush=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_asr = "--asr" in sys.argv
    for sp in args:
        for it in data.items(sp):
            try:
                run_item(it, do_asr=do_asr and sp.endswith("test"))
            except Exception as ex:
                import traceback; traceback.print_exc(); print("FAILED", it["uri"], ex, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
