"""Score the venture A/B set (component-exact SNR/SIR, SI-SDR, STOI/ESTOI, Whisper word-correct).

python -m selab.venture_ab.score obj    # objective metrics for every processed item -> OUTW/obj.csv
python -m selab.venture_ab.score asr    # Whisper base.en (int8, greedy, 1 thread), -26 dBFS normalised -> OUTW/asr.csv (resumable)
python -m selab.venture_ab.score summary  # paired deltas, medians, ranges, cluster-bootstrap CIs -> OUTW/summary.json
"""
import json, os, sys
import numpy as np, pandas as pd
from .build import OUTW, MODES, meta_all
from ..common import FS

LEVEL = 10 ** (-26 / 20)   # -26 dBFS RMS


def db(a, b):
    return float(10 * np.log10((np.sum(a ** 2) + 1e-20) / (np.sum(b ** 2) + 1e-20)))


def busy_mask(m, n):
    k = np.zeros(n, bool)
    for a, b in m["busy"]:
        k[max(int(a * FS), 0):min(int(b * FS), n)] = True
    return k


def items():
    return sorted(p.name for p in (OUTW / "items").glob("*") if (p / "done.json").exists())


def load(iid, mode):
    z = np.load(OUTW / "items" / iid / f"{mode}.npz")
    return {k: z[k].astype(np.float64) for k in z.files}


def obj():
    from ..metrics import si_sdr, stoi
    from ..rtdemo.anc_sim import dba_change
    M = meta_all(); rows = []
    for iid in items():
        m = M[iid]; raw = load(iid, "raw"); ref = raw["T"]; n = len(ref)
        bm = busy_mask(m, n)
        for mode in MODES:
            o = raw if mode == "raw" else load(iid, mode)
            r = dict(id=iid, cond=m["cond"], session=m["session"], rec=f"{m['cond']}_s{m['session']}", mode=mode,
                     snr=db(o["T"], o["I"] + o["N"]),
                     sir_ov=db(o["T"][bm], o["I"][bm]) if bm.sum() > FS * 0.2 else np.nan,
                     sir_all=db(o["T"], o["I"]),
                     snr_noise=db(o["T"], o["N"]),
                     ov_s=float(bm.sum() / FS))
            if mode == "anc_sim":   # spectral shaping by the SIMULATED ANC; reference-based metrics not meaningful
                r.update(si_sdr=np.nan, stoi=np.nan, estoi=np.nan, dba_change=dba_change(raw["mix"], o["mix"]))
            else:
                r.update(si_sdr=si_sdr(ref, o["mix"]), stoi=stoi(ref, o["mix"]), estoi=stoi(ref, o["mix"], True))
            rows.append(r)
        print(iid, flush=True)
    pd.DataFrame(rows).to_csv(OUTW / "obj.csv", index=False)


def asr():
    from faster_whisper import WhisperModel
    from ..common import MODELS
    from ..score_r5 import asr_score
    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=1, num_workers=1,
                         download_root=str(MODELS / "whisper"))
    M = meta_all(); p = OUTW / "asr.csv"
    done = set()
    if p.exists():
        d0 = pd.read_csv(p); done = set(zip(d0.id, d0["mode"]))
    sel = json.load(open(OUTW / "selection.json"))["selected"]
    order = [i for i in sel if i in items()] + [i for i in items() if i not in sel]   # selected clips first
    if not os.environ.get("VAB_ASR_ALL"):
        # time budget (shared, OOM-prone machine): ASR on the 12 selected clips + the post-hoc best-case clip only;
        # set VAB_ASR_ALL=1 to extend Whisper scoring to the whole 21-item pool.
        o = pd.read_csv(OUTW / "obj.csv"); b = o[o["mode"] == "raw"].set_index("id")["snr"]
        q = o[o["mode"] == "causal_trk_sd8"].set_index("id")["snr"]
        best = (q - b.loc[q.index]).idxmax()
        order = [i for i in order if i in sel or i == best]
    for iid in order:
        for mode in MODES + ["target_ref"]:
            if (iid, mode) in done:
                continue
            o = load(iid, "raw" if mode == "target_ref" else mode)
            x = o["T"] if mode == "target_ref" else o["mix"]
            x = (x * LEVEL / (np.sqrt(np.mean(x ** 2)) + 1e-12)).astype(np.float32)
            segs, _ = model.transcribe(x, language="en", beam_size=1, condition_on_previous_text=False,
                                       without_timestamps=True, vad_filter=False, temperature=0.0)
            hyp = " ".join(s.text for s in segs)
            r = asr_score(M[iid]["text"], hyp); r.update(id=iid, mode=mode)
            pd.DataFrame([r]).to_csv(p, mode="a", header=not p.exists(), index=False)
        print(iid, flush=True)


def cboot(d, rec, B=4000, seed=1):
    """mean and 95% cluster-bootstrap CI (clusters = recordings)."""
    d = np.asarray(d, float); rec = np.asarray(rec)
    ok = np.isfinite(d); d, rec = d[ok], rec[ok]
    u = np.unique(rec); idx = {r: np.where(rec == r)[0] for r in u}
    rng = np.random.default_rng(seed); bs = []
    for _ in range(B):
        s = rng.choice(u, len(u), replace=True)
        bs.append(np.mean(np.concatenate([d[idx[r]] for r in s])))
    return float(np.mean(d)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def summary():
    o = pd.read_csv(OUTW / "obj.csv")
    a = pd.read_csv(OUTW / "asr.csv") if (OUTW / "asr.csv").exists() else None
    if a is not None:
        o = o.merge(a[["id", "mode", "word_correct", "wer", "ins_rate", "hyp"]], on=["id", "mode"], how="left")
        tr = a[a["mode"] == "target_ref"].set_index("id")["word_correct"]
    sel = json.load(open(OUTW / "selection.json"))
    base = o[o["mode"] == "raw"].set_index("id")
    cols = ["snr", "sir_ov", "snr_noise", "si_sdr", "stoi", "estoi"] + (["word_correct"] if a is not None else [])
    for c in cols:
        o["d_" + c] = o[c].values - base.loc[o["id"], c].values
    o["selected"] = o["id"].isin(sel["selected"])
    o.to_csv(OUTW / "metrics_items.csv", index=False)
    out = {}
    for setname, mask in (("selected12", o["selected"]), ("pool21", np.ones(len(o), bool))):
        S = {}
        for mode in MODES:
            q = o[mask & (o["mode"] == mode)]
            S[mode] = {"n": int(len(q)), "n_rec": int(q["rec"].nunique())}
            for c in cols:
                v = q["d_" + c].values
                if mode == "raw":
                    S[mode][c + "_abs_median"] = float(np.nanmedian(q[c]))
                    continue
                if np.all(~np.isfinite(v)):
                    continue
                mn, lo, hi = cboot(v, q["rec"].values)
                S[mode]["d_" + c] = dict(median=float(np.nanmedian(v)), min=float(np.nanmin(v)), max=float(np.nanmax(v)),
                                        mean=mn, ci95=[lo, hi])
        if a is not None:
            ids = o[mask]["id"].unique()
            S["target_ref_word_correct_median"] = float(np.nanmedian(tr.reindex(ids)))
        out[setname] = S
    json.dump(out, open(OUTW / "summary.json", "w"), indent=1)
    print(json.dumps(out, indent=1)[:6000])


if __name__ == "__main__":
    {"obj": obj, "asr": asr, "summary": summary}[sys.argv[1]]()
