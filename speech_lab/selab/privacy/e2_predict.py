"""E2: how much does waveform prediction recover when system latency exceeds acoustic lead?
Predict x[n+h] from x[..n] for h = 0.5/1/2/5/10/50 ms on held-out LibriSpeech speakers.
Methods: none (x[n], i.e. latency uncompensated), best fixed gain, block-adaptive direct h-step LPC
(order 32, 32 ms window, 4 ms update), tiny causal MLP (CPU, minutes).
Metric: per-band residual power e=x-xhat relative to x, on speech-active samples (dB; negative=cancellation).
Run: nice -n 19 env OMP_NUM_THREADS=1 python -m selab.privacy.e2_predict [lpc|nn|all]
"""
import sys, time, numpy as np, torch
from .common_p import FS, BANDS, BAND_NAMES, speakers, concat_speaker, bandpass, save_json, load_json, OUT

HMS = [0.5, 1, 2, 5, 10, 50]
HS = [int(round(h * FS / 1000)) for h in HMS]
TEST_SPK = speakers()[20:26]
TRAIN_SPK = speakers()[:18]
TEST_SEC = 15
CTX = 256


def test_set():
    return {s: concat_speaker(s, TEST_SEC).astype(np.float64) for s in TEST_SPK}


def active_mask(x, frame=320):
    n = len(x) // frame
    e = np.array([np.mean(x[i * frame:(i + 1) * frame] ** 2) for i in range(n)])
    act = e > e.max() * 10 ** (-4)  # within 40 dB of loudest frame
    return np.repeat(act, frame)[: len(x)].tolist() + [False] * (len(x) - n * frame)


def band_nmse(x, xh, mask):
    mask = np.asarray(mask, bool); out = []
    for lo, hi in BANDS + [(100, 7900)]:
        xb = bandpass(x, lo, hi)[mask]; pb = bandpass(xh, lo, hi)[mask]
        raw = np.sum((xb - pb) ** 2) / np.sum(xb ** 2)
        g = np.dot(xb, pb) / (np.dot(pb, pb) + 1e-20)          # best per-band gain (oracle scalar)
        sc = np.sum((xb - g * pb) ** 2) / np.sum(xb ** 2)
        out.append((10 * np.log10(raw), 10 * np.log10(sc)))
    return out


def pred_none(x, h, gain=False):
    xh = np.zeros_like(x); xh[h:] = x[:-h]
    if gain:
        g = np.dot(x[h:], x[:-h]) / np.dot(x[:-h], x[:-h]); xh *= g
    return xh


def pred_lpc(x, h, p=32, win=512, hop=64):
    xh = np.zeros_like(x)
    for t in range(win + h + p, len(x) - h, hop):
        # training pairs: (x[n-p+1..n] -> x[n+h]) with n+h <= t-1
        ns = np.arange(t - h - win, t - h)
        X = np.stack([x[ns - k] for k in range(p)], 1); y = x[ns + h]
        lam = 1e-3 * (np.mean(X ** 2) + 1e-12) * len(ns)
        a = np.linalg.solve(X.T @ X + lam * np.eye(p), X.T @ y)
        nq = np.arange(t, min(t + hop, len(x) - h))
        Xq = np.stack([x[nq - k] for k in range(p)], 1)
        xh[nq + h] = Xq @ a
    return xh


class MLP(torch.nn.Module):
    def __init__(self, ctx=CTX, hid=256, nout=len(HS)):
        super().__init__()
        self.net = torch.nn.Sequential(torch.nn.Linear(ctx, hid), torch.nn.GELU(), torch.nn.Linear(hid, hid),
                                       torch.nn.GELU(), torch.nn.Linear(hid, nout))

    def forward(self, w):  # w: B x ctx (most recent last)
        s = w.pow(2).mean(1, keepdim=True).sqrt() + 1e-4
        return self.net(w / s) * s


def train_nn(minutes=6.0, chunk=95.0):
    """resumable: trains <= chunk seconds per call; returns (model, iters, done)."""
    torch.set_num_threads(1)
    ck = OUT / "e2_mlp_ckpt.pt"
    m = MLP(); opt = torch.optim.Adam(m.parameters(), 1e-3); it = 0; spent = 0.0
    if ck.exists():
        st = torch.load(ck); m.load_state_dict(st["m"]); opt.load_state_dict(st["o"]); it = st["it"]; spent = st["spent"]
    if spent >= minutes * 60:
        return m, it, True
    tr = np.concatenate([concat_speaker(s, 40) for s in TRAIN_SPK]).astype(np.float32)
    rng = np.random.default_rng(it); H = np.array(HS); mx = H.max()
    t0 = time.time()
    while time.time() - t0 < chunk and spent + (time.time() - t0) < minutes * 60:
        idx = rng.integers(CTX, len(tr) - mx - 1, 512)
        W = np.stack([tr[i - CTX:i] for i in idx]); Y = np.stack([tr[i - 1 + H] for i in idx])
        W = torch.from_numpy(W); Y = torch.from_numpy(Y)
        s = W.pow(2).mean(1, keepdim=True).sqrt() + 1e-4
        loss = (((m(W) - Y) / s) ** 2).mean()
        opt.zero_grad(); loss.backward(); opt.step(); it += 1
        if it % 500 == 0:
            print("nn it", it, float(loss), flush=True)
    spent += time.time() - t0
    torch.save({"m": m.state_dict(), "o": opt.state_dict(), "it": it, "spent": spent}, ck)
    return m, it, spent >= minutes * 60


def pred_nn(m, x):
    torch.set_num_threads(1)
    x32 = x.astype(np.float32); n = len(x)
    out = np.zeros((len(HS), n))
    with torch.no_grad():
        for st in range(CTX, n, 8192):
            idx = np.arange(st, min(st + 8192, n))
            W = torch.from_numpy(np.stack([x32[i - CTX + 1:i + 1] for i in idx]))  # window ending at n=i
            P = m(W).numpy()
            for j, h in enumerate(HS):
                ok = idx + h < n
                out[j, idx[ok] + h] = P[ok, j]
    return out


def main(which):
    res = load_json("e2_results.json") or {"bands": BAND_NAMES + ["100-7.9k"], "horizons_ms": HMS}
    T = test_set(); masks = {s: active_mask(x) for s, x in T.items()}
    if which in ("lpc", "all"):
        for h, hm in zip(HS, HMS):
            for meth in ("none", "lpc32"):
                key = f"{meth}|{hm}"
                if key in res:
                    continue
                rows = []
                for s, x in T.items():
                    xh = pred_none(x, h) if meth == "none" else pred_none(x, h, True) if meth == "gain" else pred_lpc(x, h)
                    rows.append(band_nmse(x, xh, masks[s]))
                A = np.mean(rows, 0)
                res[key] = A[:, 0].round(2).tolist(); res[key + "|scaled"] = A[:, 1].round(2).tolist(); save_json(res, "e2_results.json"); print(key, res[key], flush=True)
    if which in ("nn", "all") and "nn_mlp|0.5" not in res:
        m, it, done = train_nn(float(sys.argv[2]) if len(sys.argv) > 2 else 6.0)
        if not done:
            print("NN training chunk saved; rerun to continue", it, flush=True); return
        res["nn_train_iters"] = it; res["nn_train_minutes"] = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
        rows = {hm: [] for hm in HMS}
        for s, x in T.items():
            P = pred_nn(m, x)
            for j, hm in enumerate(HMS):
                rows[hm].append(band_nmse(x, P[j], masks[s]))
        for hm in HMS:
            A = np.mean(rows[hm], 0)
            res[f"nn_mlp|{hm}"] = A[:, 0].round(2).tolist(); res[f"nn_mlp|{hm}|scaled"] = A[:, 1].round(2).tolist()
        save_json(res, "e2_results.json"); print({k: v for k, v in res.items() if k.startswith("nn")}, flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
