"""Round-5 sensitivity inputs (critique fixes), for the sub48 item subset (2 items per recording).

1. Oracle utterance boundaries.  mixtures/r5ctx/<id>/: the same real 7-mic recording cut with CTX s of extra
   context on each side (the context contains whatever else was playing: the other talkers in OV sets).
   Methods run on the long window; scoring the FULL window against the target transcript counts transcribed
   interferer words as insertions (what a listener-facing system without oracle timing would face); the
   `_cut` variants trim the output back to the oracle span (isolates the effect of context on the processing).
   Check: the cut-back channel-0 window must equal mixtures/r5/<id>/mix.wav sample-for-sample.
2. Same-room enrolment.  mixtures/r5/<id>/enrol_dry.wav: the SAME enrolment utterance taken from the dry
   LibriSpeech loudspeaker feed (studio-clean, no room, no array) instead of the in-room mic-0 recording.
python -m selab.sens_r5 build            -> mixtures/r5ctx, enrol_dry.wav
python -m selab.sens_r5 cut <method>     -> outputs/r5ctx/<method>_cut/
"""
import json, sys
import numpy as np, soundfile as sf
from .common import MIX, OUT, FS, save, load
from . import libricss as L
from .score_r5 import sub48

CTX = 2.0


def build():
    meta = {m["id"]: m for m in json.load(open(MIX / "r5" / "meta.json"))}
    keep = sub48(meta)
    dirs = {(c, s): d for c, s, d in L.sessions()}
    out = MIX / "r5ctx"; out.mkdir(parents=True, exist_ok=True)
    newmeta, checks = [], []
    for iid in keep:
        m = meta[iid]; d = dirs[(m["cond"], m["session"])]
        info = {u["uid"]: u for u in L.read_info(d)}
        u = info[m["uid"]]
        lag = np.polyval(m["clock"], (u["start"] + u["end"]) / 2)
        ra = int(u["start"] * FS) + m["direct_idx"] + int(np.round(lag))
        n = int(round(m["dur"] * FS)); c = int(CTX * FS)
        y, _ = sf.read(d + "/record/raw_recording.wav", start=ra - c, stop=ra + n + c, dtype="float32")
        x0 = load(MIX / "r5" / iid / "mix.wav")
        seg = y[c:c + len(x0), 0]
        err = float(np.max(np.abs(seg - x0)) / (np.max(np.abs(x0)) + 1e-9))
        # tolerate a +-2 sample offset from rounding (find the best one)
        if err > 1e-3:
            best = min(range(-3, 4), key=lambda k: np.mean(np.abs(y[c + k:c + k + len(x0), 0] - x0)))
            ra += best
            y, _ = sf.read(d + "/record/raw_recording.wav", start=ra - c, stop=ra + n + c, dtype="float32")
            seg = y[c:c + len(x0), 0]
            err = float(np.max(np.abs(seg - x0)) / (np.max(np.abs(x0)) + 1e-9))
        checks.append(err)
        dd = out / iid; dd.mkdir(exist_ok=True)
        sf.write(dd / "mix_mc.wav", y, FS, subtype="FLOAT"); save(dd / "mix.wav", y[:, 0])
        enrol = load(MIX / "r5" / iid / "enrol.wav"); save(dd / "enrol.wav", enrol)
        # dry enrolment: same enrolment utterance from the dry loudspeaker feed
        e = info[m["enrol_uid"]]
        a, b = int(e["start"] * FS), int(min(e["end"], e["start"] + 15) * FS)
        xd, _ = sf.read(d + "/clean/each_spk.wav", start=a, stop=b, dtype="float32")
        ch = int(np.argmax((xd ** 2).sum(0)))
        save(MIX / "r5" / iid / "enrol_dry.wav", xd[:, ch]); save(dd / "enrol_dry.wav", xd[:, ch])
        nm = dict(m); nm["dur"] = len(y) / FS; nm["ctx_s"] = CTX; nm["oracle_n"] = len(x0); newmeta.append(nm)
        print(iid, f"cut-back max rel. err {err:.2e}", flush=True)
    json.dump(newmeta, open(out / "meta.json", "w"), indent=0)
    dref = MIX / "r5" / "doa_ref.json"
    if dref.exists():
        (out / "doa_ref.json").write_text(dref.read_text())
    print("items", len(newmeta), "worst cut-back error", max(checks))


def cut(method):
    meta = json.load(open(MIX / "r5ctx" / "meta.json"))
    od = OUT / "r5ctx" / f"{method}_cut"; od.mkdir(parents=True, exist_ok=True)
    k = 0
    for m in meta:
        p = OUT / "r5ctx" / method / f"{m['id']}.wav"
        if p.exists():
            y = load(p); c = int(m["ctx_s"] * FS); save(od / p.name, y[c:c + m["oracle_n"]]); k += 1
    print(method, "cut", k)


if __name__ == "__main__":
    build() if sys.argv[1] == "build" else cut(sys.argv[2])
