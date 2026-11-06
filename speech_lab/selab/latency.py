"""Streaming-latency check (run on an otherwise idle machine).  python -m selab.latency
 - Classical STFT methods: algorithmic latency = window (32 ms); compute per 8 ms hop measured.
 - Demucs DNS64 via the package's own DemucsStreamer (true frame-by-frame causal inference):
   algorithmic latency = streamer.total_length / fs; compute time per stride measured.
Writes results/latency.json
"""
import json, time
import numpy as np
import torch
from .common import RES, FS, load, MIX
from . import classical

torch.set_num_threads(2)


def main():
    x = load(MIX / "r1" / "babble_snr+0_00" / "mix.wav")
    out = {}
    n_hops = len(x) / classical.HOP
    for name in ["specsub", "wiener_dd", "mmse_lsa"]:
        f = classical.METHODS[name]
        ts = []
        for _ in range(3):
            t0 = time.perf_counter(); f(x); ts.append(time.perf_counter() - t0)
        per_hop_ms = 1000 * min(ts) / n_hops
        out[name] = dict(algorithmic_latency_ms=classical.ALGO_LATENCY_MS, hop_ms=1000 * classical.HOP / FS,
                         compute_per_hop_ms=per_hop_ms, realtime_ok=per_hop_ms < 1000 * classical.HOP / FS)
    from denoiser.demucs import DemucsStreamer
    from .neural import demucs_dns64
    m = demucs_dns64()
    for nf in [1, 4]:
        st = DemucsStreamer(m, num_frames=nf)
        xt = torch.from_numpy(x)[None]
        chunks = []
        t0 = time.perf_counter()
        with torch.no_grad():
            for i in range(0, xt.shape[1], st.stride):
                chunks.append(st.feed(xt[:, i:i + st.stride]))
            chunks.append(st.flush())
        tot = time.perf_counter() - t0
        n_strides = xt.shape[1] / st.stride
        stride_ms = 1000 * st.stride / FS
        out[f"demucs_dns64_stream_nf{nf}"] = dict(
            algorithmic_latency_ms=1000 * st.total_length / FS, stride_ms=stride_ms,
            compute_per_stride_ms=1000 * tot / n_strides, rtf=tot / (len(x) / FS),
            realtime_ok=(1000 * tot / n_strides) < stride_ms,
            note="latency = buffered input needed before first output; add compute time per stride for end-to-end")
    out["machine"] = "2 vCPU aarch64 sandbox, torch threads=2, no GPU"
    (RES).mkdir(exist_ok=True)
    json.dump(out, open(RES / "latency.json", "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
