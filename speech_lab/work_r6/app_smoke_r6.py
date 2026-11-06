"""Smoke test: app.process_mc with the round-6 superdirective options on one real LibriCSS 7-mic item."""
import json, sys, time
sys.argv = ["x"]
import app
m = [x for x in json.load(open("mixtures/r5/meta.json")) if x["cond"] == "OV20"][0]
p = f"mixtures/r5/{m['id']}/mix_mc.wav"; e = f"mixtures/r5/{m['id']}/enrol.wav"
geom = list(app.GEOMS)[0]
for enrol in (e, None):
    out = app.process_mc(p, geom, "", app.MC_METHODS[5:7], enrol)
    print(m["id"], "enrol" if enrol else "no enrol"); print(out[0].to_string()); print("files:", out[2])
import soundfile as sf, numpy as np
for f in out[2]:
    y, _ = sf.read(f); print(f.split("/")[-1], "rms", float(np.sqrt(np.mean(y**2))), "finite", bool(np.isfinite(y).all()), "len", len(y))
