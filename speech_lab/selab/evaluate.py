"""Score every method output against the reference (same refs, same metric code for all methods).

python -m selab.evaluate --tag r1 [--asr]       -> results/<tag>/metrics.csv  (incremental)
ASR intelligibility proxy: faster-whisper base.en (int8, greedy), WER vs LibriSpeech transcript via jiwer
with Whisper's English text normaliser.
"""
import argparse, json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd
from .common import MIX, OUT, RES, load
from .metrics import all_metrics


def _score(args):
    tag, out_tag, method, m = args
    d = MIX / tag / m["id"]
    ref, mix = load(d / "ref.wav"), load(d / "mix.wav")
    est = load(OUT / out_tag / method / f"{m['id']}.wav")
    r = all_metrics(ref, est, mix)
    r.update(method=method, id=m["id"], cond=m["cond"], snr=m["snr"])
    return r


_asr = None


def asr_model():
    global _asr
    if _asr is None:
        from faster_whisper import WhisperModel
        from .common import MODELS
        _asr = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=2,
                            download_root=str(MODELS / "whisper"))
    return _asr


def transcribe(x):
    segs, _ = asr_model().transcribe(x, language="en", beam_size=1, condition_on_previous_text=False, without_timestamps=True,
                                     vad_filter=False, temperature=0.0)
    return " ".join(s.text for s in segs)


def wer(ref_text, hyp):
    import jiwer, re
    f = lambda s: re.sub(r"[^a-z' ]", " ", s.lower()).split()
    r, h = " ".join(f(ref_text)), " ".join(f(hyp))
    return float(jiwer.wer(r, h)) if r else float("nan"), h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="r1")
    ap.add_argument("--out_tag", default=None)
    ap.add_argument("--asr", action="store_true")
    ap.add_argument("--methods", default=None)
    ap.add_argument("--asr_max_per_cell", type=int, default=None, help="ASR only on the first k utts of each cell (CPU budget)")
    a = ap.parse_args()
    out_tag = a.out_tag or a.tag
    meta = {m["id"]: m for m in json.load(open(MIX / a.tag / "meta.json"))}
    rd = RES / out_tag; rd.mkdir(parents=True, exist_ok=True)
    csv = rd / "metrics.csv"
    old = pd.read_csv(csv) if csv.exists() else pd.DataFrame(columns=["method", "id"])
    done = set(zip(old.method, old.id))
    methods = a.methods.split(",") if a.methods else sorted(p.name for p in (OUT / out_tag).iterdir() if p.is_dir())
    jobs = []
    for meth in methods:
        for f in sorted((OUT / out_tag / meth).glob("*.wav")):
            if (meth, f.stem) not in done and f.stem in meta:
                jobs.append((a.tag, out_tag, meth, meta[f.stem]))
    print(f"scoring {len(jobs)} files")
    with ProcessPoolExecutor(2) as ex:
        rows = list(ex.map(_score, jobs, chunksize=8))
    df = pd.concat([old, pd.DataFrame(rows)], ignore_index=True) if rows else old
    df.to_csv(csv, index=False)
    if a.asr:
        wcsv = rd / "wer.csv"
        wold = pd.read_csv(wcsv) if wcsv.exists() else pd.DataFrame(columns=["method", "id"])
        wdone = set(zip(wold.method, wold.id))
        wrows = []
        # clean-reference ceiling
        targets = [("clean_ref", MIX / a.tag / i / "ref.wav", i) for i in meta]
        for meth in methods:
            targets += [(meth, f, f.stem) for f in sorted((OUT / out_tag / meth).glob("*.wav")) if f.stem in meta]
        targets = [t for t in targets if (t[0], t[2]) not in wdone]
        if a.asr_max_per_cell:
            targets = [t for t in targets if int(t[2].rsplit("_", 1)[1]) < a.asr_max_per_cell]
        print(f"ASR on {len(targets)} files")
        for k, (meth, f, i) in enumerate(targets):
            w, h = wer(meta[i]["text"], transcribe(load(f)))
            wrows.append(dict(method=meth, id=i, cond=meta[i]["cond"], snr=meta[i]["snr"], wer=w, hyp=h))
            if k % 20 == 19:
                pd.concat([wold, pd.DataFrame(wrows)]).to_csv(wcsv, index=False)
        pd.concat([wold, pd.DataFrame(wrows)], ignore_index=True).to_csv(wcsv, index=False)


if __name__ == "__main__":
    main()
