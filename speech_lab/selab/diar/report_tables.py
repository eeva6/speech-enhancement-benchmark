"""Markdown tables for results.md from results/diar/test_*.csv (python -m selab.diar.report_tables > results/diar/tables.md)."""
import json
import pandas as pd
from ..common import RES

OUT = RES / "diar"
ORDER = ["platform", "A_spectral", "A_ahc", "A_spectral_oracleK", "A_spectral_oracleVAD", "A_ahc_oracleVAD",
         "B_spatial_spectral", "B_spatial_ahc", "B_spatial_spectral_oracleVAD", "B_head_rawDOA", "B_world_poseOracle",
         "B_max_poseOracle", "B_head_rawDOA_oracleVAD", "B_max_poseOracle_oracleVAD", "B_gated_spectral", "B_gated_ahc",
         "B_gated_spectral_oracleVAD", "B_gated_ahc_oracleVAD"]


def pct(x):
    return "" if pd.isna(x) else f"{100 * x:.1f}"


def main():
    s = pd.read_csv(OUT / "test_summary.csv")
    for ds in ("libricss", "easycom"):
        d = s[s.ds == ds].set_index("variant")
        d = d.loc[[v for v in ORDER if v in d.index]]
        print(f"\n### {ds} (test)\n")
        print("| variant | DER c0.25 | DER c0 | miss | FA | conf | JER | spk count err (abs / signed) | cpWER | WER (speaker-agnostic) |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for v, r in d.iterrows():
            print(f"| {v} | {pct(r.DER_c25)} | {pct(r.DER_c0)} | {pct(r.miss_c0)} | {pct(r.fa_c0)} | {pct(r.conf_c0)} | {pct(r.JER)} | "
                  f"{r.spk_abs_err:.2f} / {r.spk_signed:+.2f} | {pct(r.cpWER)} | {pct(r.WER_all)} |")
    p = OUT / "test_libricss_by_condition.csv"
    if p.exists():
        c = pd.read_csv(p).set_index("variant")
        c = c.loc[[v for v in ORDER if v in c.index]]
        print("\n### LibriCSS DER (collar 0, overlap scored) by overlap condition\n")
        print("| variant | " + " | ".join(c.columns) + " |"); print("|---|" + "---|" * len(c.columns))
        for v, r in c.iterrows():
            print(f"| {v} | " + " | ".join(pct(x) for x in r.values) + " |")
    p = OUT / "test_failure_frames.csv"
    if p.exists():
        f = pd.read_csv(p).groupby(["ds", "variant"]).mean(numeric_only=True).reset_index()
        print("\n### Failure breakdown (collar 0)\n")
        print("| dataset | variant | DER single-talker frames | DER overlap frames | overlap share of ref speech | acc turns <1 s | 1-3 s | >3 s |")
        print("|---|---|---|---|---|---|---|---|")
        for _, r in f.iterrows():
            print(f"| {r.ds} | {r.variant} | {pct(r.der_single)} | {pct(r.der_overlap)} | {pct(r.share_overlap)} | "
                  f"{pct(r['acc_turn<1s'])} | {pct(r['acc_turn1-3s'])} | {pct(r['acc_turn>3s'])} |")
    p = OUT / "test_rows.csv"
    if p.exists():
        t = pd.read_csv(p)
        k = t[t.variant.isin(["A_spectral", "A_ahc", "B_spatial_spectral"])].pivot_table(index="uri", columns="variant", values="n_hyp")
        k["n_ref"] = t.groupby("uri").n_ref.first()
        print("\n### Speaker-count estimates per test recording (clusters with >= 5 s)\n")
        print("| recording | n_ref | " + " | ".join(c for c in k.columns if c != "n_ref") + " |")
        print("|---|---|" + "---|" * (len(k.columns) - 1))
        for u, r in k.iterrows():
            print(f"| {u} | {int(r.n_ref)} | " + " | ".join(str(int(r[c])) for c in k.columns if c != "n_ref") + " |")
    p = OUT / "test_enrol_naming.csv"
    if p.exists():
        e = pd.read_csv(p)
        print("\n### Enrolment-based naming (LibriCSS test, A_spectral; first utterance of each speaker as enrolment)\n")
        print(f"Mean over {len(e)} sessions: DER with optimal mapping {pct(e.der_opt.mean())}, DER with names imposed {pct(e.der_named.mean())}, "
              f"clusters named {e.n_named.sum()}/{e.n_clusters.sum()} (reference speakers {e.n_ref.sum()}).")
    p = OUT / "rtf.csv"
    if p.exists():
        r = pd.read_csv(p)
        print("\n### Runtime (1 CPU thread, nice 19, shared 2-vCPU box; RTF = compute s / audio s)\n")
        print("| dataset | stage | audio min | RTF |"); print("|---|---|---|---|")
        for _, x in r.iterrows():
            print(f"| {x.ds} | {x.stage} | {x.dur / 60:.0f} | {x.rtf:.3f} |")


if __name__ == "__main__":
    main()
