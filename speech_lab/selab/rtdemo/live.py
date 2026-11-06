"""Genuinely live streaming path: the engine runs block by block against a real-time clock.

Mode A (default, works on this sandbox): the scene file plays the role of the microphone array.  Block i (2 ms)
"arrives" at t_start + (i+1)*2 ms; the loop sleeps until it has arrived, processes it (all modes, so a switch is
instant and every mode's filter state is live), and must finish before the next block arrives.  Mode switches
follow --switch "t:mode,..." (seconds) or keys typed on stdin (1-7 + Enter).  Logs per-block compute, lateness and
deadline misses, writes the switched output, and checks it bit-for-bit against the pre-rendered tracks.

Mode B (--device, on a laptop with PortAudio): same engine inside a sounddevice OutputStream callback (blocksize 32
at 16 kHz), so you hear it on the sound card; switch modes by typing 1-7 + Enter.  (Untested here: this sandbox has
no audio device / PortAudio.)

python -m selab.rtdemo.live --scene easycom_s10 --switch "0:raw,3:hs_sd4,6:hyb_sd4,9:trk_sd4,12:anc_sim"
python -m selab.rtdemo.live --scene libricss_ov40 --device
"""
import argparse, json, os, sys, threading, time
import numpy as np
import soundfile as sf
from ..common import ROOT, FS
from .engine import Engine, load_scene, B

OUT = ROOT / "results" / "rtdemo" / "live"
REN = ROOT / "listening" / "rtdemo" / "render"


def parse_switch(s, modes):
    ev = []
    for part in (s or "").split(","):
        if part.strip():
            t, m = part.split(":"); assert m in modes, (m, modes); ev.append((int(round(float(t) * FS / B)), m))
    return sorted(ev) or [(0, modes[0])]


def stdin_switcher(eng, state):
    def run():
        for line in sys.stdin:
            k = line.strip()
            if k.isdigit() and 1 <= int(k) <= len(eng.modes):
                state["mode"] = eng.modes[int(k) - 1]; print("->", state["mode"], flush=True)
    threading.Thread(target=run, daemon=True).start()


def paced(sid, switch, seconds=None, all_modes=True):
    meta, x, comps = load_scene(sid)
    eng = Engine(meta)
    n = x.shape[1] // B if seconds is None else min(x.shape[1] // B, int(seconds * FS / B))
    ev = parse_switch(switch, eng.modes); state = {"mode": ev[0][1]}
    if not sys.stdin.isatty():
        pass
    else:
        stdin_switcher(eng, state)
    y = np.zeros(n * B); active = []
    comp, late, miss = np.zeros(n), np.zeros(n), 0
    la0 = list(os.getloadavg())
    t_start = time.perf_counter() + 0.05
    e = 0
    for i in range(n):
        while e < len(ev) and ev[e][0] <= i:
            state["mode"] = ev[e][1]; e += 1
        arrive = t_start + (i + 1) * B / FS                      # block i fully captured at this time
        dt = arrive - time.perf_counter()
        if dt > 0:
            time.sleep(dt)
        t0 = time.perf_counter()
        cb = None if comps is None else {k: v[i * B:(i + 1) * B] for k, v in comps.items()}
        o = eng.process_block(x[:, i * B:(i + 1) * B], cb, only=None if all_modes else [state["mode"]])
        t1 = time.perf_counter()
        y[i * B:(i + 1) * B] = o[state["mode"]]; active.append(state["mode"])
        comp[i] = t1 - t0; late[i] = t1 - arrive                 # time from block arrival to its output being ready
        if t1 > arrive + B / FS:
            miss += 1
    la1 = list(os.getloadavg())
    # bit-exact check against the pre-rendered tracks
    ok = True; nd = 0
    for i, m in enumerate(active):
        p = REN / sid / f"{m}.f32.npy"
        ref = np.load(p, mmap_mode="r")[i * B:(i + 1) * B]
        if not np.array_equal(y[i * B:(i + 1) * B].astype(np.float32), ref):
            ok = False; nd += 1
    OUT.mkdir(parents=True, exist_ok=True)
    sf.write(OUT / f"{sid}_live_switched_nice{os.nice(0)}.wav", np.clip(y, -1, 1), FS, subtype="PCM_16")
    ms = lambda a: dict(mean=float(np.mean(a) * 1e3), median=float(np.median(a) * 1e3), p95=float(np.percentile(a, 95) * 1e3),
                        p99=float(np.percentile(a, 99) * 1e3), max=float(np.max(a) * 1e3))
    res = dict(scene=sid, blocks=n, block_ms=1000 * B / FS, all_modes_computed=all_modes, switch=switch,
               compute_ms=ms(comp), arrival_to_output_ms=ms(late), deadline_misses=miss, miss_frac=miss / n,
               rtf_mean=float(np.mean(comp) / (B / FS)), load_before=la0, load_after=la1, nice=os.nice(0),
               bit_identical_to_prerender=ok, n_blocks_differing=nd,
               note="deadline = the next block's arrival (2 ms after this one). Misses under load are scheduler "
                    "pre-emption of this nice-19 process by the round-7 pipeline, not compute (see compute_ms).")
    json.dump(res, open(OUT / f"{sid}_live_nice{os.nice(0)}.json", "w"), indent=1)
    print(json.dumps(res, indent=1))
    return res


def device(sid):
    import sounddevice as sd
    meta, x, comps = load_scene(sid)
    eng = Engine(meta); state = {"mode": eng.modes[0], "i": 0}
    print("modes:", " ".join(f"{k + 1}={m}" for k, m in enumerate(eng.modes)), "(type number + Enter; Ctrl-C quits)")
    stdin_switcher(eng, state)
    T = x.shape[1] // B

    def cb(outdata, frames, tinfo, status):
        i = (state["i"] % T) * B; state["i"] += 1
        c = None if comps is None else {k: v[i:i + B] for k, v in comps.items()}
        o = eng.process_block(x[:, i:i + B], c)
        outdata[:, 0] = o[state["mode"]].astype(np.float32)
    with sd.OutputStream(samplerate=FS, blocksize=B, channels=1, dtype="float32", callback=cb, latency="low"):
        while True:
            time.sleep(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="easycom_s10"); ap.add_argument("--switch", default="0:raw,3:hs_sd4,6:hyb_sd4,9:trk_sd4,12:anc_sim")
    ap.add_argument("--seconds", type=float); ap.add_argument("--device", action="store_true")
    ap.add_argument("--active-only", action="store_true", help="compute only the active mode (not bit-identical after a switch)")
    a = ap.parse_args()
    if a.device:
        device(a.scene)
    else:
        paced(a.scene, a.switch, a.seconds, not a.active_only)


if __name__ == "__main__":
    main()
