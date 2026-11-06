"""Round 6 listening pack: BEFORE / ROUND-5 DS / ROUND-6 tracked / ROUND-6 reference-direction sets from the REAL LibriCSS recordings.

Rule-based selection from the measured Whisper word-correct (not chosen by ear), panel items only:
  1-3  largest gain of the round-6 method over round-5 delay-and-sum at OV10 / OV20 / OV40
  4    a TYPICAL overlapped item: the one whose round-6 gain over unprocessed is closest to the panel median
  5    FAILURE case: the round-6 method's largest loss against round-5 delay-and-sum
  6    no-overlap (0S) control
a = unprocessed centre mic, b = round-5 delay-and-sum (blind direction, 32 ms STFT), c = round-6 method.
All files RMS-matched. Writes listening/r6/, README.txt and ../round6_listening.zip.
python -m selab.listening_r6 --method sd8_rt
"""
import argparse, json, shutil, zipfile
import numpy as np, pandas as pd, soundfile as sf
from .common import ROOT, MIX, OUT, RES
from .listening_r5 import mp3
from .analyze_r6 import load_wer, label
from .run_r6 import select

DST = ROOT / "listening" / "r6"
ZIP = ROOT.parent / "round6_listening.zip"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--method", required=True)
    ap.add_argument("--ref", default=None, help="reference-direction (oracle steering) version; default <method> with _rt -> _ref")
    a = ap.parse_args()
    best = a.method; refm = a.ref or best.replace("_rt", "_ref")
    w = load_wer("r5")
    meta = {m["id"]: m for m in json.load(open(MIX / "r5" / "meta.json"))}
    panel = set(m["id"] for m in select(list(meta.values()), "sub48"))
    wc = w[w.id.isin(panel)].pivot_table(index="id", columns="method", values="word_correct")
    wc = wc.dropna(subset=["noisy", "ds_est", best] + ([refm] if refm in wc else []))
    d5 = wc[best] - wc["ds_est"]; d0 = wc[best] - wc["noisy"]
    used, picks = set(), []

    def pick(s, conds, sign=1, why=""):
        s = s[[i for i in s.index if meta[i]["cond"] in conds and i not in used and 3 <= meta[i]["dur"] <= 12]]
        if s.empty:
            return
        i = (s * sign).idxmax(); used.add(i); picks.append((i, why))

    for c in ("OV10", "OV20", "OV40"):
        pick(d5, [c], 1, f"{c}: largest measured gain of the round-6 method over round-5 delay-and-sum")
    ov = d0[[i for i in d0.index if meta[i]["cond"] != "0S" and i not in used]]
    med = ov.median(); pick(-(ov - med).abs(), ["OV10", "OV20", "OV40"], 1,
                            f"TYPICAL overlapped item: round-6 gain over unprocessed closest to the panel median ({med:+.2f})")
    pick(d5, ["OV10", "OV20", "OV40"], -1, "FAILURE case: largest measured loss of the round-6 method vs round-5 delay-and-sum")
    pick(d0, ["0S"], -1, "no overlap (control): single talker, check the beamformer does no harm")
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)
    lines = ["ROUND 6 LISTENING PACK - real meeting-room recordings (LibriCSS, 7-mic array, 4.25 cm radius)",
             "Each set: a = BEFORE (unprocessed centre mic), b = ROUND-5 delay-and-sum (blind direction, 32 ms STFT),",
             f"c = ROUND-6 {label(best)} (causal, low latency, direction from the causal tracker),",
             f"d = ROUND-6 {label(refm)} (same filter, steered with the REFERENCE direction: oracle geometry, an upper bound",
             "    for what an intent cue such as head/gaze steering could give; not deployable as is).",
             "Loudness matched (RMS). Use headphones. Clips were chosen by rule from Whisper scores (best, typical, worst),",
             "so 1-3 and 5 are NOT typical; see REPORT_R6.pdf for averages.", ""]
    for k, (i, why) in enumerate(picks, 1):
        m = meta[i]; row = w[w.id == i].set_index("method")
        files = [("a", "BEFORE", MIX / "r5" / i / "mix.wav", "noisy"), ("b", "R5_DS", OUT / "r5" / "ds_est" / f"{i}.wav", "ds_est"),
                 ("c", f"R6_{best}", OUT / "r5" / best / f"{i}.wav", best),
                 ("d", f"R6_{refm}", OUT / "r5" / refm / f"{i}.wav", refm)]
        files = [f for f in files if f[2].exists() and f[3] in row.index]
        lines += [f"{k:02d}  {why}", f"    item {i}  ({m['dur']:.1f} s, {100*m['ovl']:.0f}% of the sentence overlapped)",
                  f"    target sentence: \"{m['text'].lower()}\""]
        for tag, nm, src, meth in files:
            mp3(src, DST / f"{k:02d}{tag}_{m['cond']}_{nm}.mp3", 0.05)
            lines += [f"    {tag} {nm:<14} Whisper: \"{row.loc[meth, 'hyp']}\"  (word-correct {row.loc[meth, 'word_correct']:.2f})"]
        lines += [""]
    lines += ["Source: LibriCSS (Chen et al., ICASSP 2020; recordings of LibriSpeech test-clean, CC BY 4.0).",
              "Nothing here is a human listening result; word-correct figures are Whisper base.en (an ASR proxy)."]
    (DST / "README.txt").write_text("\n".join(lines))
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DST.iterdir()):
            z.write(p, f"round6_listening/{p.name}")
    print("\n".join(lines)); print(ZIP)


if __name__ == "__main__":
    main()
