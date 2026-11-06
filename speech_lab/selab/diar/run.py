"""Who-said-what CLI.

python -m selab.diar.run <wav> [--multichannel] [--array libricss|easycom] [--num-speakers N]
                         [--cluster spectral|ahc] [--no-asr] [--enrol NAME=clip.wav ...] -o out.json|out.txt

Writes <stem>.rttm, <stem>.txt (speaker-attributed transcript) and <stem>.json (segments, words, timing) next to -o.
Single-channel: Silero VAD -> ECAPA (1.5 s / 0.5 s) -> NME-SC spectral clustering (eigengap K) or AHC -> smoothing
-> faster-whisper word timestamps -> word-level speaker assignment.
--multichannel: also SRP-PHAT DOA per window, fused into the affinity (array geometry from --array; default libricss
7-mic circular). Hyper-parameters default to results/diar/frozen_diar.json when present (tuned on held-out sessions).
--enrol: name clusters by cosine match of cluster centroids to enrolment clips (Hungarian; unmatched stay SPEAKER_k).
"""
import argparse, json, time
from pathlib import Path
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
from . import core, spatial
from ..common import RES


def load_wav(p):
    x, sr = sf.read(p, dtype="float32", always_2d=True)
    x = x.T
    if sr != 16000:
        g = np.gcd(sr, 16000); x = resample_poly(x, 16000 // g, sr // g, axis=1).astype(np.float32)
    return x


def frozen(ds):
    p = RES / "diar" / "frozen_diar.json"
    if p.exists():
        fz = json.load(open(p))
        if ds in fz:
            return fz[ds]
    return {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("wav"); ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--multichannel", action="store_true")
    ap.add_argument("--array", default="libricss", choices=["libricss", "easycom"])
    ap.add_argument("--num-speakers", type=int, default=None)
    ap.add_argument("--cluster", default="spectral", choices=["spectral", "ahc"])
    ap.add_argument("--no-asr", action="store_true")
    ap.add_argument("--mono-channel", type=int, default=None, help="channel used for VAD/embeddings/ASR")
    ap.add_argument("--enrol", nargs="*", default=[], help="NAME=clip.wav")
    a = ap.parse_args(argv)
    t0 = time.time(); tm = {}
    x = load_wav(a.wav)
    ch = a.mono_channel if a.mono_channel is not None else (1 if a.array == "easycom" and x.shape[0] >= 4 else 0)
    y = x[ch] if x.shape[0] > 1 else x[0]
    dur = len(y) / 16000; T = int(np.ceil(dur / core.FR))
    fz = frozen(a.array)
    key = ("spec" if a.cluster == "spectral" else "ahc") + ("_sp" if a.multichannel else "")
    cfg = dict(fz.get(key, {}))
    t = time.time(); p, hop = core.silero_probs(y); tm["vad"] = time.time() - t
    sp = core.probs_to_frames(p, hop, T, thr=cfg.get("vad_thr", 0.5), min_sil=cfg.get("min_sil", 0.15))
    t = time.time()
    wins = core.window_grid(len(y), 1.5, 0.5)
    i0 = np.round(wins[:, 0] / core.FR).astype(int); i1 = np.minimum(np.round(wins[:, 1] / core.FR).astype(int), T)
    cs = np.r_[0, np.cumsum(sp)]; frac = (cs[i1] - cs[i0]) / np.maximum(i1 - i0, 1)
    sel = np.where(frac >= 0.5)[0]; wins = wins[sel]
    E = core.embed_windows(y, wins); tm["embed"] = time.time() - t
    S = E @ E.T
    if a.multichannel:
        if x.shape[0] < 4:
            raise SystemExit("--multichannel needs a multichannel wav")
        t = time.time()
        az, steer, band = spatial.libricss_steer() if a.array == "libricss" else spatial.easycom_steer()
        xm = x[:7] if a.array == "libricss" else x[:4]
        P, _ = spatial.srp_blocks(xm, steer, band)
        _, pk, _ = spatial.window_doa(P, wins, az)
        A = spatial.angle_affinity(pk, sigma=cfg.get("sigma", 20.0))
        b = cfg.get("beta", 0.3); S = (1 - b) * S + b * A
        tm["doa"] = time.time() - t
    t = time.time()
    if a.cluster == "spectral":
        fn = lambda M: core.spectral(M, kmax=cfg.get("kmax", 10), oracle_k=a.num_speakers)
    else:
        fn = lambda M: core.ahc(M, thr=cfg.get("ahc_thr", 0.6), oracle_k=a.num_speakers)
    lab, info = core.cluster_big(S, fn)
    lab = core.refine(E, lab, oracle_k=a.num_speakers)
    fl, _ = core.frame_labels(wins, lab, sp)
    segs = core.labels_to_segments(fl); tm["cluster"] = time.time() - t
    names = None
    if a.enrol:
        from scipy.optimize import linear_sum_assignment
        en = {}
        for kv in a.enrol:
            nm, path = kv.split("=", 1)
            en[nm] = core.embed_clip(load_wav(path)[0])
        K = int(lab.max()) + 1
        C = np.stack([E[lab == k].mean(0) for k in range(K)]); C /= np.linalg.norm(C, axis=1, keepdims=True)
        M = np.stack(list(en.values())); sim = C @ M.T
        ri, ci = linear_sum_assignment(-sim)
        nms = list(en)
        names = {int(r): nms[c] for r, c in zip(ri, ci) if sim[r, c] > 0.35}
    words = []
    if not a.no_asr:
        t = time.time(); words = core.transcribe_words(y); tm["asr"] = time.time() - t
    wl = core.assign_words(words, fl)
    out = Path(a.out); stem = out.with_suffix("")
    out.parent.mkdir(parents=True, exist_ok=True)
    core.write_rttm(segs, str(stem) + ".rttm", uri=Path(a.wav).stem, names=names)
    txt = core.transcript_text(wl, names) if wl else "\n".join(
        f"[{s:7.2f}-{e:7.2f}] {(names or {}).get(k, f'SPEAKER_{k + 1}')}" for s, e, k in segs)
    open(str(stem) + ".txt", "w").write(txt + "\n")
    tm["total"] = time.time() - t0
    res = dict(wav=a.wav, duration_s=dur, n_speakers=int(lab.max()) + 1, cluster=a.cluster, multichannel=a.multichannel,
               config=cfg, info={k: (int(v) if isinstance(v, (np.integer,)) else v) for k, v in info.items()},
               segments=[dict(start=round(s, 2), end=round(e, 2), speaker=(names or {}).get(k, f"SPEAKER_{k + 1}"))
                         for s, e, k in segs],
               words=[dict(start=round(s, 2), end=round(e, 2), word=w, speaker=(names or {}).get(k, f"SPEAKER_{k + 1}"))
                      for s, e, w, k in wl],
               timing_s=tm, rtf=tm["total"] / dur)
    json.dump(res, open(str(stem) + ".json", "w"), indent=1)
    print(f"{a.wav}: {dur:.1f} s, {res['n_speakers']} speakers, RTF {res['rtf']:.2f} -> {stem}.rttm/.txt/.json")


if __name__ == "__main__":
    main()
