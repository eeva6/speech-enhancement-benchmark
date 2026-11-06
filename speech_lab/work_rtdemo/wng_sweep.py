# scratch: hs_sd4 SNR gain vs WNG floor on the simulated 4-mic linear scenes (exact decomposition)
import json, numpy as np
from selab import r6
from selab.rtdemo import scenes as S, evalsim as EV
from selab.rtdemo.engine import B, load_scene
out = {}
for sid, b in (("sim_street", S.build_sim_street), ("sim_restaurant", S.build_sim_restaurant)):
    g = EV.capture(b); meta, xs, comps = load_scene(sid)
    t = g["imgs"][0]; a = float(np.dot(comps["target"], t[1]) / np.dot(t[1], t[1])); T = a * t; N = xs - T
    base = EV.snr(T[1], N[1]); head = meta["head_az_array"]; r = {}
    for w in (6, 3, 0, -3, -6, -10):
        for ms in (4, 8):
            ys = []
            for X in (T, N):
                p = r6.STFTBF(np.asarray(meta["xy"]), win_ms=ms, kind="sd", wng_db=w)
                H = p.H; y = np.zeros(X.shape[1] // H * H)
                for i in range(0, len(y), H):
                    y[i:i + H] = p.process_hop(X[:, i:i + H], head, 1)
                ys.append(y)
            r[f"sd{ms}_w{w}"] = round(EV.snr(*ys) - base, 2)
    out[sid] = r; print(sid, r, flush=True)
json.dump(out, open("results/rtdemo/sim_wng_sweep.json", "w"), indent=1)
