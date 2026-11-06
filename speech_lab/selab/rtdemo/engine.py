"""Causal block-by-block streaming engine for the listening demo.

One Engine instance = one live stream.  Every call to process_block(xb) consumes exactly one 2 ms block
(B = 32 samples at 16 kHz) of the multichannel input, uses only that block and past state, and returns one block
of output for every enabled mode.  The SAME engine is used by
  * the pre-renderer (render.py: feeds the scene file block by block as fast as possible), and
  * the live paths (live.py: blocks paced by a real-time clock, or a sounddevice input/output callback),
so a pre-rendered track is the live output (checked bit-for-bit in render.py --verify / live.py).

Lab code reused, not rebuilt:
  EasyCom (glasses): selab.bf_r7.SDATF (ATF superdirective MVDR, ATF diffuse coherence, WNG floor; sqrt-Hann WOLA
      4 ms / 2 ms hop -> 4 ms latency), selab.bf_r7.DSTimeATF (head-fixed time-domain DS, 0.75 ms), tracker =
      selab.onset_r7.make_tracker('atf') (round-6 rtn tracker with ATF steering), head-prior hybrid = the logic of
      selab.bf_r7.hybrid run incrementally.  Round-7 frozen params: ref mic ch2 (index 1), WNG floor -6 dB,
      hybrid X = 20 deg, thr = 8; front mic ch2 (index 1).
  LibriCSS 7-mic / simulated 4-mic linear: selab.r6.STFTBF kind 'sd' 4 ms (WNG floor: round-6 frozen +6 dB on
      LibriCSS, round-7 frozen -6 dB on the 4-mic linear sim, see sd4_wng),
      selab.r6.DSTime, tracker selab.r6.Tracker(mode='rtn') (track+hysteresis, no ECAPA).

Filter choice: sd4 (4 ms) rather than sd8: round 7 froze its params on sd8, but 8 ms equals the hard cap and misses
the 5 ms target; sd4 is the same filter family at 4 ms.

Steering updates (tracker, every 16 ms on the newest 32 ms) select filter weights only; they add no audio delay.
"""
import time
import numpy as np
from ..common import FS
from .. import r6
from .anc_sim import StreamFIR, filters as anc_filters

B = 32                       # samples per block (2 ms)
FROZEN_R7 = dict(front=2, ref=1, wng_db=-6.0, X=20.0, thr=8.0)   # results/r7/frozen_r7.json (front is 1-based)
R6_SD4_WNG = 6.0                                                   # results/r6/holdout_choice.json sd4_rt w6


def sd4_wng(scene):
    """WNG floor: round-7 frozen -6 dB for the 4-mic arrays (EasyCom glasses, simulated 4-mic linear); round-6
    frozen +6 dB for the LibriCSS 7-mic circle (the array it was tuned on).  Note +6 dB on a 4-mic array is the
    delay-and-sum limit (10log10(4) = 6.02 dB), i.e. no superdirectivity at all."""
    return FROZEN_R7["wng_db"] if scene["array"] in ("easycom", "lin4") else R6_SD4_WNG

MODE_INFO = {
    "raw":     dict(label="Unprocessed front mic", steer="-", filt="none"),
    "ear":     dict(label="Unprocessed in-ear mics (avg ch5+6)", steer="-", filt="none"),
    "hs_ds":   dict(label="Head-steered delay-and-sum (0.7 ms)", steer="head", filt="ds_td"),
    "hs_sd4":  dict(label="Head-steered superdirective (4 ms)", steer="head", filt="sd4"),
    "trk_sd4": dict(label="Tracker-steered superdirective (4 ms)", steer="tracker", filt="sd4"),
    "hyb_sd4": dict(label="Head-prior hybrid tracker superdirective (4 ms)", steer="hybrid", filt="sd4"),
    "anc_sim": dict(label="SIMULATED noise-cut (not real ANC)", steer="-", filt="anc_sim"),
}


def angd(a, b):
    return (np.asarray(a) - np.asarray(b) + 180) % 360 - 180


class Limiter:
    """Causal block peak limiter, no look-ahead (adds no latency).  If a block's peak would exceed thr the gain
    drops immediately for the whole block (the block is already in hand, so this needs no future samples);
    recovery ramps linearly at `rel_db_s`."""

    def __init__(self, thr_db=-1.0, rel_db_s=20.0):
        self.thr = 10 ** (thr_db / 20); self.g = 1.0
        self.rel = 10 ** (rel_db_s * B / FS / 20)
        self.n_hits = 0

    def process(self, y):
        pk = float(np.max(np.abs(y))) if len(y) else 0.0
        need = 1.0 if pk <= self.thr else self.thr / pk
        if need < self.g:
            g1 = need; out = y * g1; self.n_hits += 1
        else:
            g1 = min(need, self.g * self.rel, 1.0)
            out = y * np.linspace(self.g, g1, len(y), endpoint=False) if g1 != self.g else y * g1
        self.g = g1
        return out


class Steering:
    """causal tracker + head-prior hybrid, updated every 256 samples on the newest 512 (round-6 framing)."""

    def __init__(self, scene, X=FROZEN_R7["X"], thr=FROZEN_R7["thr"], hyst=1.3, maxk=8):
        self.kind = scene["array"]
        self.head = float(scene["head_az_array"])
        if self.kind == "easycom":
            from ..onset_r7 import make_tracker
            self.tr = make_tracker("atf")
            self.chans = [0, 1, 2, 3]
        else:
            self.tr = r6.Tracker(np.asarray(scene["xy"]), mode="rtn")
            self.chans = list(range(len(scene["xy"])))
        self.buf = np.zeros((len(self.chans), r6.TN)); self.n = 0
        self.X, self.thr, self.hyst, self.maxk = X, thr, hyst, maxk
        self.uid = 0; self.lock = None
        self.trk_az = 0.0                         # bf_r7.run / r6.run_filter use az 0 before the first frame
        self.hyb_az = self.head; self.hyb_conf = False
        self.updated = False; self.t_last = 0.0

    def push(self, xb):
        """feed one block; runs a tracker step when a new 16 ms hop is complete."""
        self.buf = np.concatenate([self.buf[:, xb.shape[1]:], xb[self.chans]], 1); self.n += xb.shape[1]
        self.updated = False
        if self.n >= r6.TN and (self.n - r6.TN) % r6.TH == 0:
            t0 = time.perf_counter()
            a, _ = self.tr.step(self.buf)
            self.trk_az = float(a)
            self._hybrid()
            self.t_last = time.perf_counter() - t0; self.updated = True
        return self.updated

    def _hybrid(self):
        """incremental version of selab.bf_r7.hybrid (same rule) with the window centred on the head direction."""
        for t in self.tr.tracks:
            if "uid" not in t:
                t["uid"] = self.uid; self.uid += 1
        top = sorted(self.tr.tracks, key=lambda t: -t["cnt"])[: self.maxk]
        cand = [(t["uid"], t["az"], t["cnt"]) for t in top if abs(angd(t["az"], self.head)) <= self.X]
        if not cand:
            self.lock = None; self.hyb_az = self.head; self.hyb_conf = False; return
        u = [c[0] for c in cand]; a = [c[1] for c in cand]; c = [c[2] for c in cand]
        b = int(np.argmax(c))
        if self.lock not in u or c[b] > self.hyst * c[u.index(self.lock)]:
            self.lock = int(u[b])
        q = u.index(self.lock)
        if c[q] >= self.thr:
            self.hyb_az = float(a[q]); self.hyb_conf = True
        else:
            self.hyb_az = self.head; self.hyb_conf = False


class Engine:
    def __init__(self, scene, modes=None, limiter=True, precompute=True):
        self.scene = scene; self.kind = scene["array"]
        allm = ["raw", "hs_ds", "hs_sd4", "trk_sd4", "hyb_sd4", "anc_sim"]
        if self.kind == "easycom":
            allm.insert(1, "ear")
        self.modes = [m for m in (modes or allm) if m in allm]
        self.front = int(scene["front"])
        self.head = float(scene["head_az_array"])
        self.steer = Steering(scene) if any(m in self.modes for m in ("trk_sd4", "hyb_sd4")) else None
        self.f = {}
        for m in self.modes:
            if m in ("hs_sd4", "trk_sd4", "hyb_sd4"):
                if self.kind == "easycom":
                    from ..bf_r7 import SDATF
                    self.f[m] = SDATF(4, FROZEN_R7["ref"], FROZEN_R7["wng_db"])
                else:
                    self.f[m] = r6.STFTBF(np.asarray(scene["xy"]), win_ms=4, kind="sd", wng_db=sd4_wng(scene))
            elif m == "hs_ds":
                if self.kind == "easycom":
                    from ..bf_r7 import DSTimeATF
                    self.f[m] = DSTimeATF(FROZEN_R7["ref"], fixed=(0.0, 0.0))
                else:
                    self.f[m] = r6.DSTime(np.asarray(scene["xy"]))
            elif m == "anc_sim":
                F, self.anc_curves = anc_filters()
                st = scene.get("scene_type")
                if scene["kind"] == "sim":
                    self.anc_split = True
                    self.f[m] = (StreamFIR(F["companion"]), StreamFIR(F["traffic" if st == "traffic" else "babble"]))
                else:
                    self.anc_split = False
                    self.f[m] = StreamFIR(F["companion"])
        # Precompute the superdirective weight table for every 1-degree steering direction at start-up and share
        # it between the head / tracker / hybrid filters, so a steering change is a table lookup (a device would
        # store this table).  Lazily designing weights on a steering change costs 2-6 ms in this Python code,
        # i.e. more than the 2 ms block deadline.  The weights are the same deterministic function either way.
        self.t_precompute = 0.0
        sd = [m for m in self.modes if m in ("hs_sd4", "trk_sd4", "hyb_sd4")]
        if sd and precompute:
            t0 = time.perf_counter(); p0 = self.f[sd[0]]
            if self.kind == "easycom":
                for a in range(360):
                    p0.weights((a, 0))
                for m in sd[1:]:
                    self.f[m].cache = p0.cache
            else:
                for a in range(360):
                    p0.sd_weights(a)
                for m in sd[1:]:
                    self.f[m].sd_cache = p0.sd_cache
            self.t_precompute = time.perf_counter() - t0
        self.lim = {m: Limiter() for m in self.modes} if limiter else {}
        self.n = 0
        self.timing = {m: [] for m in self.modes}; self.t_steer = []
        self.steer_log = []          # (sample, trk_az_rel, hyb_az_rel, hyb_conf)

    # ---------------------------------------------------------------- latency (algorithmic, lab convention)
    def latency_ms(self, m):
        if m in ("raw", "ear", "anc_sim"):
            return 0.0
        if m == "hs_ds":
            return 1000 * self.f[m].latency_samples / FS
        return 1000 * self.f[m].latency_samples / FS

    def rel(self, az):
        return float(angd(az, self.head))

    def _bf(self, m, xb, az):
        p = self.f[m]
        if self.kind == "easycom":
            return p.hop(xb[:4], az, 0.0)
        return p.process_hop(xb, az, 1) if isinstance(p, r6.STFTBF) else p.process_hop(xb, az)

    def _one(self, m, xb, comps=None):
        """one block of one mode (filter + limiter); steering must already be updated for this block."""
        if m == "raw":
            y = xb[self.front].copy()
        elif m == "ear":
            y = 0.5 * (xb[4] + xb[5])
        elif m in ("hs_ds", "hs_sd4"):
            y = self._bf(m, xb, 0.0 if self.kind == "easycom" else self.head)
        elif m == "trk_sd4":
            y = self._bf(m, xb, self.steer.trk_az)
        elif m == "hyb_sd4":
            y = self._bf(m, xb, self.steer.hyb_az)
        elif m == "anc_sim":
            if self.anc_split and comps is not None:
                ft, fn = self.f[m]; y = ft.process(comps["target"]) + fn.process(comps["noise"])
            elif self.anc_split:
                raise ValueError("simulated scene needs comps for anc_sim")
            else:
                y = self.f[m].process(xb[self.front])
        else:
            raise KeyError(m)
        if m in self.lim:
            y = self.lim[m].process(y)
        return y

    def process_block(self, xb, comps=None, only=None):
        """xb (M,B) float64; comps = dict(target=(B,), noise=(B,)) front-mic images (simulated scenes only, used by
        anc_sim).  Returns dict mode -> (B,) output (after the limiter)."""
        assert xb.shape[1] == B
        out = {}
        if self.steer is not None:
            t0 = time.perf_counter(); up = self.steer.push(xb); dt = time.perf_counter() - t0
            if up:
                self.t_steer.append(dt)
                self.steer_log.append((self.n + B, self.rel(self.steer.trk_az), self.rel(self.steer.hyb_az),
                                       bool(self.steer.hyb_conf)))
        for m in (only or self.modes):
            t0 = time.perf_counter()
            y = self._one(m, xb, comps)
            self.timing[m].append(time.perf_counter() - t0)
            out[m] = y
        self.n += B
        return out


def load_scene(sid):
    import json, soundfile as sf
    from .scenes import OUTD
    d = OUTD / sid
    meta = json.load(open(d / "scene.json"))
    x, _ = sf.read(d / "mc.wav", dtype="float32"); x = x.T.astype(np.float64)
    comps = None
    if (d / "comp_target.wav").exists():
        comps = {k: sf.read(d / f"comp_{k}.wav", dtype="float32")[0].astype(np.float64) for k in ("target", "noise")}
    return meta, x, comps


def run_offline(meta, x, comps, modes=None, limiter=True, precompute=True):
    """feed the whole scene block by block (as fast as possible). Returns outputs (mode -> (n,)), engine."""
    eng = Engine(meta, modes, limiter, precompute)
    n = x.shape[1] // B * B
    outs = {m: np.zeros(n) for m in eng.modes}
    for i in range(0, n, B):
        cb = None if comps is None else {k: v[i:i + B] for k, v in comps.items()}
        o = eng.process_block(x[:, i:i + B], cb)
        for m, y in o.items():
            outs[m][i:i + B] = y
    return outs, eng
