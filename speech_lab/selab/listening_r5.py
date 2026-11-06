"""Round 5 listening pack: BEFORE/AFTER mp3 pairs from the REAL LibriCSS recordings.

Selection is rule-based from the measured Whisper results (not hand-picked by ear), one clip per question:
  1-3  biggest measured word-correct gain of the best deployable-ish cascade (online MVDR est. DOA -> TSE) at
       OV10 / OV20 / OV40
  4    the fully causal 32-ms online MVDR alone (est. DOA), largest gain on an overlapped item
  5    DeepFilterNet3 on an overlapped item where it measured no gain (a denoiser does not remove a talker)
  6    a failure case: the cascade's largest word-correct LOSS
  7    a no-overlap (0S) item, TSE: check it does not damage clean single-talker speech
Each AFTER file is loudness-matched (RMS) to its BEFORE file. Writes listening/r5/*.mp3, README.txt,
and the zip ../round5_listening.zip (next to the lab folder).
python -m selab.listening_r5
"""
import json, shutil, subprocess, zipfile
import numpy as np, pandas as pd, soundfile as sf
from .common import ROOT, MIX, OUT, RES, FS

DST = ROOT / "listening" / "r5"
ZIP = ROOT.parent / "round5_listening.zip"


def mp3(src_wav, dst, ref_rms=None):
    x, _ = sf.read(str(src_wav), dtype="float32")
    if x.ndim > 1:
        x = x[:, 0]
    r = np.sqrt(np.mean(x ** 2)) + 1e-9
    x = x * ((ref_rms or 0.05) / r)
    x = np.clip(x, -0.99, 0.99)
    tmp = dst.with_suffix(".wav"); sf.write(tmp, x, FS, subtype="PCM_16")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-codec:a", "libmp3lame", "-b:a", "96k", str(dst)], check=True)
    tmp.unlink()


def main():
    w = pd.concat([pd.read_csv(p) for p in sorted((RES / "r5").glob("wer_r5.csv")) + sorted((RES / "r5").glob("wer_r5.part*.csv"))],
                  ignore_index=True).drop_duplicates(["method", "id"])
    meta = {m["id"]: m for m in json.load(open(MIX / "r5" / "meta.json"))}
    wc = w.pivot_table(index="id", columns="method", values="word_correct")
    d = wc.sub(wc["noisy"], axis=0)
    picks = []
    casc = "mvdr_online_est_tse" if "mvdr_online_est_tse" in d else "tse"
    used = set()

    def best(col, conds, sign=1, cond_extra=None):
        s = d[col][[i for i in d.index if meta[i]["cond"] in conds and i not in used and 3 <= meta[i]["dur"] <= 10]]
        s = s.dropna()
        if cond_extra is not None:
            s = s[cond_extra(s)]
        if s.empty:
            return None
        i = (s * sign).idxmax(); used.add(i); return i

    for c in ("OV10", "OV20", "OV40"):
        i = best(casc, [c]); picks.append((i, casc, f"{c} overlap: online MVDR (estimated direction) then target-speaker extraction"))
    i = best("mvdr_online_est", ["OV10", "OV20", "OV40"]); picks.append((i, "mvdr_online_est", "overlap: online MVDR alone, fully causal, 32 ms, estimated direction"))
    i = best("deepfilternet3", ["OV20", "OV40"], sign=-1, cond_extra=lambda s: s <= 0.0)
    picks.append((i, "deepfilternet3", "overlap: DeepFilterNet3 alone (a noise suppressor) - expect little change to the second voice"))
    i = best(casc, ["OV10", "OV20", "OV40"], sign=-1); picks.append((i, casc, "FAILURE case: largest measured loss for the cascade"))
    i = best("tse", ["0S"], sign=-1, cond_extra=lambda s: s > -2); picks.append((i, "tse", "no overlap (control): TSE on clean single-talker speech"))
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)
    lines = ["ROUND 5 LISTENING PACK - real meeting-room recordings (LibriCSS, 7-mic array, mic 0 shown)",
             "Each pair: a = BEFORE (unprocessed centre mic), b = AFTER. Loudness matched. Use headphones.",
             "These are recordings; a device that processes audio in the room is a different situation (see REPORT_R5).",
             "Clips were chosen by rule from the measured ASR scores (best / worst cases), so they are NOT typical:",
             "typical effects are in REPORT_R5.pdf.", ""]
    for k, (i, meth, why) in enumerate(picks, 1):
        if i is None:
            continue
        m = meta[i]
        b = MIX / "r5" / i / "mix.wav"; a = OUT / "r5" / meth / f"{i}.wav"
        x, _ = sf.read(str(b), dtype="float32"); rr = float(np.sqrt(np.mean(x ** 2)))
        g = 0.05 / (rr + 1e-9)
        nb = f"{k:02d}a_{m['cond']}_BEFORE.mp3"; na = f"{k:02d}b_{m['cond']}_AFTER_{meth}.mp3"
        mp3(b, DST / nb, 0.05); mp3(a, DST / na, 0.05)
        row = w[w.id == i].set_index("method")
        lines += [f"{k:02d}  {why}", f"    item {i}  ({m['dur']:.1f} s, {100*m['ovl']:.0f}% of the sentence overlapped)",
                  f"    target sentence: \"{m['text'].lower()}\"",
                  f"    Whisper heard BEFORE: \"{row.loc['noisy','hyp']}\"  (word-correct {row.loc['noisy','word_correct']:.2f})",
                  f"    Whisper heard AFTER:  \"{row.loc[meth,'hyp']}\"  (word-correct {row.loc[meth,'word_correct']:.2f})"]
        if k <= 4 and row.loc[meth, 'word_correct'] <= row.loc['noisy', 'word_correct']:
            lines += ["    NOTE: no scored item in this cell improved with this method; this is the least-bad one."]
        lines += [""]
    lines += ["Source: LibriCSS (Chen et al., ICASSP 2020; recordings of LibriSpeech test-clean, CC BY 4.0).",
              "Nothing here is a human listening result; the word-correct figures are Whisper base.en (an ASR proxy)."]
    (DST / "README.txt").write_text("\n".join(lines))
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DST.iterdir()):
            z.write(p, f"round5_listening/{p.name}")
    print("\n".join(lines)); print(ZIP)


if __name__ == "__main__":
    main()
