"""Diarization core: VAD, sliding-window ECAPA embeddings, clustering (spectral/NME-SC and AHC),
frame-level smoothing, RTTM writing and word-level speaker assignment.

All components are ungated: Silero VAD (MIT, weights ship in the pip package), SpeechBrain
spkrec-ecapa-voxceleb (Apache-2.0, already cached by round 6), faster-whisper base.en.
Time base: 16 kHz audio, 10 ms label frames.
"""
import os
import numpy as np

FS = 16000
FR = 0.01            # label frame (s)


# ----------------------------------------------------------------------------------------------- VAD
_M = {}


def silero_probs(y, fs=FS):
    """Silero VAD speech probability per 512-sample chunk (32 ms). Returns (probs, hop_s)."""
    import torch
    torch.set_num_threads(1)
    if "vad" not in _M:
        from silero_vad import load_silero_vad
        _M["vad"] = load_silero_vad(onnx=True)
    m = _M["vad"]
    m.reset_states()
    y = np.asarray(y, np.float32)
    n = len(y) // 512
    out = np.zeros(n, np.float32)
    t = torch.from_numpy(y[: n * 512].copy())
    for i in range(n):
        out[i] = float(m(t[i * 512:(i + 1) * 512], fs))
    return out, 512 / fs


def probs_to_frames(p, hop, n_frames, thr=0.5, min_speech=0.25, min_sil=0.15, pad=0.05):
    """Hysteresis on Silero probs -> boolean speech mask at 10 ms frames."""
    on = p >= thr
    off_thr = max(thr - 0.15, 0.05)
    st = np.zeros(len(p), bool); cur = False
    for i, v in enumerate(p):
        cur = (v >= thr) if not cur else (v >= off_thr)
        st[i] = cur
    segs = mask_to_segs(st, hop)
    segs = merge_close(segs, min_sil)
    segs = [(max(0, a - pad), b + pad) for a, b in segs if b - a >= min_speech]
    return segs_to_mask(segs, n_frames)


def mask_to_segs(m, step=FR):
    m = np.asarray(m, bool)
    if not m.any():
        return []
    d = np.diff(np.r_[0, m.astype(int), 0])
    s = np.where(d == 1)[0]; e = np.where(d == -1)[0]
    return [(a * step, b * step) for a, b in zip(s, e)]


def merge_close(segs, gap):
    out = []
    for a, b in sorted(segs):
        if out and a - out[-1][1] < gap:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def segs_to_mask(segs, n_frames, step=FR):
    m = np.zeros(n_frames, bool)
    for a, b in segs:
        m[max(0, int(round(a / step))):min(n_frames, int(round(b / step)))] = True
    return m


# ----------------------------------------------------------------------------------------------- embeddings
def window_grid(n_samples, win=1.5, hop=0.5, fs=FS):
    L = len(np.arange(0, max(n_samples / fs - win, 0) + 1e-9, hop))
    st = np.arange(L) * hop
    return np.stack([st, st + win], 1)


def ecapa_model():
    if "ecapa" not in _M:
        import torch
        torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "1")))
        from ..common import MODELS
        from speechbrain.inference.speaker import EncoderClassifier
        _M["ecapa"] = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb",
                                                     savedir=str(MODELS / "speechbrain" / "spkrec-ecapa-voxceleb"),
                                                     run_opts={"device": "cpu"})
    return _M["ecapa"]


def embed_windows(y, wins, fs=FS, batch=32):
    import torch
    m = ecapa_model()
    out = []
    L = int(round((wins[0, 1] - wins[0, 0]) * fs))
    with torch.no_grad():
        for i in range(0, len(wins), batch):
            seg = [y[int(round(a * fs)):int(round(a * fs)) + L] for a, _ in wins[i:i + batch]]
            seg = [np.pad(s, (0, L - len(s))) for s in seg]
            x = torch.from_numpy(np.stack(seg).astype(np.float32))
            e = m.encode_batch(x)[:, 0].numpy()
            out.append(e)
    e = np.concatenate(out, 0)
    return e / (np.linalg.norm(e, axis=1, keepdims=True) + 1e-9)


def embed_clip(y):
    import torch
    with torch.no_grad():
        e = ecapa_model().encode_batch(torch.from_numpy(np.asarray(y, np.float32))[None])[0, 0].numpy()
    return e / (np.linalg.norm(e) + 1e-9)


# ----------------------------------------------------------------------------------------------- clustering
def _kmeans(X, k, seed=0):
    from sklearn.cluster import KMeans
    return KMeans(k, n_init=10, random_state=seed).fit_predict(X)


def _small_eigs(L, kmax):
    """the kmax+1 smallest eigenvalues followed by the largest one (enough for the eigengap and NME normalisation)."""
    from scipy.linalg import eigh
    N = len(L)
    lo = eigh(L, eigvals_only=True, subset_by_index=[0, min(kmax, N - 1)], driver="evr")
    hi = eigh(L, eigvals_only=True, subset_by_index=[N - 1, N - 1], driver="evr")
    return np.r_[lo, hi]


def spectral(S, kmax=10, kmin=2, oracle_k=None, p_grid=None):
    """NME-SC style spectral clustering (Park et al., IEEE SPL 2020): row-wise top-p binarisation of the
    affinity, unnormalised Laplacian, p chosen to minimise p / normalised-max-eigengap, K by eigengap.
    Returns labels, info dict."""
    N = len(S)
    if N <= 2:
        return np.zeros(N, int), dict(k=1, p=0)
    S = np.array(S, float)
    np.fill_diagonal(S, 1.0)
    kmax = min(kmax, N - 1)
    if p_grid is None:
        hi = max(2, int(N * 0.25))
        p_grid = np.unique(np.linspace(max(2, int(N * 0.01)), hi, 12).astype(int))
    best = None
    for p in p_grid:
        A = np.zeros_like(S)
        idx = np.argsort(-S, 1)[:, :p]
        np.put_along_axis(A, idx, 1.0, 1)
        A = 0.5 * (A + A.T)
        L = np.diag(A.sum(1)) - A
        lam = _small_eigs(L, kmax)
        gaps = np.diff(lam[: kmax + 1])
        g = gaps[kmin - 1:].max() / (lam[-1] + 1e-10)
        r = (p / N) / (g + 1e-10)
        if best is None or r < best[0]:
            best = (r, p, A, lam)
    _, p, A, lam = best
    if oracle_k:
        k = int(oracle_k)
    else:
        gaps = np.diff(lam[: kmax + 1])
        k = int(np.argmax(gaps[kmin - 1:]) + kmin)
    L = np.diag(A.sum(1)) - A
    from scipy.linalg import eigh
    w, V = eigh(L, subset_by_index=[0, k - 1], driver="evr")
    U = V[:, :k]
    U = U / (np.linalg.norm(U, axis=1, keepdims=True) + 1e-9)
    lab = _kmeans(U, k)
    return lab, dict(k=k, p=int(p))


def ahc(S, thr=0.6, oracle_k=None):
    """Average-linkage AHC on cosine distance 1-S, cut at distance thr (or at oracle_k clusters)."""
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import squareform
    N = len(S)
    if N <= 1:
        return np.zeros(N, int), dict(k=1)
    D = np.clip(1.0 - np.array(S, float), 0, 2)
    D = 0.5 * (D + D.T); np.fill_diagonal(D, 0)
    Z = linkage(squareform(D, checks=False), "average")
    lab = fcluster(Z, oracle_k, "maxclust") if oracle_k else fcluster(Z, thr, "distance")
    lab = np.unique(lab, return_inverse=True)[1]
    return lab, dict(k=int(lab.max() + 1))


def cluster_big(S, fn, nmax=1500):
    """cluster at most nmax evenly strided windows with fn(S_sub) -> (labels, info), then give every window the
    cluster with the highest mean affinity to that cluster's members (keeps O(N^3) eigen-solves bounded)."""
    N = len(S)
    if N <= nmax:
        return fn(S)
    step = int(np.ceil(N / nmax)); sub = np.arange(0, N, step)
    lab_s, info = fn(S[np.ix_(sub, sub)])
    K = int(lab_s.max()) + 1
    M = np.stack([S[:, sub[lab_s == k]].mean(1) for k in range(K)], 1)
    lab = np.argmax(M, 1)
    info = dict(info, subsampled=int(step))
    return np.unique(lab, return_inverse=True)[1], info


def refine(E, lab, min_frac=0.02, iters=2, oracle_k=None):
    """Centroid re-assignment ('k-means polish') and absorption of tiny clusters (< min_frac of windows)."""
    lab = np.asarray(lab).copy()
    for _ in range(iters):
        ks, cnt = np.unique(lab, return_counts=True)
        keep = ks[cnt >= max(2, min_frac * len(lab))] if not oracle_k else ks
        if len(keep) == 0:
            keep = ks[[np.argmax(cnt)]]
        C = np.stack([E[lab == k].mean(0) for k in keep])
        C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-9
        lab = keep[np.argmax(E @ C.T, 1)]
    return np.unique(lab, return_inverse=True)[1]


# ----------------------------------------------------------------------------------------------- frames / output
def frame_labels(wins, wlab, speech, wscore=None, min_run=0.25):
    """Vote window labels onto 10 ms frames (Hann-weighted), restricted to speech frames.
    Returns int array (-1 = non-speech) and the vote matrix (T, K)."""
    T = len(speech)
    K = int(wlab.max()) + 1 if len(wlab) else 1
    V = np.zeros((T, K), np.float32)
    for (a, b), k in zip(wins, wlab):
        i0, i1 = int(round(a / FR)), min(T, int(round(b / FR)))
        if i1 <= i0:
            continue
        V[i0:i1, k] += np.hanning(i1 - i0 + 2)[1:-1]
    lab = np.full(T, -1, int)
    has = V.sum(1) > 0
    lab[has] = np.argmax(V[has], 1)
    # speech frames not covered by any selected window -> nearest covered frame
    need = speech & ~has
    if need.any() and has.any():
        idx = np.where(has)[0]
        j = np.searchsorted(idx, np.where(need)[0]).clip(0, len(idx) - 1)
        j2 = (j - 1).clip(0)
        nf = np.where(need)[0]
        pick = np.where(np.abs(idx[j] - nf) <= np.abs(idx[j2] - nf), idx[j], idx[j2])
        lab[need] = lab[pick]
    lab[~speech] = -1
    # remove short runs inside speech: relabel to the longer neighbour
    mr = int(round(min_run / FR))
    for _ in range(2):
        runs = _runs(lab)
        for i, (s, e, k) in enumerate(runs):
            if k < 0 or e - s >= mr:
                continue
            prv = runs[i - 1] if i > 0 else None
            nxt = runs[i + 1] if i + 1 < len(runs) else None
            cands = [r for r in (prv, nxt) if r is not None and r[2] >= 0 and (r[1] == s or r[0] == e)]
            if cands:
                lab[s:e] = max(cands, key=lambda r: r[1] - r[0])[2]
    return lab, V


def _runs(lab):
    out = []; s = 0
    for i in range(1, len(lab) + 1):
        if i == len(lab) or lab[i] != lab[s]:
            out.append((s, i, int(lab[s]))); s = i
    return out


def labels_to_segments(lab, extra=None):
    """frame labels (+ optional list of (frame_idx_array, label) overlap additions) -> [(start, end, spk)]."""
    segs = [(s * FR, e * FR, k) for s, e, k in _runs(lab) if k >= 0]
    if extra is not None:
        for k, m in extra.items():
            segs += [(a, b, k) for a, b in mask_to_segs(m)]
    return sorted(segs)


def write_rttm(segs, path, uri="rec", names=None):
    with open(path, "w") as f:
        for a, b, k in segs:
            nm = k if isinstance(k, str) else (names.get(k, f"SPEAKER_{k + 1}") if names else f"SPEAKER_{k + 1}")
            f.write(f"SPEAKER {uri} 1 {a:.3f} {b - a:.3f} <NA> <NA> {nm} <NA> <NA>\n")


# ----------------------------------------------------------------------------------------------- ASR
def asr_model():
    if "asr" not in _M:
        from faster_whisper import WhisperModel
        from ..common import MODELS
        _M["asr"] = WhisperModel("base.en", device="cpu", compute_type="int8",
                                 cpu_threads=int(os.environ.get("OMP_NUM_THREADS", "1")), num_workers=1,
                                 download_root=str(MODELS / "whisper"))
    return _M["asr"]


def transcribe_words(y, fs=FS):
    """faster-whisper base.en with word timestamps on the whole recording; returns [(start, end, word)]."""
    r = np.sqrt(np.mean(np.asarray(y, np.float64) ** 2)) + 1e-12
    y = np.clip(np.asarray(y, np.float32) * (10 ** (-26 / 20) / r), -1, 1).astype(np.float32)
    segs, _ = asr_model().transcribe(y, language="en", beam_size=1, condition_on_previous_text=False,
                                     word_timestamps=True, vad_filter=True, temperature=0.0)
    out = []
    for s in segs:
        for w in (s.words or []):
            out.append((float(w.start), float(w.end), w.word.strip()))
    return out


def assign_words(words, lab):
    """word -> speaker by majority of labelled frames inside [start, end]; nearest labelled frame if none."""
    T = len(lab)
    idx = np.where(lab >= 0)[0]
    out = []
    for a, b, w in words:
        i0, i1 = int(a / FR), max(int(a / FR) + 1, int(np.ceil(b / FR)))
        seg = lab[i0:min(i1, T)]
        seg = seg[seg >= 0]
        if len(seg):
            k = int(np.bincount(seg).argmax())
        elif len(idx):
            c = int(((a + b) / 2) / FR)
            j = np.searchsorted(idx, c).clip(0, len(idx) - 1)
            j2 = max(j - 1, 0)
            k = int(lab[idx[j] if abs(idx[j] - c) <= abs(idx[j2] - c) else idx[j2]])
        else:
            k = 0
        out.append((a, b, w, k))
    return out


def transcript_text(wl, names=None, gap=1.0):
    """speaker-attributed transcript lines 'SPEAKER_k [mm:ss]: words' (new line on speaker change or long gap)."""
    lines = []; cur = None; buf = []; t0 = 0; last = -1e9
    for a, b, w, k in wl:
        if k != cur or a - last > gap * 4:
            if buf:
                lines.append((t0, cur, " ".join(buf)))
            cur, buf, t0 = k, [], a
        buf.append(w); last = b
    if buf:
        lines.append((t0, cur, " ".join(buf)))
    nm = (lambda k: names.get(k, f"SPEAKER_{k + 1}")) if names else (lambda k: f"SPEAKER_{k + 1}")
    return "\n".join(f"[{int(t // 60):02d}:{t % 60:04.1f}] {nm(k)}: {txt}" for t, k, txt in lines)
