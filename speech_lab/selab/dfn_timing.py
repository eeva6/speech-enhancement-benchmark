"""Round 5: DeepFilterNet3 frame-by-frame streaming timing through its real-time Rust path.

Uses the libDF C API (third_party/df_bin/libdf.so, built by scripts/build_dfn_rust.sh) via ctypes:
df_create(DeepFilterNet3_onnx.tar.gz) then df_process_frame() once per 10-ms hop (480 samples @ 48 kHz),
timing every call with perf_counter_ns. ctypes call overhead (measured with a no-op-sized numpy copy) is
reported separately.  Also runs the `deep-filter` CLI (whole-file, tract streaming loop) for its own RTF, and
checks that the C-API output matches the Python `df.enhance` output (SI-SDR between the two, after delay
alignment), so the timing is of the same model that was benchmarked.
Latency budget = algorithmic (STFT window 20 ms + lookahead from config) + per-frame compute.
python -m selab.dfn_timing  ->  results/r5/dfn3_timing.json, results/r5/figs/dfn3_frame_times.png
"""
import ctypes, json, os, subprocess, time, glob
import numpy as np
from scipy.signal import resample_poly
from .common import ROOT, RES, MIX, load

BIN = ROOT / "third_party" / "df_bin"
MODEL = ROOT / "third_party" / "DeepFilterNet" / "models" / "DeepFilterNet3_onnx.tar.gz"


def loadavg():
    return os.getloadavg()


def cli_rtf(out, files):
    """whole-file RTF of the Rust `deep-filter` CLI (tract, frame-by-frame internally), 6 files, 48 kHz PCM16,
    input gain-staged to -26 dBFS RMS like the benchmark."""
    cli = BIN / "deep-filter"
    if not cli.exists():
        out["cli"] = "deep-filter binary missing"; return
    import tempfile, soundfile as sf
    td = tempfile.mkdtemp(); wavs = []
    for f in files[:6]:
        x = load(f); x = 0.05 * x / (np.sqrt(np.mean(x ** 2)) + 1e-9)
        p = os.path.join(td, os.path.basename(os.path.dirname(f)) + ".wav")
        sf.write(p, resample_poly(x, 3, 1).astype(np.float32), 48000, subtype="PCM_16"); wavs.append(p)
    la0 = os.getloadavg()[0]; t = time.perf_counter(); c0 = os.times()
    r = subprocess.run([str(cli), "-m", str(MODEL), "-o", os.path.join(td, "out")] + wavs, capture_output=True, text=True, timeout=900)
    c1 = os.times(); wall = time.perf_counter() - t
    aud = float(sum(sf.info(w).duration for w in wavs))
    cpu = (c1.children_user - c0.children_user) + (c1.children_system - c0.children_system)
    out["cli"] = dict(wall_s=wall, cpu_s=cpu, audio_s=aud, rtf_wall=wall / aud, rtf_cpu=cpu / aud, loadavg_1min_before=la0,
                      note="includes model load (once per run) and WAV I/O", stderr_tail=(r.stderr or r.stdout)[-1200:], returncode=r.returncode)


def main(n_files=12, repeats=1):
    out = dict(model=str(MODEL.name), cpu="2 vCPU aarch64 (shared sandbox; load average recorded)")
    lib = BIN / "libdf.so"
    if not lib.exists():
        out["blocker"] = "libdf.so not built (see logs/r5_dfn_build*.log); per-frame C-API timing not measured"
        cli_rtf(out, sorted(glob.glob(str(MIX / "r5" / "*" / "mix.wav")))[:n_files])
        json.dump(out, open(RES / "r5" / "dfn3_timing.json", "w"), indent=1); print(json.dumps(out, indent=1)); return
    L = ctypes.CDLL(str(lib))
    L.df_create.restype = ctypes.c_void_p; L.df_create.argtypes = [ctypes.c_char_p, ctypes.c_float, ctypes.c_char_p]
    L.df_get_frame_length.restype = ctypes.c_size_t; L.df_get_frame_length.argtypes = [ctypes.c_void_p]
    L.df_process_frame.restype = ctypes.c_float
    L.df_process_frame.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]
    t0 = time.perf_counter()
    st = L.df_create(str(MODEL).encode(), ctypes.c_float(100.0), None)
    out["create_s"] = time.perf_counter() - t0
    H = int(L.df_get_frame_length(st)); out["hop_samples_48k"] = H; out["hop_ms"] = 1000 * H / 48000
    files = sorted(glob.glob(str(MIX / "r5" / "*" / "mix.wav")))[:n_files]
    times, la = [], []
    outs = {}
    for f in files:
        x0 = load(f); x0 = 0.05 * x0 / (np.sqrt(np.mean(x0 ** 2)) + 1e-9)   # gain-staged to -26 dBFS like the benchmark
        x = resample_poly(x0, 3, 1).astype(np.float32)
        n = len(x) // H * H
        y = np.zeros(n, np.float32)
        ib = np.zeros(H, np.float32); ob = np.zeros(H, np.float32)
        ip = ib.ctypes.data_as(ctypes.POINTER(ctypes.c_float)); op = ob.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        la.append(loadavg()[0])
        for i in range(0, n, H):
            ib[:] = x[i:i + H]
            t = time.perf_counter_ns(); L.df_process_frame(st, ip, op); times.append(time.perf_counter_ns() - t)
            y[i:i + H] = ob
        outs[f] = (x[:n], y)
    # ctypes + copy overhead with a trivial C call
    tt = []
    for _ in range(2000):
        t = time.perf_counter_ns(); L.df_get_frame_length(st); tt.append(time.perf_counter_ns() - t)
    ms = np.array(times) / 1e6
    out.update(n_frames=int(len(ms)), n_files=len(files), audio_s=float(len(ms) * H / 48000),
               frame_ms=dict(mean=float(ms.mean()), median=float(np.median(ms)), p95=float(np.percentile(ms, 95)),
                             p99=float(np.percentile(ms, 99)), max=float(ms.max()), first10_mean=float(ms[:10].mean())),
               rtf_frames=float(ms.sum() / (len(ms) * 1000 * H / 48000)),
               frac_frames_over_hop=float(np.mean(ms > 1000 * H / 48000)),
               ctypes_overhead_us=float(np.median(tt) / 1e3), loadavg_1min_during=float(np.mean(la)))
    # delay of the C-API path vs input (cross-correlation) and agreement with the Python enhance() used in the benchmark
    try:
        from .neural import run_deepfilternet
        f = files[0]; x48, y48 = outs[f]
        c = np.correlate(y48[:48000 * 3], x48[:48000 * 3], "full"); d = int(np.argmax(c) - (48000 * 3 - 1))
        out["capi_output_delay_samples_48k"] = d; out["capi_output_delay_ms"] = 1000 * d / 48000
        x0 = load(f); x0 = 0.05 * x0 / (np.sqrt(np.mean(x0 ** 2)) + 1e-9)
        yp = resample_poly(run_deepfilternet(x0), 3, 1).astype(np.float32)
        yc = y48[d:]; m = min(len(yc), len(yp)); a, b = yp[:m], yc[:m]
        al = np.dot(b, a) / (np.dot(a, a) + 1e-12)
        out["capi_vs_python_si_sdr_db"] = float(10 * np.log10(np.sum((al * a) ** 2) / (np.sum((b - al * a) ** 2) + 1e-12)))
    except Exception as e:
        out["capi_vs_python_error"] = repr(e)
    # config latency
    import configparser
    cfgp = ROOT / "models" / "df" / "DeepFilterNet3" / "config.ini"
    if cfgp.exists():
        cp = configparser.ConfigParser(); cp.read(cfgp)
        fft = int(cp["df"]["fft_size"]); hop = int(cp["df"]["hop_size"]); sr = int(cp["df"]["sr"])
        la_ = max(int(cp["deepfilternet"].get("conv_lookahead", 0)), int(cp["df"].get("df_lookahead", cp["deepfilternet"].get("df_lookahead", 0))))
        out["config"] = dict(sr=sr, fft_size=fft, hop_size=hop, lookahead_frames=la_,
                             algorithmic_latency_ms=1000 * (fft - hop) / sr + 1000 * la_ * hop / sr + 1000 * hop / sr)
        out["config"]["note"] = "algorithmic = (fft-hop) analysis/synthesis overlap + lookahead*hop + one hop of buffering"
        p99 = out["frame_ms"]["p99"]
        out["end_to_end_latency_ms_estimate"] = dict(algorithmic=out["config"]["algorithmic_latency_ms"],
                                                     plus_p99_compute=out["config"]["algorithmic_latency_ms"] + p99)
    cli_rtf(out, files)
    json.dump(out, open(RES / "r5" / "dfn3_timing.json", "w"), indent=1)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    (RES / "r5" / "figs").mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.hist(ms, bins=80, color="#1f5fa8"); ax.axvline(1000 * H / 48000, color="r", ls="--", label="hop = real-time deadline (10 ms)")
    ax.set_yscale("log"); ax.set_xlabel("df_process_frame compute time per 10-ms frame (ms)"); ax.set_ylabel("frames")
    ax.set_title("DeepFilterNet3 via libDF C API, 2 vCPU aarch64"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(RES / "r5" / "figs" / "dfn3_frame_times.png", dpi=130)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
