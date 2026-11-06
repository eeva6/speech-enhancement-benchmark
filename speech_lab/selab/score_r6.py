"""Score round-6 outputs (same metrics and ASR settings as round 5; see selab/score_r5.py).

python -m selab.score_r6 --tag r5 --methods a,b [--asr] [--items sub48|all|s012|s345] [--shard k --nshard n]
Objective -> results/r6/metrics_<tag>.csv ; ASR -> results/r6/wer_<tag>[.part<k>].csv (resumable, de-duplicated
across all part files).  Baseline methods already transcribed in round 5 are read from results/r5 by the
analysis and are not re-transcribed (same model, same settings, deterministic greedy decoding).
"""
import argparse, json, os
from concurrent.futures import ProcessPoolExecutor
import pandas as pd
from .common import MIX, OUT, RES, load
from .score_r5 import _obj, asr_score
from .run_r6 import select


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="r5"); ap.add_argument("--asr", action="store_true")
    ap.add_argument("--methods", required=True); ap.add_argument("--items", default="sub48")
    ap.add_argument("--shard", type=int, default=0); ap.add_argument("--nshard", type=int, default=1)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    allmeta = json.load(open(MIX / a.tag / "meta.json"))
    meta = {m["id"]: m for m in select(allmeta, a.items)}
    rd = RES / "r6"; rd.mkdir(parents=True, exist_ok=True)
    methods = a.methods.split(",")
    if not a.asr:
        csv = rd / f"metrics_{a.tag}.csv"
        old = pd.read_csv(csv) if csv.exists() else pd.DataFrame(columns=["method", "id"])
        done = set(zip(old.method, old.id))
        jobs = [(a.tag, me, meta[i]) for me in methods for i in meta
                if (OUT / a.tag / me / f"{i}.wav").exists() and (me, i) not in done]
        print("objective:", len(jobs), flush=True)
        if a.workers > 1:
            with ProcessPoolExecutor(a.workers) as ex:
                rows = list(ex.map(_obj, jobs, chunksize=8))
        else:
            rows = [_obj(j) for j in jobs]
        cur = pd.read_csv(csv) if csv.exists() else pd.DataFrame(columns=["method", "id"])
        pd.concat([cur, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(["method", "id"]).to_csv(csv, index=False)
        return
    from .evaluate import transcribe
    csv = rd / (f"wer_{a.tag}.csv" if a.nshard == 1 else f"wer_{a.tag}.part{a.shard}.csv")
    old = pd.read_csv(csv) if csv.exists() else pd.DataFrame(columns=["method", "id"])
    allw = [pd.read_csv(p) for p in list(rd.glob(f"wer_{a.tag}.csv")) + list(rd.glob(f"wer_{a.tag}.part*.csv"))]   # not r5 -> r5sim
    # round-5 transcriptions of the same baseline files count as done (same model, settings, deterministic)
    allw += [pd.read_csv(p)[lambda d: d.method.isin(["noisy", "ds_est", "ref_image"])] for p in list((RES / "r5").glob(f"wer_{a.tag}.csv")) + list((RES / "r5").glob(f"wer_{a.tag}.part*.csv"))]
    allw = pd.concat(allw) if allw else old
    done = set(zip(allw.method, allw.id))
    targets = []
    for me in methods:
        src = (lambda i: MIX / a.tag / i / "ref.wav") if me == "ref_image" else (lambda i, me=me: OUT / a.tag / me / f"{i}.wav")
        targets += [(me, src(i), i) for i in meta if src(i).exists() and (me, i) not in done]
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
