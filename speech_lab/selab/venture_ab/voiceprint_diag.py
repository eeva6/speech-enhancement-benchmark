"""EXPLORATORY (not pre-registered) diagnostic for the voiceprint experiment: is the failure enrolment COVERAGE (3 s holds one
group talker) or embedding NOISE (1 s ECAPA on a leaky beam)?  Re-runs the FROZEN re-aim / revert rules on the test set with
two alternative enrolments:
  clean3  : causal, [1, 3] s, but from the clean group image (e+0 beam of T only)  -> removes other-talker leakage only
  oracleG : NON-causal oracle, group image T (e+0 beam) over windows anywhere in the clip with group speech and no other talker
            -> all group talkers enrolled (upper bound; not deployable)
python -m selab.venture_ab.voiceprint_diag test -> VW/diag_obj.csv
"""
import json, sys
import numpy as np, pandas as pd
from . import voiceprint as V
from ..common import FS


def enrol_sets(c, Z):
    from ..diar import core
    T = Z["e+0_T"].astype(np.float32); n = len(T); te = V.win_ends(n)
    gm, om = Z["gm"], Z["om"]
    out = {}
    w = [(t - 1, t) for t in te if t <= V.E_PRI + 1e-9 and gm[int((t - 1) * FS):int(t * FS)].mean() >= 0.5]
    out["clean3"] = core.embed_windows(T, np.array(w)) if w else None
    w = [(t - 1, t) for t in te[::2] if gm[int((t - 1) * FS):int(t * FS)].mean() >= 0.8 and om[int((t - 1) * FS):int(t * FS)].mean() == 0]
    out["oracleG"] = core.embed_windows(T, np.array(w)) if w else None
    return out


def main(which="test"):
    prm = V.load_params(); rows = []
    orig = V.enrol
    for c in V.sel(which):
        Z, comp = V.paths(c["gid"]); sets = enrol_sets(c, Z)
        for name, X in sets.items():
            if X is None:
                continue
            cen = X.mean(0); cen /= np.linalg.norm(cen) + 1e-9
            V.enrol = lambda Em, E, X=X, cen=cen: (X, cen)
            for r in V.clip_eval(c, prm, aims=["e+0", "e+20", "e-20", "wrong_group"], Zc=(Z, comp)):
                r["enrol"] = name; r["n_enrol"] = len(X); rows.append(r)
            V.enrol = orig
        print(c["gid"], {k: (None if v is None else len(v)) for k, v in sets.items()}, flush=True)
    pd.DataFrame(rows).to_csv(V.VW / "diag_obj.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "test")
