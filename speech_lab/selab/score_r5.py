"""Score round-5 outputs.

Objective (needs a reference): SI-SDR and ESTOI vs ref.wav.
  r5    : ref = ESTIMATED reverberant target image at mic 0 (dry feed x system-identified RIR). Its own error
          floor is the LS residual (~ -10 dB), so SI-SDR above ~10 dB is not resolvable; treat as indicative.
  r5sim : ref = exact simulated reverberant target image.
ASR (no reference audio needed; primary intelligibility proxy): faster-whisper base.en int8 greedy (same
settings as rounds 1-4), WER and word-correct (= hits / reference words) vs the LibriSpeech transcript; insertions
are reported separately because transcribing the competing talker shows up as insertions.
python -m selab.score_r5 --tag r5 [--asr] [--methods a,b]
"""
import argparse, json, re
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
from .common import MIX, OUT, RES, load


def _obj(args):
    tag, meth, m = args
    from .metrics import si_sdr, stoi
    d = MIX / tag / m["id"]
    ref = load(d / "ref.wav"); est = load(OUT / tag / meth / f"{m['id']}.wav")
    n = min(len(ref), len(est)); ref, est = ref[:n], est[:n]
    return dict(method=meth, id=m["id"], cond=m["cond"], si_sdr=si_sdr(ref, est), estoi=stoi(ref, est, extended=True))


def asr_score(ref_text, hyp):
    import jiwer
    f = lambda s: re.sub(r"[^a-z' ]", " ", s.lower()).split()
    r, h = " ".join(f(ref_text)), " ".join(f(hyp))
    o = jiwer.process_words(r, h if h else "<empty>") if h else None
    N = len(r.split())
    if o is None:
        return dict(wer=1.0, word_correct=0.0, ins_rate=0.0, hyp="")
    return dict(wer=float(o.wer), word_correct=o.hits / N, ins_rate=o.insertions / N, sub_rate=o.substitutions / N,
                del_rate=o.deletions / N, hyp=h)


def sub48(meta):
    """first 2 items (in build order) of every recording -> 48 items."""
    out, cnt = [], {}
    for i, m in meta.items():
        k = (m["cond"], m.get("session"))
        if cnt.get(k, 0) < 2:
            out.append(i); cnt[k] = cnt.get(k, 0) + 1
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="r5"); ap.add_argument("--asr", action="store_true")
    ap.add_argument("--methods", default=None)
    ap.add_argument("--shard", type=int, default=0); ap.add_argument("--nshard", type=int, default=1)
    ap.add_argument("--items", default=None, help="'sub48' = 2 items per recording (CPU budget for secondary methods)")
    a = ap.parse_args()
    meta = {m["id"]: m for m in json.load(open(MIX / a.tag / "meta.json"))}
    rd = RES / "r5"; rd.mkdir(parents=True, exist_ok=True)
    methods = a.methods.split(",") if a.methods else sorted(p.name for p in (OUT / a.tag).iterdir() if p.is_dir())
    if not a.asr:
        csv = rd / f"metrics_{a.tag}.csv"
        old = pd.read_csv(csv) if csv.exists() else pd.DataFrame(columns=["method", "id"])
        done = set(zip(old.method, old.id))
        jobs = [(a.tag, me, meta[f.stem]) for me in methods for f in sorted((OUT / a.tag / me).glob("*.wav"))
                if f.stem in meta and (me, f.stem) not in done]
        print("objective:", len(jobs))
        with ProcessPoolExecutor(2) as ex:
            rows = list(ex.map(_obj, jobs, chunksize=8))
        pd.concat([old, pd.DataFrame(rows)], ignore_index=True).to_csv(csv, index=False)
        return
    from .evaluate import transcribe
    csv = rd / (f"wer_{a.tag}.csv" if a.nshard == 1 else f"wer_{a.tag}.part{a.shard}.csv")
    old = pd.read_csv(csv) if csv.exists() else pd.DataFrame(columns=["method", "id"])
    allw = [pd.read_csv(p) for p in list(rd.glob(f"wer_{a.tag}.csv")) + list(rd.glob(f"wer_{a.tag}.part*.csv"))]   # exact: r5 must not match r5sim
    allw = pd.concat(allw) if allw else old
    done = set(zip(allw.method, allw.id))
    targets = [("ref_image", MIX / a.tag / i / "ref.wav", i) for i in meta]
    if a.tag == "r5":   # dry LibriSpeech feed of the target = clean ceiling
        targets += []
    for me in methods:
        targets += [(me, f, f.stem) for f in sorted((OUT / a.tag / me).glob("*.wav")) if f.stem in meta]
    targets = [t for t in targets if (t[0], t[2]) not in done]
    if a.items == "sub48":
        keep = set(sub48(meta))
        targets = [t for t in targets if t[2] in keep]
    if a.methods:
        targets = [t for t in targets if t[0] in methods]   # ref_image only when asked for
    targets = targets[a.shard::a.nshard]
    print("ASR:", len(targets), flush=True)
    rows = []
    for k, (me, f, i) in enumerate(targets):
        r = asr_score(meta[i]["text"], transcribe(load(f)))
        r.update(method=me, id=i, cond=meta[i]["cond"]); rows.append(r)
        if k % 10 == 9:
            pd.concat([old, pd.DataFrame(rows)], ignore_index=True).to_csv(csv, index=False)
    pd.concat([old, pd.DataFrame(rows)], ignore_index=True).to_csv(csv, index=False)


if __name__ == "__main__":
    main()
