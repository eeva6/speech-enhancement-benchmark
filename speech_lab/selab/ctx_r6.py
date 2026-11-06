"""Round-6 warm-start inputs: every round-5 item (all 144) re-cut from the raw LibriCSS 7-mic recording with
PRE seconds of the preceding audio (whatever was playing: silence, the target's previous sentence, or other
talkers) and no extra audio after the item.  A causal front-end run over this window has the history a
continuously running device would have; the output is then cut back to the item span for scoring.
Check: the cut-back channel-0 span equals channel 0 of mixtures/r5/<id>/mix_mc.wav (max relative error printed / stored).
Same alignment code as selab/sens_r5.py (round-5 context build).
python -m selab.ctx_r6   -> mixtures/r6ctx/<id>/mix_mc.wav, meta.json (ctx_s, oracle_n, cutback_err)
"""
import json
import numpy as np, soundfile as sf
from .common import MIX, FS, load
from . import libricss as L

PRE = 2.0


def main():
    meta = json.load(open(MIX / "r5" / "meta.json"))
    dirs = {(c, s): d for c, s, d in L.sessions()}
    out = MIX / "r6ctx"; out.mkdir(parents=True, exist_ok=True)
    infos, newmeta = {}, []
    for m in meta:
        iid = m["id"]; d = dirs[(m["cond"], m["session"])]
        if d not in infos:
            infos[d] = {u["uid"]: u for u in L.read_info(d)}
        u = infos[d][m["uid"]]
        lag = np.polyval(m["clock"], (u["start"] + u["end"]) / 2)
        ra = int(u["start"] * FS) + m["direct_idx"] + int(np.round(lag))
        x0 = sf.read(str(MIX / "r5" / iid / "mix_mc.wav"), dtype="float32")[0][:, 0]; n = len(x0); c = int(PRE * FS)
        y, _ = sf.read(d + "/record/raw_recording.wav", start=ra - c, stop=ra + n, dtype="float32")
        err = float(np.max(np.abs(y[c:c + n, 0] - x0)) / (np.max(np.abs(x0)) + 1e-9))
        if err > 1e-3:
            best = min(range(-3, 4), key=lambda k: np.mean(np.abs(y[c + k:c + k + n, 0] - x0)) if c + k + n <= len(y) else 9)
            ra += best
            y, _ = sf.read(d + "/record/raw_recording.wav", start=ra - c, stop=ra + n, dtype="float32")
            err = float(np.max(np.abs(y[c:c + n, 0] - x0)) / (np.max(np.abs(x0)) + 1e-9))
        dd = out / iid; dd.mkdir(exist_ok=True)
        sf.write(dd / "mix_mc.wav", y, FS, subtype="FLOAT")
        nm = dict(m); nm["ctx_s"] = PRE; nm["oracle_n"] = n; nm["cutback_err"] = err; newmeta.append(nm)
        print(iid, f"{err:.1e}", flush=True)
    json.dump(newmeta, open(out / "meta.json", "w"), indent=0)
    json.dump(json.load(open(MIX / "r5" / "doa_ref.json")), open(out / "doa_ref.json", "w"))


if __name__ == "__main__":
    main()
