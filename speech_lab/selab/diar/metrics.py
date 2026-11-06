"""Diarization metrics.

der(): frame-based (10 ms) DER following the NIST md-eval definition: optimal one-to-one speaker mapping
(Hungarian on overlap time), overlapped speech scored, a no-score collar of +-collar seconds around every
reference segment boundary. DER = (miss + false alarm + confusion) / total reference speaker time.
Cross-checked against pyannote.metrics (collar there = total width = 2 x ours) in tests_metrics.py.
jer(): pyannote.metrics JaccardErrorRate (collar 0).
cpwer(): concatenated minimum-permutation WER (CHiME-6 definition): per speaker, concatenate the words in time
order for reference and hypothesis, pick the speaker mapping that minimises total errors (Hungarian over the
pairwise edit-distance matrix, unmatched speakers padded with empty streams), divide by reference words.
"""
import numpy as np
from scipy.optimize import linear_sum_assignment

FR = 0.01


def _mat(segs, T, keys=None):
    keys = keys or sorted({s for _, _, s in segs}, key=str)
    M = np.zeros((T, len(keys)), bool)
    ix = {k: i for i, k in enumerate(keys)}
    for a, b, s in segs:
        M[max(0, int(round(a / FR))):min(T, int(round(b / FR))), ix[s]] = True
    return M, keys


def der(ref, hyp, collar=0.0, T=None):
    """ref/hyp: lists of (start, end, speaker). Returns dict(der, miss, fa, conf, total) (rates)."""
    end = max([b for _, b, _ in ref] + [b for _, b, _ in hyp] + [0])
    T = T or int(np.ceil(end / FR)) + 1
    R, rk = _mat(ref, T); H, hk = _mat(hyp, T)
    score = np.ones(T, bool)
    if collar > 0:
        c = int(round(collar / FR))
        for a, b, _ in ref:
            for t in (int(round(a / FR)), int(round(b / FR))):
                score[max(0, t - c):min(T, t + c)] = False
    R, H = R[score], H[score]
    nr, nh = R.sum(1), H.sum(1)
    if R.shape[1] and H.shape[1]:
        ov = R.T.astype(float) @ H.astype(float)
        ri, hi = linear_sum_assignment(-ov)
        corr = sum((R[:, i] & H[:, j]).astype(int) for i, j in zip(ri, hi))
        mapping = {rk[i]: hk[j] for i, j in zip(ri, hi)}
    else:
        corr = np.zeros(len(R), int); mapping = {}
    tot = nr.sum()
    miss = np.maximum(nr - nh, 0).sum(); fa = np.maximum(nh - nr, 0).sum()
    conf = (np.minimum(nr, nh) - corr).sum()
    tot = max(tot, 1)
    return dict(der=(miss + fa + conf) / tot, miss=miss / tot, fa=fa / tot, conf=conf / tot,
                total_s=tot * FR, mapping=mapping)


def jer(ref, hyp):
    from pyannote.core import Annotation, Segment
    from pyannote.metrics.diarization import JaccardErrorRate
    r, h = Annotation(), Annotation()
    for i, (a, b, s) in enumerate(ref):
        r[Segment(a, b), i] = str(s)
    for i, (a, b, s) in enumerate(hyp):
        h[Segment(a, b), i] = str(s)
    return float(JaccardErrorRate(collar=0.0)(r, h))


def pyannote_der(ref, hyp, collar=0.0):
    from pyannote.core import Annotation, Segment
    from pyannote.metrics.diarization import DiarizationErrorRate
    r, h = Annotation(), Annotation()
    for i, (a, b, s) in enumerate(ref):
        r[Segment(a, b), i] = str(s)
    for i, (a, b, s) in enumerate(hyp):
        h[Segment(a, b), i] = str(s)
    return float(DiarizationErrorRate(collar=2 * collar, skip_overlap=False)(r, h))


def edit_distance(r, h):
    """word-level Levenshtein distance (substitutions + deletions + insertions)."""
    if not r:
        return len(h)
    if not h:
        return len(r)
    voc = {}
    ri = np.array([voc.setdefault(w, len(voc)) for w in r]); hi = np.array([voc.setdefault(w, len(voc)) for w in h])
    prev = np.arange(len(hi) + 1)
    for i in range(1, len(ri) + 1):
        cur = np.empty_like(prev); cur[0] = i
        sub = prev[:-1] + (hi != ri[i - 1])
        # cur[j] = min(prev[j]+1, cur[j-1]+1, sub[j-1]) -> sequential in j; vectorise with cummin trick
        base = np.minimum(prev[1:] + 1, sub)
        # handle insertions (cur[j-1]+1) via running minimum of (base[j] - j) + j
        tmp = np.minimum.accumulate(np.r_[cur[0], base] - np.arange(len(hi) + 1)) + np.arange(len(hi) + 1)
        cur = tmp
        prev = cur
    return int(prev[-1])


def cpwer(ref_words, hyp_words):
    """ref_words / hyp_words: dict speaker -> list of words (time order). Returns dict(cpwer, errors, n_ref, mapping)."""
    rk, hk = list(ref_words), list(hyp_words)
    n = max(len(rk), len(hk))
    C = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            r = ref_words[rk[i]] if i < len(rk) else []
            h = hyp_words[hk[j]] if j < len(hk) else []
            C[i, j] = edit_distance(r, h)
    ri, hi = linear_sum_assignment(C)
    err = C[ri, hi].sum(); N = sum(len(v) for v in ref_words.values())
    mp = {rk[i]: hk[j] for i, j in zip(ri, hi) if i < len(rk) and j < len(hk)}
    return dict(cpwer=err / max(N, 1), errors=int(err), n_ref=int(N), mapping=mp)


def wer_all(ref_words_t, hyp_words_t):
    """speaker-agnostic WER on time-ordered word lists (lower bound of cpWER apart from ordering effects)."""
    return edit_distance(ref_words_t, hyp_words_t) / max(len(ref_words_t), 1)
