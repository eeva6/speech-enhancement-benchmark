"""Light-weight variant scoring on cached features (selab.diar.features).

python -m selab.diar.score tune      -> grid on tune splits, writes results/diar/tune_*.csv + frozen_diar.json
python -m selab.diar.score test      -> frozen variants on test splits, writes results/diar/test_rows.csv (+ RTTM / transcripts)
"""
import json, sys, time
import numpy as np, pandas as pd
from . import core, metrics, data, spatial
from .data import CACHE
from ..common import RES

OUT = RES / "diar"
FR = core.FR


# ----------------------------------------------------------------------------------------------- loading
_cache = {}


def feats(item):
    u = item["uri"]
    if u in _cache:
        return _cache[u]
    v = np.load(CACHE / f"{u}.vad.npz"); e = np.load(CACHE / f"{u}.emb.npz"); s = np.load(CACHE / f"{u}.srp.npz")
    n = int(v["n"]); T = int(np.ceil(n / 16000 / FR))
    ref_segs, ref_words = data.ref(item)
    f = dict(T=T, dur=n / 16000, p=v["p"], hop=float(v["hop"]), wins=e["wins"], emb=e["emb"], P=s["P"], az=s["az"],
             ref=ref_segs, ref_words=ref_words, plat=dict(np.load(CACHE / f"{u}.plat.npz")))
    if item["ds"] == "easycom":
        f["yaw"] = np.load(CACHE / f"{u}.yaw.npy")
    a = CACHE / f"{u}.asr.json"
    f["asr"] = json.load(open(a)) if a.exists() else None
    _cache[u] = f
    return f


def circ_mean_deg(a):
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return np.nan
    return np.degrees(np.arctan2(np.sin(np.deg2rad(a)).mean(), np.cos(np.deg2rad(a)).mean()))


# ----------------------------------------------------------------------------------------------- one variant
def speech_mask(f, cfg):
    if cfg.get("vad") == "oracle":
        return core.segs_to_mask([(a, b) for a, b, _ in f["ref"]], f["T"])
    return core.probs_to_frames(f["p"], f["hop"], f["T"], thr=cfg.get("vad_thr", 0.5), min_sil=cfg.get("min_sil", 0.15))


def diarize(f, cfg, item=None):
    """returns frame labels (T,), info. cfg keys: vad, vad_thr, cluster (spectral|ahc), ahc_thr, kmax, oracle_k,
    spatial (None|head|world|max), beta, sigma, min_run."""
    sp = speech_mask(f, cfg)
    wins = f["wins"]
    i0 = np.round(wins[:, 0] / FR).astype(int); i1 = np.minimum(np.round(wins[:, 1] / FR).astype(int), f["T"])
    cs = np.r_[0, np.cumsum(sp)]
    frac = (cs[i1] - cs[i0]) / np.maximum(i1 - i0, 1)
    sel = np.where(frac >= cfg.get("min_frac", 0.5))[0]
    if len(sel) < 3:
        return np.where(sp, 0, -1), dict(k=1, nwin=len(sel))
    E = f["emb"][sel]
    S = E @ E.T
    if cfg.get("spatial"):
        Pw, pk, sharp = spatial.window_doa(f["P"], wins[sel], f["az"])
        az_head = pk
        if item is not None and item["ds"] == "easycom" and cfg["spatial"] in ("world", "max"):
            yaw = f["yaw"]; yw = np.array([circ_mean_deg(yaw[int(a * 20):int(b * 20)]) for a, b in wins[sel]])
            yw = np.where(np.isfinite(yw), yw, 0.0)
            az_world = az_head + yw
        else:
            az_world = az_head
        sig = cfg.get("sigma", 20.0)
        if cfg["spatial"] == "head":
            A = spatial.angle_affinity(az_head, sigma=sig)
        elif cfg["spatial"] == "world":
            A = spatial.angle_affinity(az_world, sigma=sig)
        else:   # max: talker fixed in the room (world) OR wearer fixed on the head
            A = np.maximum(spatial.angle_affinity(az_world, sigma=sig), spatial.angle_affinity(az_head, sigma=sig))
        if cfg.get("gate"):   # DOA reliability gating: only sharp SRP peaks vote (both windows must be reliable)
            lo, hi = np.percentile(sharp, cfg.get("gate_pct", (30, 80)))
            c = np.clip((sharp - lo) / max(hi - lo, 1e-9), 0, 1)
            A = A * np.outer(c, c)
        b = cfg.get("beta", 0.3)
        S = (1 - b) * S + b * A
    ok = cfg.get("oracle_k")
    if cfg.get("cluster", "spectral") == "spectral":
        fn = lambda M: core.spectral(M, kmax=cfg.get("kmax", 10), kmin=cfg.get("kmin", 2), oracle_k=ok)
    else:
        fn = lambda M: core.ahc(M, thr=cfg.get("ahc_thr", 0.6), oracle_k=ok)
    lab, info = core.cluster_big(S, fn, nmax=cfg.get("nmax", 1500))
    if cfg.get("refine", True) and not cfg.get("spatial"):
        lab = core.refine(E, lab, min_frac=cfg.get("min_cluster", 0.02), oracle_k=ok)
    elif cfg.get("refine", True):
        lab = _absorb_small(S, lab, cfg.get("min_cluster", 0.02))
    fl, V = core.frame_labels(wins[sel], lab, sp, min_run=cfg.get("min_run", 0.25))
    info.update(nwin=len(sel), k_final=int(lab.max() + 1))
    return fl, info


def _absorb_small(S, lab, min_frac):
    ks, cnt = np.unique(lab, return_counts=True)
    keep = ks[cnt >= max(2, min_frac * len(lab))]
    if len(keep) == 0:
        return np.zeros_like(lab)
    out = lab.copy()
    for k in ks:
        if k in keep:
            continue
        idx = np.where(lab == k)[0]
        sim = np.stack([S[np.ix_(idx, np.where(lab == j)[0])].mean(1) for j in keep], 1)
        out[idx] = keep[np.argmax(sim, 1)]
    return np.unique(out, return_inverse=True)[1]


def platform_labels(f, item, cfg):
    """'Zoom-style' per-participant streams -> activity. LibriCSS: energy on dry loudspeaker feeds (> max-35 dB).
    EasyCom: close-mic Silero VAD with cross-talk dominance (stream level within dom_db of the loudest active stream,
    after per-stream level normalisation); wearer (no close mic) = array speech when no close-mic stream is active."""
    T = f["T"]; pl = f["plat"]; segs = []
    if item["ds"] == "libricss":
        edb = pl["edb"]; lag = int(pl["lag"]); sh = int(round(lag / 16000 / FR))
        for c in range(edb.shape[0]):
            m = edb[c] > edb[c].max() - cfg.get("e_rel", 35.0)
            m = np.r_[np.zeros(max(sh, 0), bool), m][:T] if sh >= 0 else m[-sh:][:T]
            ss = core.merge_close(core.mask_to_segs(m), max(0.3, cfg.get("min_sil", 0.3)))
            segs += [(a, b, f"ch{c}") for a, b in ss if b - a >= 0.2]
    else:
        pr = pl["probs"]; edb = pl["edb"]; pids = list(pl["pids"])
        n = min(T, edb.shape[1])
        act = np.zeros((len(pids), n), bool)
        for i in range(len(pids)):
            m = core.probs_to_frames(pr[i], 512 / 16000, n, thr=cfg.get("vad_thr", 0.5), min_sil=cfg.get("min_sil", 0.15))
            act[i] = m[:n]
        # level normalisation: median frame energy over the stream's own active frames
        ref_lvl = np.array([np.median(edb[i, :n][act[i]]) if act[i].any() else 0 for i in range(len(pids))])
        lv = edb[:, :n] - ref_lvl[:, None]
        lv_act = np.where(act, lv, -np.inf)
        mx = lv_act.max(0)
        dom = act & (lv >= mx[None, :] - cfg.get("dom_db", 6.0))
        for i, p in enumerate(pids):
            ss = core.merge_close(core.mask_to_segs(dom[i]), max(0.2, cfg.get("min_sil", 0.15)))
            segs += [(a, b, f"P{p}") for a, b in ss if b - a >= 0.2]
        arr = core.probs_to_frames(f["p"], f["hop"], T, thr=cfg.get("arr_thr", 0.5))[:n]
        wear = arr & ~act.any(0)
        segs += [(a, b, "glasses") for a, b in core.merge_close(core.mask_to_segs(wear), max(0.2, cfg.get("min_sil", 0.15)))
                 if b - a >= 0.2]
    return segs


def score_segs(f, hyp, words_lab=None):
    r = dict()
    for c in (0.0, 0.25):
        d = metrics.der(f["ref"], hyp, collar=c, T=f["T"] + 10)
        tag = "c0" if c == 0 else "c25"
        r.update({f"der_{tag}": d["der"], f"miss_{tag}": d["miss"], f"fa_{tag}": d["fa"], f"conf_{tag}": d["conf"]})
    r["jer"] = metrics.jer(f["ref"], hyp)
    r["n_ref"] = len({s for *_, s in f["ref"]})
    # hyp speakers with >= 5 s total (tiny clusters do not count as a 'speaker' for counting)
    tot = {}
    for a, b, s in hyp:
        tot[s] = tot.get(s, 0) + b - a
    r["n_hyp"] = sum(1 for v in tot.values() if v >= 5.0)
    if words_lab is not None:
        hw = {}
        for a, b, w, k in words_lab:
            t = data.norm_text(w).split()
            hw.setdefault(k, []).extend(t)
        c = metrics.cpwer(f["ref_words"], hw)
        r["cpwer"] = c["cpwer"]
        allh = [t for a, b, w, k in words_lab for t in data.norm_text(w).split()]
        refw = [t for a, s, txt in sorted(_ref_utts(f), key=lambda x: x[0]) for t in txt]
        r["wer_all"] = metrics.wer_all(refw, allh)
    return r


def _ref_utts(f):
    return f.setdefault("_ref_utts", [])


def segs_to_framelab(segs, T):
    """hyp segments -> single-label frame array for word assignment (later segment wins on overlap)."""
    lab = np.full(T, -1, int); keys = {}
    for a, b, s in segs:
        k = keys.setdefault(s, len(keys))
        lab[int(a / FR):min(T, int(b / FR))] = k
    return lab, {v: k for k, v in keys.items()}


def run_variant(item, name, cfg, with_words=False, save=False):
    f = feats(item)
    t = time.time()
    if cfg.get("kind") == "platform":
        hyp = platform_labels(f, item, cfg)
        lab, names = segs_to_framelab(hyp, f["T"])
    else:
        lab, info = diarize(f, cfg, item)
        hyp = core.labels_to_segments(lab)
        names = None
    sec = time.time() - t
    wl = core.assign_words(f["asr"], lab) if (with_words and f["asr"] is not None) else None
    r = score_segs(f, hyp, wl)
    r.update(uri=item["uri"], ds=item["ds"], cond=item.get("cond", f"s{item['sess']}"), variant=name,
             cluster_sec=sec, dur=f["dur"])
    if save:
        d = OUT / "rttm" / name; d.mkdir(parents=True, exist_ok=True)
        core.write_rttm(hyp, d / f"{item['uri']}.rttm", uri=item["uri"])
        if wl is not None:
            (OUT / "transcripts" / name).mkdir(parents=True, exist_ok=True)
            nm = None if names is None else {k: str(v) for k, v in names.items()}
            open(OUT / "transcripts" / name / f"{item['uri']}.txt", "w").write(core.transcript_text(wl, nm))
    return r


def add_ref_utts(item):
    """time-ordered reference word list for speaker-agnostic WER."""
    f = feats(item)
    if f.get("_ref_utts"):
        return
    if item["ds"] == "libricss":
        from ..libricss import read_info
        A = data.libricss_clock(item)
        f["_ref_utts"] = [(r["start"], r["spk"], data.norm_text(r["text"]).split()) for r in read_info(item["dir"])]
    else:
        from .. import ec_r7 as E
        import soundfile as sf
        out = []; off = 0.0
        for seg in data.easycom_segs(item):
            n = sf.info(str(E.CACHE / f"Session_{item['sess']}" / f"{seg}.wav")).frames / 16000
            for u in E.transcripts(item["sess"], seg):
                out.append((off + u["start"], u["pid"], data.norm_text(u["text"]).split()))
            off += n
        f["_ref_utts"] = out


# ----------------------------------------------------------------------------------------------- grids
def tune_gate():
    """EasyCom only: confidence-gated spatial fusion, searched around the frozen single-channel bases."""
    fp = OUT / "frozen_diar.json"; fz = json.load(open(fp)); best = fz["easycom"]
    its = data.items("ec_tune"); rows = []
    for fam, base in (("spec_gate", best["spec"]), ("ahc_gate", best["ahc"])):
        for m in ("head", "world", "max"):
            for b in (0.15, 0.3, 0.5):
                for sg in (15.0, 30.0):
                    cfg = dict(base, spatial=m, beta=b, sigma=sg, gate=True)
                    for it in its:
                        r = run_variant(it, fam, cfg); r["cfg"] = json.dumps(cfg); rows.append(r)
    df = pd.DataFrame(rows); df.to_csv(OUT / "tune_easycom_gate.csv", index=False)
    g = df.groupby(["variant", "cfg"]).der_c25.mean().reset_index()
    for fam in ("spec_gate", "ahc_gate"):
        best[fam] = json.loads(g[g.variant == fam].sort_values("der_c25").iloc[0].cfg)
        print(fam, best[fam], g[g.variant == fam].der_c25.min(), flush=True)
    json.dump(fz, open(fp, "w"), indent=1)


def test_gate():
    fz = json.load(open(OUT / "frozen_diar.json"))["easycom"]; rows = []
    for it in data.items("ec_test"):
        add_ref_utts(it)
        for name, cfg in (("B_gated_spectral", fz["spec_gate"]), ("B_gated_ahc", fz["ahc_gate"]),
                          ("B_gated_spectral_oracleVAD", dict(fz["spec_gate"], vad="oracle")),
                          ("B_gated_ahc_oracleVAD", dict(fz["ahc_gate"], vad="oracle"))):
            r = run_variant(it, name, cfg, with_words=True, save=True); r["cfg"] = json.dumps(cfg); rows.append(r)
            print(it["uri"], name, f"DER {r['der_c25']:.3f}/{r['der_c0']:.3f} cpWER {r['cpwer']:.3f} nhyp {r['n_hyp']}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "test_rows_easycom_gate.csv", index=False)


def tune_grid(ds):
    G = []
    thrs = (0.35, 0.5, 0.65) if ds == "libricss" else (0.02, 0.05, 0.1, 0.2)
    for thr in thrs:
        for ms in (0.15, 0.5, 1.0):
            for kmax in (8, 10) if ds == "libricss" else (6,):
                G.append(("spec", dict(cluster="spectral", vad_thr=thr, min_sil=ms, kmax=kmax)))
            for at in (0.5, 0.6, 0.7, 0.8, 0.9):
                G.append(("ahc", dict(cluster="ahc", vad_thr=thr, min_sil=ms, ahc_thr=at)))
    return G


def tune_spatial_grid(ds, base_spec, base_ahc):
    G = []
    modes = ("head",) if ds == "libricss" else ("head", "world", "max")
    for m in modes:
        for b in (0.08, 0.15, 0.3, 0.5):
            for sg in (15.0, 30.0):
                G.append(("spec_sp", dict(base_spec, spatial=m, beta=b, sigma=sg)))
                G.append(("ahc_sp", dict(base_ahc, spatial=m, beta=b, sigma=sg)))
    return G


def tune(dss=("easycom", "libricss")):
    fp = OUT / "frozen_diar.json"
    frozen = json.load(open(fp)) if fp.exists() else {}
    for ds, sp in (("easycom", "ec_tune"), ("libricss", "lc_tune")):
        if ds not in dss:
            continue
        its = [it for it in data.items(sp) if (CACHE / f"{it['uri']}.srp.npz").exists() and (CACHE / f"{it['uri']}.plat.npz").exists()]
        if not its:
            print("no cached items for", sp); continue
        rows = []
        for fam, cfg in tune_grid(ds):
            for it in its:
                r = run_variant(it, fam, cfg); r["cfg"] = json.dumps(cfg); rows.append(r)
        df = pd.DataFrame(rows)
        g = df.groupby(["variant", "cfg"]).der_c25.mean().reset_index()
        best = {fam: json.loads(g[g.variant == fam].sort_values("der_c25").iloc[0].cfg) for fam in ("spec", "ahc")}
        rows2 = []
        for fam, cfg in tune_spatial_grid(ds, best["spec"], best["ahc"]):
            for it in its:
                r = run_variant(it, fam, cfg); r["cfg"] = json.dumps(cfg); rows2.append(r)
        df2 = pd.DataFrame(rows2)
        g2 = df2.groupby(["variant", "cfg"]).der_c25.mean().reset_index()
        for fam in ("spec_sp", "ahc_sp"):
            best[fam] = json.loads(g2[g2.variant == fam].sort_values("der_c25").iloc[0].cfg)
        if ds == "easycom":   # labelled oracle-assisted variants: best world/max and best raw head
            for m in ("head", "world", "max"):
                gm = g2[g2.cfg.str.contains(f'"spatial": "{m}"')].sort_values("der_c25")
                best[f"sp_{m}"] = json.loads(gm.iloc[0].cfg)
        # platform tuning
        rows3 = []
        pg = [dict(kind="platform", e_rel=e, min_sil=ms) for e in (30.0, 35.0, 40.0) for ms in (0.3, 0.5, 1.0)] if ds == "libricss" else \
             [dict(kind="platform", dom_db=d, vad_thr=t, min_sil=ms, arr_thr=at) for d in (3.0, 6.0, 10.0) for t in (0.3, 0.5)
              for ms in (0.15, 0.5, 1.0) for at in (0.1, 0.5)]
        for cfg in pg:
            for it in its:
                r = run_variant(it, "platform", cfg); r["cfg"] = json.dumps(cfg); rows3.append(r)
        df3 = pd.DataFrame(rows3)
        g3 = df3.groupby("cfg").der_c25.mean().sort_values()
        best["platform"] = json.loads(g3.index[0])
        pd.concat([df, df2, df3]).to_csv(OUT / f"tune_{ds}.csv", index=False)
        frozen[ds] = best
        print(ds, json.dumps(best, indent=1), flush=True)
        json.dump(frozen, open(fp, "w"), indent=1)


def test_variants(ds, fz):
    V = [("A_spectral", fz["spec"]), ("A_ahc", fz["ahc"]),
         ("A_spectral_oracleVAD", dict(fz["spec"], vad="oracle")), ("A_ahc_oracleVAD", dict(fz["ahc"], vad="oracle")),
         ("A_spectral_oracleK", dict(fz["spec"], oracle_k=-1)),
         ("B_spatial_spectral", fz["spec_sp"]), ("B_spatial_ahc", fz["ahc_sp"]),
         ("B_spatial_spectral_oracleVAD", dict(fz["spec_sp"], vad="oracle")),
         ("platform", fz["platform"])]
    if ds == "easycom":
        V += [("B_head_rawDOA", fz["sp_head"]), ("B_world_poseOracle", fz["sp_world"]), ("B_max_poseOracle", fz["sp_max"]),
              ("B_head_rawDOA_oracleVAD", dict(fz["sp_head"], vad="oracle")),
              ("B_max_poseOracle_oracleVAD", dict(fz["sp_max"], vad="oracle"))]
        if "spec_gate" in fz:
            V += [("B_gated_spectral", fz["spec_gate"]), ("B_gated_ahc", fz["ahc_gate"]),
                  ("B_gated_spectral_oracleVAD", dict(fz["spec_gate"], vad="oracle")),
                  ("B_gated_ahc_oracleVAD", dict(fz["ahc_gate"], vad="oracle"))]
    return V


def test():
    fz = json.load(open(OUT / "frozen_diar.json"))
    rows = []
    for ds, sp in (("libricss", "lc_test"), ("easycom", "ec_test")):
        if ds not in fz:
            continue
        for it in data.items(sp):
            if not (CACHE / f"{it['uri']}.plat.npz").exists():
                print("missing features", it["uri"]); continue
            add_ref_utts(it)
            f = feats(it)
            for name, cfg in test_variants(ds, fz[ds]):
                cfg = dict(cfg)
                if cfg.get("oracle_k") == -1:
                    cfg["oracle_k"] = len({s for *_, s in f["ref"]})
                r = run_variant(it, name, cfg, with_words=True, save=True)
                r["cfg"] = json.dumps(cfg); rows.append(r)
                print(it["uri"], name, f"DER {r['der_c25']:.3f}/{r['der_c0']:.3f} cpWER {r.get('cpwer', np.nan):.3f}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "test_rows.csv", index=False)


if __name__ == "__main__":
    if sys.argv[1] == "gate":
        tune_gate(); test_gate()
    elif sys.argv[1] == "tune":
        tune(tuple(sys.argv[2:]) or ("easycom", "libricss"))
    else:
        test()
