"""Results tables for ab_set.md from summary.json / group_summary.json / metrics_items.csv.
python -m selab.venture_ab.tables  -> OUTW/ab_set_tables.md
"""
import json
import pandas as pd
from .build import OUTW

LAB = {"causal_trk_sd8": "A1 causal 8 ms, self-steering (deployable)", "causal_ref_sd8": "A2 causal 8 ms, ORACLE direction",
       "r5_ds32": "A3 DS 32 ms, blind direction (non-causal steering)", "oracle_mvdr": "A4 ORACLE MVDR (upper bound)",
       "anc_sim": "C SIMULATED ANC at ear", "sector_sd8": "G1 causal 8 ms, user-chosen sector", "sector_ds32": "G2 DS 32 ms, user-chosen sector",
       "oracle_mwf": "G3 ORACLE MWF (upper bound)"}
COLS = [("snr", "ΔSNR dB", 1, 1), ("sir_ov", "ΔB ratio dB", 1, 1), ("snr_noise", "Δ vs noise dB", 1, 1),
        ("si_sdr", "ΔSI-SDR dB", 1, 1), ("stoi", "ΔSTOI", 3, 1), ("estoi", "ΔESTOI", 3, 1), ("word_correct", "Δword-correct (pts)", 0, 100)]


def cell(d, k, mul):
    if not d:
        return "n/a"
    f = lambda v: f"{v * mul:+.{k}f}"
    return f"{f(d['median'])} [{f(d['min'])}, {f(d['max'])}]; mean {f(d['mean'])} (CI {f(d['ci95'][0])}, {f(d['ci95'][1])})"


def table(S, modes):
    h = "| mode | n | " + " | ".join(c[1] for c in COLS) + " |\n|" + "---|" * (len(COLS) + 2) + "\n"
    for m in modes:
        s = S.get(m, {})
        h += f"| {LAB.get(m, m)} | {s.get('n', 0)} | " + " | ".join(cell(s.get('d_' + c), k, mul) for c, _, k, mul in COLS) + " |\n"
    return h


def main():
    S = json.load(open(OUTW / "summary.json"))
    out = "Cells: median [min, max] over clips; mean with 95% cluster-bootstrap CI over recordings.\n\n"
    for k, lab in (("selected12", "Single-target, pre-registered 12 clips"), ("pool21", "Single-target, whole eligible pool (21)")):
        out += f"### {lab}\n\n" + table(S[k], ["causal_trk_sd8", "causal_ref_sd8", "r5_ds32", "oracle_mvdr", "anc_sim"])
        raw = S[k].get("raw", {})
        out += (f"\nUnprocessed medians: SNR {raw.get('snr_abs_median', float('nan')):.1f} dB, target-vs-talker {raw.get('sir_ov_abs_median', float('nan')):.1f} dB, "
                f"word-correct {raw.get('word_correct_abs_median', float('nan')):.2f}; target-image-alone word-correct median {S[k].get('target_ref_word_correct_median', float('nan')):.2f}.\n\n")
    p = OUTW / "group_summary.json"
    if p.exists():
        out += "### Group (sector) clips\n\n" + table(json.load(open(p)), ["sector_sd8", "sector_ds32", "oracle_mwf", "anc_sim"])
    o = pd.read_csv(OUTW / "metrics_items.csv")
    o = o[o["selected"]]
    pv = o.pivot_table(index="id", columns="mode", values=["d_snr", "d_sir_ov", "d_word_correct"])
    out += "\n### Per clip (selected 12): ΔSNR / ΔB / Δword-correct\n\n| clip | A1 causal trk | A2 causal ORACLE-dir | A3 DS32 | A4 ORACLE MVDR | C SIM ANC |\n|---|---|---|---|---|---|\n"
    for iid in pv.index:
        c = []
        for m in ["causal_trk_sd8", "causal_ref_sd8", "r5_ds32", "oracle_mvdr", "anc_sim"]:
            v = [pv.loc[iid, (q, m)] if (q, m) in pv.columns else float("nan") for q in ("d_snr", "d_sir_ov", "d_word_correct")]
            c.append(f"{v[0]:+.1f} / {v[1]:+.1f} / {100 * v[2]:+.0f}")
        out += f"| {iid} | " + " | ".join(c) + " |\n"
    gp = OUTW / "group_metrics_items.csv"
    if gp.exists():
        g = pd.read_csv(gp)
        pv = g.pivot_table(index="id", columns="mode", values=["d_snr", "d_sir_ov", "d_word_correct"])
        out += "\n### Per group clip: ΔSNR / ΔB(group vs others) / Δword-correct\n\n| clip | G1 sector sd8 | G2 sector DS32 | G3 ORACLE MWF | C SIM ANC |\n|---|---|---|---|---|\n"
        for iid in pv.index:
            c = []
            for m in ["sector_sd8", "sector_ds32", "oracle_mwf", "anc_sim"]:
                v = [pv.loc[iid, (q, m)] if (q, m) in pv.columns else float("nan") for q in ("d_snr", "d_sir_ov", "d_word_correct")]
                c.append(f"{v[0]:+.1f} / {v[1]:+.1f} / {100 * v[2]:+.0f}")
            out += f"| {iid} | " + " | ".join(c) + " |\n"
    (OUTW / "ab_set_tables.md").write_text(out)
    print(out)


if __name__ == "__main__":
    main()
