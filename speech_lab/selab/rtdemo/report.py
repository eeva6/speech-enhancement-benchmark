"""Collect measured numbers into results/rtdemo/latency_compute.{csv,md} (no estimates: every number is read from
bench_*.json, timing/<scene>.json and live/<scene>_live.json)."""
import csv, glob, json
from pathlib import Path
from ..common import ROOT

R = ROOT / "results" / "rtdemo"
LABEL = {"raw": "unprocessed front mic", "ear": "unprocessed in-ear mics", "hs_ds": "head-steered DS (time domain)",
         "hs_sd4": "head-steered superdirective 4 ms", "trk_sd4": "tracker-steered superdirective 4 ms",
         "hyb_sd4": "head-prior hybrid tracker sd 4 ms", "anc_sim": "SIMULATED noise-cut (fixed FIR)"}
BLOCK_BUF = {"raw": 2.0, "ear": 2.0, "hs_ds": 2.0, "anc_sim": 2.0, "hs_sd4": 0.0, "trk_sd4": 0.0, "hyb_sd4": 0.0}


def main():
    rows = []
    md = ["# Latency and compute (measured on this sandbox)", ""]
    for bp in sorted(R.glob("bench_*.json")):
        b = json.load(open(bp))
        md += [f"## Isolated per-block benchmark `{bp.name}`", "",
               f"{b['n_blocks']} consecutive real 2 ms blocks per mode (fresh engine running only that mode, 1 s warm-up, "
               f"GC off), {b.get('cpu', '')} {b['nproc']} vCPU, nice {b['nice']}, OMP_NUM_THREADS={b['omp_threads']}. "
               f"Load average before {b['load_before'][0]:.2f}/{b['load_before'][1]:.2f}/{b['load_before'][2]:.2f}, "
               f"after {b['load_after'][0]:.2f}/{b['load_after'][1]:.2f}/{b['load_after'][2]:.2f}; "
               f"round-7 pipeline running: {b['r7_pipeline_running']} -> {b['r7_pipeline_running_after']}.", "",
               "| array | mode | alg. latency ms | + block buffer ms | compute/block mean | median | p95 | p99 | max (ms) | RTF mean | RTF p95 |",
               "|---|---|---|---|---|---|---|---|---|---|---|"]
        for arr, A in b["arrays"].items():
            for m, v in A["modes"].items():
                if m == "ALL_MODES":
                    continue
                k = v["block"]
                md.append(f"| {arr} | {LABEL.get(m, m)} | {v['latency_ms']:.2f} | {BLOCK_BUF[m]:.0f} | {k['mean']:.4f} | {k['median']:.4f} | "
                          f"{k['p95']:.4f} | {k['p99']:.4f} | {k['max']:.3f} | {v['rtf_mean']:.4f} | {v['rtf_p95']:.4f} |")
                rows.append(dict(source=bp.name, array=arr, mode=m, alg_latency_ms=round(v["latency_ms"], 3),
                                 block_buffer_ms=BLOCK_BUF[m], mean_ms=k["mean"], median_ms=k["median"], p95_ms=k["p95"],
                                 p99_ms=k["p99"], max_ms=k["max"], rtf_mean=v["rtf_mean"], load1=b["load_before"][0]))
            a = A["modes"]["ALL_MODES"]; k = a["block"]; t = a["tracker_step"]
            md.append(f"| {arr} | **all modes at once** (live path) | - | - | {k['mean']:.4f} | {k['median']:.4f} | {k['p95']:.4f} | "
                      f"{k['p99']:.4f} | {k['max']:.3f} | {a['rtf_mean']:.4f} | - |")
            md.append(f"| {arr} | tracker step (every 16 ms, shared by trk/hyb) | 0 (control only) | - | {t['mean']:.4f} | {t['median']:.4f} | "
                      f"{t['p95']:.4f} | {t['p99']:.4f} | {t['max']:.3f} | {a['tracker_rtf_mean']:.4f} | - |")
            md.append(f"| {arr} | **total live engine (all modes + tracker)** | | | | | | | | **{a['total_rtf_mean']:.4f}** | |")
            rows.append(dict(source=bp.name, array=arr, mode="ALL_MODES+tracker", mean_ms=k["mean"], median_ms=k["median"],
                             p95_ms=k["p95"], p99_ms=k["p99"], max_ms=k["max"], rtf_mean=a["total_rtf_mean"], load1=b["load_before"][0]))
        md.append("")
    md += ["## Under load: during the pre-render of each scene (all modes in one engine)", "",
           "| scene | load avg (1 min) | mode | mean | p95 | p99 | max (ms) | RTF mean |", "|---|---|---|---|---|---|---|---|"]
    for tp in sorted((R / "timing").glob("*.json")):
        t = json.load(open(tp))
        for m, v in t["modes"].items():
            md.append(f"| {t['scene']} | {t['load_before'][0]:.2f} | {m} | {v['mean']:.4f} | {v['p95']:.4f} | {v['p99']:.4f} | {v['max']:.3f} | {v['rtf_mean']:.4f} |")
        if t.get("steer"):
            s = t["steer"]; md.append(f"| {t['scene']} | | tracker step | {s['mean']:.3f} | {s['p95']:.3f} | {s['p99']:.3f} | {s['max']:.2f} | {s['rtf_mean']:.4f} |")
    md += ["", "## Live paced loop (selab.rtdemo.live)", "",
           "| scene | nice | load avg before | blocks | compute mean / p95 / max (ms) | arrival-to-output p95 / max (ms) | deadline misses | RTF | bit-identical to pre-render |",
           "|---|---|---|---|---|---|---|---|---|"]
    for lp in sorted((R / "live").glob("*_live*.json")):
        l = json.load(open(lp)); c = l["compute_ms"]; a = l["arrival_to_output_ms"]
        md.append(f"| {l['scene']} ({lp.stem}) | {l['nice']} | {l['load_before'][0]:.2f} | {l['blocks']} | {c['mean']:.3f} / {c['p95']:.3f} / {c['max']:.2f} | "
                  f"{a['p95']:.3f} / {a['max']:.2f} | {l['deadline_misses']} ({100 * l['miss_frac']:.1f}%) | {l['rtf_mean']:.3f} | {l['bit_identical_to_prerender']} |")
    (R / "latency_compute.md").write_text("\n".join(md) + "\n")
    if rows:
        keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
        with open(R / "latency_compute.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print("\n".join(md))


if __name__ == "__main__":
    main()
