"""Round 7 phase 2: processing, scoring and the val-tune -> freeze -> test pipeline (resumable).

Method names: <steer>_<filt>[__<variant>] with steer in hs/trk/hyb/ref, filt in ds_td/sd4/sd8; plus
front1..front4 (single frame mic), unproc_front (frozen best frame mic), unproc_ear (mean of ch5/ch6), r5ds.
Variants (tuning only): r<ref>w<wng>  (reference mic index 0-3, WNG floor dB), X<deg>t<thr> (hybrid window/threshold).
Outputs: outputs/r7/<split>/<method>/<id>.wav = SCORED SPAN only ([utt_offset_samples:], raw level).
Per-item info: results/r7/proc/<split>_<method>.<pid>.csv ; ASR: results/r7/wer_<split>.part<k>.csv ;
objective: results/r7/metrics_<split>.part<k>.csv ; tuning decisions: results/r7/frozen_r7.json.

python -m selab.run_r7 pipeline            # everything, 2 worker processes, resumable
python -m selab.run_r7 work --split val --items sub300 --methods a,b --shard 0 --nshard 2 [--asr --obj]
"""
import argparse, glob, json, os, re, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd, soundfile as sf
from .common import MIX, OUT, RES, FS

R7 = RES / "r7"; PROC = R7 / "proc"; FROZEN = R7 / "frozen_r7.json"
FINAL = ["unproc_front", "unproc_ear", "r5ds", "hs_ds_td", "hs_sd8", "hs_sd4", "trk_ds_td", "trk_sd8", "trk_sd4",
         "hyb_ds_td", "hyb_sd8", "hyb_sd4", "ref_sd8", "ref_ds_td"]
DEFAULT = dict(ref=1, wng_db=0.0, X=30.0, thr=3.0, front=1)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def items(split, which="all"):
    it = json.load(open(MIX / "r7" / split / "meta.json"))["items"]
    if which == "all":
        return it
    if which == "words":
        return [m for m in it if m["n_words"] > 0]
    if which.startswith("sub"):
        n = int(which[3:]); w = [m for m in it if m["n_words"] > 0]
        # stratified by session x target, deterministic (seed 7), proportional allocation
        rng = np.random.default_rng(7); df = pd.DataFrame(w); keep = []
        for _, g in df.groupby(["session", "target"]):
            k = int(round(n * len(g) / len(df))); keep += list(rng.permutation(g.id.values)[:k])
        keep = set(keep)
        return [m for m in w if m["id"] in keep]
    raise ValueError(which)


def params(name, frozen):
    base, _, var = name.partition("__")
    p = dict(DEFAULT); p.update({k: v for k, v in frozen.items() if k in DEFAULT})
    if var:
        m = re.fullmatch(r"r(\d)w(-?\d+(?:\.\d+)?)", var)
        if m:
            p["ref"], p["wng_db"] = int(m.group(1)), float(m.group(2))
        m = re.fullmatch(r"X(\d+)t(\d+(?:\.\d+)?)", var)
        if m:
            p["X"], p["thr"] = float(m.group(1)), float(m.group(2))
    return base, p


def load_frozen():
    return json.load(open(FROZEN)) if FROZEN.exists() else {}


# ------------------------------------------------------------------------------------------------ processing
def get_tracks(split, m, x4):
    from . import bf_r7 as B
    cd = OUT / "r7" / split / "_trk"; cd.mkdir(parents=True, exist_ok=True); cp = cd / f"{m['id']}.npz"
    if cp.exists():
        z = np.load(cp); return {k: z[k] for k in z.files}
    ts = B.track_states(x4); np.savez(cp, **ts); return ts


def process_one(split, name, m, frozen):
    from . import bf_r7 as B
    d = MIX / "r7" / split / m["id"]
    x, _ = sf.read(str(d / "mix_mc.wav"), dtype="float32"); x = x.T.astype(np.float64)
    off = int(m["utt_offset_samples"]); n = x.shape[1]
    base, p = params(name, frozen)
    doa = np.load(d / "doa_ref.npz"); tmask = doa["t"] * FS >= off
    az_ref = doa["az"][tmask]
    info = dict(method=name, id=m["id"], split=split, head_angle=float(np.nanmedian(np.abs(az_ref))) if np.isfinite(az_ref).any() else np.nan)
    tt = None; steer_az = None; extra = {}
    if base.startswith("front"):
        y = x[int(base[5:]) - 1]
    elif base == "unproc_front":
        y = x[int(p["front"]) - 1]
    elif base == "unproc_ear":
        y = 0.5 * (x[4] + x[5])
    elif base == "r5ds":
        y, az = B.r5ds(x[:4], p["ref"], (off, n)); extra["steer_az"] = az
        steer_az = np.full(tmask.sum(), az)
    else:
        steer, filt = base.split("_", 1)
        if steer == "hs":
            st = B.const_steer(n)
        elif steer in ("trk", "hyb"):
            ts = get_tracks(split, m, x[:4])
            if steer == "trk":
                a = ts["az"]
            else:
                a, conf = B.hybrid(ts, p["X"], p["thr"])
                extra["hyb_conf_frac"] = float(conf[ts["avail"] >= off].mean()) if (ts["avail"] >= off).any() else np.nan
            st = dict(az=a, el=np.zeros_like(a), avail=ts["avail"])
            extra["trk_ms_per_frame"] = float(1000 * np.mean(ts["sec"]))
        elif steer == "ref":
            st = B.ref_steer(doa)
        else:
            raise ValueError(name)
        if filt == "ds_td" and steer == "hs":
            pass
        y, tt, li = B.run(filt, x[:4], st, p["ref"], p["wng_db"])
        extra.update(li)
        # steering az at each scored pose-frame time (latest available)
        tf = np.round(doa["t"][tmask] * FS)
        j = np.searchsorted(st["avail"], tf, side="right") - 1
        steer_az = np.where(j >= 0, st["az"][np.clip(j, 0, None)], 0.0)
    if steer_az is not None and np.isfinite(az_ref).any():
        e = np.abs(B.angd(steer_az, az_ref)); info["steer_err_med"] = float(np.nanmedian(e))
        info["steer_within15"] = float(np.nanmean(e <= 15))
    if tt is not None:
        info.update(per_hop_ms=float(1000 * tt.mean()), p99_hop_ms=float(1000 * np.quantile(tt, 0.99)))
    info.update(extra)
    return np.asarray(y[off:], np.float32), info


def do_process(split, names, its, shard, nshard, frozen):
    from .common import save
    PROC.mkdir(parents=True, exist_ok=True)
    its = its[shard::nshard]
    for name in names:
        od = OUT / "r7" / split / name
        todo = [m for m in its if not (od / f"{m['id']}.wav").exists()]
        if not todo:
            continue
        log("process", split, name, len(todo))
        csv = PROC / f"{split}_{name}.{os.getpid()}.csv"; rows = []
        for k, m in enumerate(todo):
            try:
                y, info = process_one(split, name, m, frozen)
                save(od / f"{m['id']}.wav", np.nan_to_num(y)); rows.append(info)
            except Exception as e:
                log("FAIL", name, m["id"], repr(e), traceback.format_exc()[-600:])
            if len(rows) >= 25 or k == len(todo) - 1:
                if rows:
                    pd.DataFrame(rows).to_csv(csv, mode="a", header=not csv.exists(), index=False); rows = []


# ------------------------------------------------------------------------------------------------ scoring
_ASR = {}
ONES = None


def norm_text(s):
    from num2words import num2words
    s = re.sub(r"\[[A-Za-z]\]", " ", s)
    s = s.replace("*", " ").replace("-", " ").replace("–", " ").replace("—", " ")
    s = s.replace("%", " percent ").replace("&", " and ")

    def num(mo):
        t = mo.group(0); core = re.sub(r"[^\d.]", "", t)
        try:
            if re.fullmatch(r"\d+(st|nd|rd|th)", t):
                return " " + num2words(int(core), to="ordinal") + " "
            if re.fullmatch(r"\d+s", t):
                w = num2words(int(core), to="year" if len(core) == 4 else "cardinal")
                return " " + (w[:-1] + "ies" if w.endswith("y") else w + "s") + " "
            if "." in core:
                return " " + num2words(float(core)) + " "
            v = int(core.replace(",", ""))
            return " " + (num2words(v, to="year") if 1100 <= v <= 2099 and len(core) == 4 else num2words(v)) + " "
        except Exception:
            return " "
    s = re.sub(r"\d+(?:[.,]\d+)?(?:st|nd|rd|th|s)?", num, s.lower())
    s = s.replace("-", " ")
    return " ".join(re.sub(r"[^a-z' ]", " ", s).replace(" '", " ").replace("' ", " ").split())


def asr_model():
    if "m" not in _ASR:
        from faster_whisper import WhisperModel
        from .common import MODELS
        _ASR["m"] = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=1, num_workers=1,
                                 download_root=str(MODELS / "whisper"))
    return _ASR["m"]


def transcribe(y):
    r = np.sqrt(np.mean(y.astype(np.float64) ** 2)) + 1e-12
    y = (y * (10 ** (-26 / 20) / r)).astype(np.float32)                   # -26 dBFS RMS
    y = np.clip(y, -1, 1)
    segs, _ = asr_model().transcribe(y, language="en", beam_size=1, condition_on_previous_text=False,
                                     without_timestamps=True, vad_filter=False, temperature=0.0)
    return " ".join(s.text for s in segs)


def asr_score(ref_text, hyp):
    import jiwer
    r, h = norm_text(ref_text), norm_text(hyp)
    N = len(r.split())
    if not h:
        return dict(wer=1.0, word_correct=0.0, ins_rate=0.0, sub_rate=0.0, del_rate=1.0, hyp="", n_ref=N)
    o = jiwer.process_words(r, h)
    return dict(wer=float(o.wer), word_correct=o.hits / N, ins_rate=o.insertions / N, sub_rate=o.substitutions / N,
                del_rate=o.deletions / N, hyp=h, n_ref=N)


def done_set(split, kind):
    ps = sorted(glob.glob(str(R7 / f"{kind}_{split}.csv")) + glob.glob(str(R7 / f"{kind}_{split}.part*.csv")))
    s = set()
    for p in ps:
        try:
            d = pd.read_csv(p, usecols=["method", "id"]); s |= set(zip(d.method, d.id))
        except Exception:
            pass
    return s


def do_asr(split, names, its, shard, nshard):
    its = [m for m in its[shard::nshard] if m["n_words"] > 0]
    csv = R7 / f"wer_{split}.part{shard}.csv"; done = done_set(split, "wer"); rows = []
    todo = [(nm, m) for nm in names for m in its if (nm, m["id"]) not in done and (OUT / "r7" / split / nm / f"{m['id']}.wav").exists()]
    if todo:
        log("asr", split, len(todo))
    for k, (nm, m) in enumerate(todo):
        fp = OUT / "r7" / split / nm / f"{m['id']}.wav"
        try:
            y, _ = sf.read(str(fp), dtype="float32")
            r = asr_score(m["text"], transcribe(y)); r.update(method=nm, id=m["id"]); rows.append(r)
        except Exception as e:
            log("ASR FAIL (output removed, will be re-processed)", nm, m["id"], repr(e)); fp.unlink(missing_ok=True)
        if len(rows) >= 20 or k == len(todo) - 1:
            pd.DataFrame(rows).to_csv(csv, mode="a", header=not csv.exists(), index=False); rows = []


def do_obj(split, names, its, shard, nshard):
    from pystoi import stoi
    its = its[shard::nshard]
    csv = R7 / f"metrics_{split}.part{shard}.csv"; done = done_set(split, "metrics"); rows = []
    todo = [(nm, m) for nm in names for m in its if (nm, m["id"]) not in done and (OUT / "r7" / split / nm / f"{m['id']}.wav").exists()]
    if todo:
        log("obj", split, len(todo))
    refc = {}
    for k, (nm, m) in enumerate(todo):
        if m["id"] not in refc:
            refc = {m["id"]: sf.read(str(MIX / "r7" / split / m["id"] / "ref.wav"), dtype="float32")[0][int(m["utt_offset_samples"]):]}
        ref = refc[m["id"]].astype(np.float64)
        try:
            est = sf.read(str(OUT / "r7" / split / nm / f"{m['id']}.wav"), dtype="float32")[0].astype(np.float64)
        except Exception as e:
            log("OBJ read FAIL", nm, m["id"], repr(e)); continue
        n = min(len(ref), len(est)); ref, est = ref[:n], est[:n]
        best, bl = -1e9, 0
        for lag in range(-8, 9):            # +-0.5 ms lag search (outputs are aligned to different reference mics)
            a = est[max(lag, 0): n + min(lag, 0)]; b = ref[max(-lag, 0): n - max(lag, 0)]
            b0 = b - b.mean(); a0 = a - a.mean(); al = a0 @ b0 / (b0 @ b0 + 1e-12); t = al * b0
            v = 10 * np.log10((t @ t) / ((a0 - t) @ (a0 - t) + 1e-12) + 1e-12)
            if v > best:
                best, bl = v, lag
        a = est[max(bl, 0): n + min(bl, 0)]; b = ref[max(-bl, 0): n - max(bl, 0)]
        rows.append(dict(method=nm, id=m["id"], si_sdr=float(best), lag=bl, estoi=float(stoi(b, a, FS, extended=True)),
                         align_suspect=bool(m["align_suspect"])))
        if len(rows) >= 50 or k == len(todo) - 1:
            pd.DataFrame(rows).to_csv(csv, mode="a", header=not csv.exists(), index=False); rows = []


def load_wer(split):
    ps = sorted(glob.glob(str(R7 / f"wer_{split}.csv")) + glob.glob(str(R7 / f"wer_{split}.part*.csv")))
    return pd.concat([pd.read_csv(p) for p in ps]).drop_duplicates(["method", "id"], keep="last") if ps else None


# ------------------------------------------------------------------------------------------------ pipeline
def work(split, names, which, shard, nshard, asr=True, obj=True):
    os.environ["OMP_NUM_THREADS"] = "1"
    frozen = load_frozen(); its = items(split, which)
    do_process(split, names, its, shard, nshard, frozen)
    if asr:
        do_asr(split, names, its, shard, nshard)
    if obj:
        do_obj(split, names, its, shard, nshard)


def _w(args):
    try:
        work(*args)
    except Exception:
        log("WORKER FAIL", traceback.format_exc())
        raise


def stage(split, names, which, asr=True, obj=True):
    import multiprocessing as mp
    log("STAGE", split, which, names)
    with mp.get_context("spawn").Pool(2) as pool:
        pool.map(_w, [(split, names, which, k, 2, asr, obj) for k in range(2)])


def best_of(split, names, ids):
    w = load_wer(split); w = w[w.method.isin(names) & w.id.isin(ids)]
    t = w.groupby("method").word_correct.agg(["mean", "size"])
    return t, t["mean"].idxmax()


def pipeline():
    frozen = load_frozen()
    if frozen.get("frozen"):
        log("frozen already:", frozen)
    else:
        sub = "sub300"; ids = {m["id"] for m in items("val", sub)}
        rec = dict(tuning_set="val sub300 (stratified session x target, seed 7, items with words)", n_tuning=len(ids))
        A = ["front1", "front2", "front3", "front4"] + [f"hs_sd8__r{r}w0" for r in range(4)]
        stage("val", A, sub, obj=False)
        t, b = best_of("val", A[:4], ids); rec["front_choice"] = t["mean"].round(4).to_dict(); front = int(b[-1])
        t, b = best_of("val", A[4:], ids); rec["ref_choice"] = t["mean"].round(4).to_dict(); ref = int(b.split("__r")[1][0])
        Bn = [f"hs_sd8__r{ref}w{w}" for w in (-6, -3, 0, 3, 6)]
        stage("val", Bn, sub, obj=False)
        t, b = best_of("val", Bn, ids); rec["wng_choice"] = t["mean"].round(4).to_dict(); wng = float(b.split("w")[-1])
        json.dump(dict(rec, front=front, ref=ref, wng_db=wng, frozen=False), open(FROZEN, "w"), indent=1)
        Cn = [f"hyb_sd8__X{X}t{thr}" for X in (20, 30, 45) for thr in (1, 3, 8)]
        stage("val", Cn, sub, obj=False)
        t, b = best_of("val", Cn, ids); rec["hyb_choice"] = t["mean"].round(4).to_dict()
        X, thr = re.fullmatch(r"hyb_sd8__X(\d+)t(\d+)", b).groups()
        frozen = dict(rec, front=front, ref=ref, wng_db=wng, X=float(X), thr=float(thr), frozen=True,
                      frozen_at_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                      rule="argmax mean word-correct on the val tuning set; sequential: front mic and ref mic (WNG 0 dB), then WNG floor, then hybrid X/thr")
        json.dump(frozen, open(FROZEN, "w"), indent=1)
        log("FROZEN", frozen)
    stage("test", FINAL, "all")                       # test: run once with frozen parameters
    stage("val", FINAL, "sub300")                     # val reference numbers for the frozen set
    (R7 / "PIPELINE_DONE").write_text(time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
    log("PIPELINE DONE")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("what")
    ap.add_argument("--split", default="val"); ap.add_argument("--items", default="sub300")
    ap.add_argument("--methods", default=""); ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshard", type=int, default=1); ap.add_argument("--asr", action="store_true"); ap.add_argument("--obj", action="store_true")
    a = ap.parse_args()
    if a.what == "pipeline":
        pipeline()
    elif a.what == "work":
        work(a.split, a.methods.split(","), a.items, a.shard, a.nshard, a.asr, a.obj)


if __name__ == "__main__":
    main()
