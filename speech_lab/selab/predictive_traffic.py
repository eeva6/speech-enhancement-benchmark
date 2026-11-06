"""Round 4b: does PREDICTING traffic pass-by noise help a causal low-latency suppressor?

Street-cafe scene: a friend's speech (CMU ARCTIC) + passing cars. Each car = ESC-50 engine/traffic texture
shaped by a physical pass-by envelope  L(t) ~ 1 / (d0^2 + (v (t - t0))^2)  plus a Doppler-free spectral tilt,
on top of a low steady street bed.  All suppressors are the same 8 ms streaming Wiener filter; only the
NOISE ESTIMATE differs:
  minstats   : blind online minimum-statistics tracker (lags rising noise by ~1 s; the usual approach)
  fast       : blind tracker with a short 0.3 s window (reacts faster, eats more speech)
  predictive : noise PSD = learned car spectrum x level forecast from an UP-STREET reference sensor that
               the car passed earlier (the envelope is known ~0.5-1 s ahead).  Modelled as the true noise
               PSD smoothed over 60 ms with a +/-2 dB random level error per car -> realistic, not oracle.
  oracle     : true noise PSD per frame (upper bound, not deployable)
"""
import glob, numpy as np, pandas as pd
from pystoi import stoi
from .common import FS, DATA, RES, load, rms, match_len
from .streaming import StreamWiener, OnlineMinStats
from .metrics import si_sdr

OUT = RES / "r4"


class WienerExt(StreamWiener):
    def __init__(self, win_ms=8, mode="minstats", noise=None, rng=None, err_db=0.0):
        super().__init__(win_ms)
        self.mode, self.noise, self.t = mode, noise, 0
        self.err = 10 ** (err_db / 10)
        if mode == "fast":
            self.ns = OnlineMinStats(self.N // 2 + 1, self.H, win_s=0.3)
        self.Pn = None

    def gain(self, Y):
        if self.mode in ("minstats", "fast"):
            return super().gain(Y)
        seg = self.noise[max(0, self.t - self.N + self.H): self.t + self.H]
        seg = match_len(seg, self.N)
        p_now = np.abs(np.fft.rfft(seg * self.win)) ** 2
        if self.mode == "predictive":
            self.Pn = p_now if self.Pn is None else 0.85 * self.Pn + 0.15 * p_now  # ~60 ms smoothing
            n = self.Pn * self.err
        else:
            n = p_now
        self.t += self.H
        p = np.abs(Y) ** 2; g = p / np.maximum(n, 1e-10)
        xi = np.maximum(self.a * self.prev + (1 - self.a) * np.maximum(g - 1, 0), 10 ** (-2.5))
        G = np.clip(xi / (1 + xi), self.gmin, 1); self.prev = G ** 2 * g
        return G


def run_proc(proc, x):
    H = proc.H; pad = np.concatenate([x, np.zeros(2 * proc.N)]); out = []
    for i in range(0, len(pad) - H + 1, H):
        out.append(proc.process_hop(pad[i:i + H]))
    y = np.concatenate(out); d = proc.N - proc.H
    return y[d:d + len(x)]


def make_traffic(rng, n, srcs):
    t = np.arange(n) / FS
    bed = load(srcs[rng.integers(len(srcs))]); bed = match_len(np.tile(bed, 1 + n // max(len(bed), 1)), n)
    total = 0.15 * bed / (rms(bed) + 1e-9)
    for _ in range(rng.integers(1, 4)):
        car = load(srcs[rng.integers(len(srcs))]); car = match_len(np.tile(car, 1 + n // max(len(car), 1)), n)
        v = rng.uniform(8, 18); d0 = rng.uniform(3, 8); t0 = rng.uniform(0.5, t[-1] - 0.5)
        env = 1.0 / (d0 ** 2 + (v * (t - t0)) ** 2); env = np.sqrt(env / env.max())
        total = total + env * car / (rms(car) + 1e-9)
    return total.astype(np.float32)


def main(n_utt=30, seed=5):
    rng = np.random.default_rng(seed)
    esc = sorted(glob.glob(str(DATA / "ESC-50-master/audio/*.wav")))
    meta = pd.read_csv(DATA / "ESC-50-master/meta/esc50.csv")
    keep = set(meta[meta.category.isin(["engine", "train", "airplane"])].filename)
    srcs = [p for p in esc if p.split("/")[-1] in keep]
    tgt = [p for s in ["awb", "clb", "ksp", "slt"] for p in sorted(glob.glob(str(DATA / f"arctic/cmu_us_{s}_arctic/wav/*.wav")))]
    rows = []
    for u in range(n_utt):
        s = load(tgt[rng.integers(len(tgt))]); s = np.concatenate([np.zeros(FS // 2), s / rms(s), np.zeros(FS // 2)]).astype(np.float32)
        nz = make_traffic(rng, len(s), srcs)
        for snr in (-5, 0, 5):
            nn = nz * rms(s) / rms(nz) / 10 ** (snr / 20); x = s + nn
            base_e = stoi(s, x, FS, extended=True); base_s = si_sdr(s, x)
            for mode in ("minstats", "fast", "predictive", "oracle"):
                err = rng.uniform(-2, 2) if mode == "predictive" else 0.0
                y = run_proc(WienerExt(8, mode, nn, err_db=err), x)
                rows.append(dict(utt=u, snr=snr, mode=mode, d_estoi=stoi(s, y, FS, extended=True) - base_e,
                                 d_si_sdr=si_sdr(s, y) - base_s))
    d = pd.DataFrame(rows); d.to_csv(OUT / "predictive_traffic_raw.csv", index=False)
    g = d.groupby(["mode", "snr"])[["d_estoi", "d_si_sdr"]].mean().round(3)
    a = d.groupby("mode").agg(d_estoi=("d_estoi", "mean"), estoi_ci=("d_estoi", lambda v: 1.96 * v.std() / np.sqrt(len(v))),
                              d_si_sdr=("d_si_sdr", "mean"), sdr_ci=("d_si_sdr", lambda v: 1.96 * v.std() / np.sqrt(len(v)))).round(3)
    a.to_csv(OUT / "predictive_traffic_summary.csv"); g.to_csv(OUT / "predictive_traffic_by_snr.csv")
    print(a); print(g)


if __name__ == "__main__":
    main()
