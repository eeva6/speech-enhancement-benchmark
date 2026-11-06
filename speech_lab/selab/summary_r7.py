"""Write results/r7/summary_r7.md from analyze_r7 outputs (asr_test.csv, asr_wer_test.csv, obj_test.csv, steer_test.csv),
frozen_r7.json and timing_r7_summary.csv (if present).  python -m selab.summary_r7"""
import json
import numpy as np, pandas as pd
from .common import RES
from .analyze_r7 import LABEL, FINAL

R7 = RES / "r7"


def f(e, lo, hi, p=3):
    return "" if pd.isna(e) else f"{e:+.{p}f} [{lo:+.{p}f}, {hi:+.{p}f}]"


def ptxt(p):
    return "" if pd.isna(p) else (f"{p:.3f}" if p >= 0.001 else "<0.001")


def main():
    L = ["# Round 7 phase 2 summary: ATF beamformers + ASR on EasyCom (test sessions 10, 11)", "",
         "EasyCom is CC-BY-NC 4.0 (research only); no audio in any deliverable.", ""]
    fz = json.load(open(R7 / "frozen_r7.json"))
    L += ["## Frozen parameters (tuned on val sub300, frozen before test)", "",
          f"- front mic: ch{fz['front']}; reference mic: ch{fz['ref'] + 1}; WNG floor: {fz['wng_db']:+.0f} dB; hybrid window ±{fz['X']:.0f}°, confidence threshold {fz['thr']:.0f} (decayed dominant-frame count)",
          f"- frozen at {fz.get('frozen_at_utc')} UTC; rule: {fz.get('rule')}",
          f"- val word-correct: front {fz.get('front_choice')}; ref mic {fz.get('ref_choice')}; WNG {fz.get('wng_choice')}; hybrid {fz.get('hyb_choice')}", ""]
    T = pd.read_csv(R7 / "asr_test.csv")
    for g, title in (("all", "All test items with words (align_suspect kept)"), ("all_noSuspect", "Without align_suspect items"),
                     ("overlap", "Overlapped items"), ("no_overlap", "Non-overlapped items"), ("to_wearer", "Addressed to the wearer"),
                     ("to_group", "Addressed to the group"), ("to_other", "Target: other"), ("to_none", "Target: none"),
                     ("onset<0.5s", "< 0.5 s since turn onset"), ("onset0.5-2s", "0.5-2 s since turn onset"), ("onset>2s", "> 2 s since turn onset")):
        s = T[T.group == g]
        if s.empty:
            continue
        L += [f"## Word-correct, {title} (n = {int(s.n.max())})", "",
              "| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |", "|---|---|---|---|---|---|"]
        for me in FINAL:
            r = s[s.method == me]
            if r.empty:
                continue
            r = r.iloc[0]
            L.append(f"| {LABEL.get(me, me)} | {r['mean']:.3f} | {f(r.get('d_front'), r.get('d_front_lo'), r.get('d_front_hi'))} | {ptxt(r.get('p_front_holm'))} | "
                     f"{f(r.get('d_r5ds'), r.get('d_r5ds_lo'), r.get('d_r5ds_hi'))} | {ptxt(r.get('p_r5ds_holm'))} |")
        L.append("")
    try:
        O = pd.read_csv(R7 / "obj_test.csv")
        for met in ("si_sdr", "estoi"):
            s = O[(O.metric == met) & (O.group == "all")]
            L += [f"## {met.upper()} (align_suspect excluded, n = {int(s.n.max())})", "", "| method | mean | Δ vs unproc_front [95% CI] | Δ vs R5 DS |", "|---|---|---|---|"]
            for me in FINAL:
                r = s[s.method == me]
                if r.empty:
                    continue
                r = r.iloc[0]; p = 2 if met == "si_sdr" else 3
                L.append(f"| {LABEL.get(me, me)} | {r['mean']:.{p}f} | {f(r.get('d_front'), r.get('d_front_lo'), r.get('d_front_hi'), p)} | {f(r.get('d_r5ds'), r.get('d_r5ds_lo'), r.get('d_r5ds_hi'), p)} |")
            L.append("")
    except FileNotFoundError:
        pass
    try:
        S = pd.read_csv(R7 / "steer_test.csv")
        L += ["## Steering error (median per item, deg) vs word-correct gain", "", S.round(3).to_markdown(index=False), ""]
    except FileNotFoundError:
        pass
    try:
        G = pd.read_csv(R7 / "timing_r7_summary.csv")
        L += ["## Compute per hop (single thread, weight tables precomputed)", "", G.round(4).to_markdown(index=False), ""]
    except FileNotFoundError:
        L += ["## Compute per hop", "", "Not yet measured on an idle machine (python -m selab.timing_r7).", ""]
    (R7 / "summary_r7.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
