"""Enrolment-based naming (how 'named' speakers work offline): python -m selab.diar.enrol_eval

For each LibriCSS test session: enrolment clip per reference speaker = their FIRST utterance (<= 8 s, mono, from the same
recording; it is excluded from scoring). Clusters of the frozen A_spectral system are named by Hungarian matching of
cluster-centroid vs enrolment embeddings (cosine > 0.35, else left unnamed). Scored: DER with the NAME mapping imposed
(no optimal re-mapping) vs DER with the optimal mapping, on speech after each speaker's enrolment utterance.
"""
import json
import numpy as np, pandas as pd
from scipy.optimize import linear_sum_assignment
from . import core, data, score, metrics
from ..common import RES

OUT = RES / "diar"


def main():
    fz = json.load(open(OUT / "frozen_diar.json"))["libricss"]
    rows = []
    for it in data.items("lc_test"):
        f = score.feats(it)
        y = data.load(it, "mono")
        first = {}
        for a, b, s in sorted(f["ref"]):
            first.setdefault(s, (a, min(b, a + 8.0)))
        en = {s: core.embed_clip(y[int(a * 16000):int(b * 16000)]) for s, (a, b) in first.items()}
        t_cut = max(b for a, b in first.values())          # score only after every enrolment clip
        lab, _ = score.diarize(f, fz["spec"], it)
        wins = f["wins"]; E = f["emb"]
        K = int(lab.max()) + 1
        # cluster centroids from windows whose centre frame carries that label
        cen = []
        for k in range(K):
            idx = [i for i, (a, b) in enumerate(wins) if lab[min(int((a + b) / 2 / core.FR), len(lab) - 1)] == k]
            c = E[idx].mean(0) if idx else np.zeros(E.shape[1]); cen.append(c / (np.linalg.norm(c) + 1e-9))
        C = np.stack(cen); spk = list(en); M = np.stack([en[s] for s in spk])
        sim = C @ M.T
        ri, ci = linear_sum_assignment(-sim)
        name = {int(r): spk[c] for r, c in zip(ri, ci) if sim[r, c] > 0.35}
        hyp = [(a, b, name.get(k, f"unk{k}")) for a, b, k in core.labels_to_segments(lab) if b > t_cut]
        hyp = [(max(a, t_cut), b, s) for a, b, s in hyp]
        ref = [(max(a, t_cut), b, s) for a, b, s in f["ref"] if b > t_cut]
        d_opt = metrics.der(ref, hyp)["der"]
        # imposed mapping: confusion counted when the hyp name differs from the reference speaker
        T = int(np.ceil(max(b for _, b, _ in ref + hyp) / core.FR)) + 1
        keys = sorted({s for *_, s in ref} | {s for *_, s in hyp}, key=str)
        R, _ = metrics._mat(ref, T, keys); H, _ = metrics._mat(hyp, T, keys)
        nr, nh = R.sum(1), H.sum(1); corr = (R & H).sum(1)
        d_name = (np.maximum(nr - nh, 0) + np.maximum(nh - nr, 0) + np.minimum(nr, nh) - corr).sum() / nr.sum()
        rows.append(dict(uri=it["uri"], n_ref=len(spk), n_clusters=K, n_named=len(name), der_opt=d_opt, der_named=d_name))
        print(rows[-1], flush=True)
    df = pd.DataFrame(rows); df.to_csv(OUT / "test_enrol_naming.csv", index=False)
    print(df.mean(numeric_only=True).round(3))


if __name__ == "__main__":
    main()
