"""Venture A/B set, GROUP clips: 'hear the talkers in sector X over the talkers elsewhere' on REAL LibriCSS 7-mic.

LibriCSS is ONE read-speech 'meeting' per recording (8 loudspeakers taking turns, at most ~2 overlapping at once),
not two concurrent conversations.  So a true 'conversation X vs conversation Y' does not exist in it.  The closest
honest construction: target GROUP = all loudspeakers within +-50 deg of a sector centre (>= 2 distinct talkers who
speak inside the window); competing = every other loudspeaker.  Windows are cut at group-utterance boundaries.

python -m selab.venture_ab.group select   -> OUTW/group_selection.json (pre-registered rule, seed 20261026)
python -m selab.venture_ab.group proc     -> OUTW/groups/<gid>/<mode>.npz (resumable)
python -m selab.venture_ab.group score    -> OUTW/group_obj.csv, group_asr.csv (resumable)
"""
import json, sys, time
import numpy as np, pandas as pd, soundfile as sf
from scipy.signal import fftconvolve, lfilter
from ..common import MIX, FS
from .. import libricss as L
from .. import r5methods as R5
from .. import r6
from .build import OUTW, meta_all, apply_stft_w, anc_filters, wait_mem, sysid_lean

GMODES = ["raw", "sector_sd8", "sector_ds32", "oracle_mwf", "anc_sim"]
HALF = 50.0
SEED = 20261026


def angd(a, b):
    return abs((a - b + 180) % 360 - 180)


def recordings():
    M = meta_all(); recs = {}
    for m in M.values():
        if m["session"] in (3, 4, 5) and m["cond"] in ("OV10", "OV20", "OV40"):
            recs.setdefault((m["cond"], m["session"]), m)
    return recs


def utt_channels(d, info):
    for u in info:
        x, _ = sf.read(d + "/clean/each_spk.wav", dtype="float32", start=int(u["start"] * FS), stop=int(u["end"] * FS))
        u["ch"] = int(np.argmax((x ** 2).sum(0)))
    return info


def candidates(cond, s, m0, dref):
    import glob
    d = [p for p in glob.glob(str(L.LC / cond / "*")) if f"session{s}_" in p][0]
    info = utt_channels(d, L.read_info(d))
    T_end = sf.info(d + "/record/raw_recording.wav").duration
    az = {k: dref.get(f"{s}_{k}") for k in range(8)}
    cands = []
    for c in sorted({v for v in az.values() if v is not None}):
        G = sorted(k for k, v in az.items() if v is not None and angd(v, c) <= HALF)
        if len(G) < 2:
            continue
        gu = [i for i, u in enumerate(info) if u["ch"] in G]
        for ii, i in enumerate(gu):
            for j in gu[ii:]:
                ws, we = info[i]["start"], info[j]["end"]
                if not (8.0 <= we - ws <= 15.0) or ws < 14 or we > T_end - 14:
                    continue
                inside = [k for k in gu if info[k]["start"] >= ws and info[k]["end"] <= we]
                cross = [k for k in gu if info[k]["end"] > ws and info[k]["start"] < we and k not in inside]
                if cross or len({info[k]["ch"] for k in inside}) < 2:
                    continue
                oth = [k for k, u in enumerate(info) if u["ch"] not in G and u["end"] > ws and u["start"] < we]
                if not oth:
                    continue
                gm = np.zeros(int((we - ws) * 100), bool); om = gm.copy()
                for k in inside:
                    gm[int((info[k]["start"] - ws) * 100):int((info[k]["end"] - ws) * 100)] = True
                for k in oth:
                    om[max(int((info[k]["start"] - ws) * 100), 0):int((info[k]["end"] - ws) * 100)] = True
                both = float((gm & om).sum() / 100)
                if both < 1.0:
                    continue
                gaz = np.rad2deg(np.angle(np.mean([np.exp(1j * np.deg2rad(az[k])) for k in G])))  % 360
                cands.append(dict(gid=f"G_{cond}_s{s}_{int(ws)}", cond=cond, session=s, rec_dir=d, ws=ws, we=we,
                                  group_ch=G, group_az={k: az[k] for k in G}, sector_centre=float(gaz),
                                  group_utts=[info[k]["uid"] for k in inside],
                                  text=" ".join(info[k]["text"] for k in sorted(inside, key=lambda k: info[k]["start"])),
                                  other_ch=sorted({info[k]["ch"] for k in oth}), both_s=both, clock=m0["clock"],
                                  mic_xy=m0["mic_xy"]))
    # one candidate per distinct window (sector centres can produce the same group)
    seen, out = set(), []
    for c in cands:
        key = (c["ws"], c["we"], tuple(c["group_ch"]))
        if key not in seen:
            seen.add(key); out.append(c)
    return out


def select():
    dref = json.load(open(MIX / "r5" / "doa_ref.json"))
    rng = np.random.default_rng(SEED); pick, n_c = [], {}
    for (cond, s), m0 in sorted(recordings().items()):
        c = candidates(cond, s, m0, dref); n_c[f"{cond}_s{s}"] = len(c)
        if c:
            pick.append(c[int(rng.integers(len(c)))])
    json.dump(dict(seed=SEED, half_width_deg=HALF, n_candidates=n_c, selected=pick), open(OUTW / "group_selection.json", "w"), indent=1)
    print(json.dumps(n_c), [p["gid"] for p in pick])


def proc_group(g, anc, W=12.0):
    od = OUTW / "groups" / g["gid"]
    if (od / "done.json").exists():
        return
    od.mkdir(parents=True, exist_ok=True); t0s = time.time()
    A = np.array(g["clock"])
    lag = np.polyval(A, (g["ws"] + g["we"]) / 2)
    y, x, base = L.read_win(g["rec_dir"], (g["ws"] * FS + lag) / FS - W - 1.5, (g["we"] * FS + lag) / FS + W + 1.5, margin=1.0)
    Ab = L.shift_clock(A, base); B = int(round(base * FS))
    a, b = int(g["ws"] * FS) - B, int(g["we"] * FS) - B
    lag_b = np.polyval(Ab, (a + b) / 2 / FS)
    ra, rb = int(a + lag_b), int(b + lag_b)
    Hh, res, sh = sysid_lean(y, x, ra / FS - W, rb / FS + W, Ab)
    h = np.fft.irfft(Hh, axis=0).astype(np.float32)
    n = rb - ra; NS = L.NS
    T = np.zeros((7, n)); I = np.zeros((7, n)); az_est = {}
    for k in range(x.shape[1]):
        src = x[ra - sh - 2 * NS:rb - sh, k].astype(np.float64)
        if not np.any(src) or not np.any(h[:, :, k]):
            continue
        for mi in range(7):
            img = fftconvolve(src, h[:, mi, k])[2 * NS:2 * NS + n]
            (T if k in g["group_ch"] else I)[mi] += img
        try:
            az_est[k] = L.fit_az(L.direct_tdoa(h[:, :, k]))[0]
        except Exception:
            pass
    yy = y[ra:rb].T.astype(np.float64); del y, x, Hh, h
    N = yy - T - I; xy = g["mic_xy"]
    comps = dict(mix=yy, T=T, I=I, N=N); outs = {"raw": {k: v[0].copy() for k, v in comps.items()}}
    ctr = r6.const_track(yy, g["sector_centre"])
    outs["sector_sd8"] = {k: r6.run_filter("sd8", v, xy, ctr)[0].astype(np.float64) for k, v in comps.items()}
    D = R5.steer2d(xy, g["sector_centre"], np.fft.rfftfreq(R5.NFFT, 1 / FS)) / len(xy)
    outs["sector_ds32"] = {k: apply_stft_w(D, v) for k, v in comps.items()}
    # ORACLE multichannel Wiener filter for the whole group (rank > 1 target): w = (Rs+Rv)^-1 Rs e0
    XT = R5.mstft(T); XV = R5.mstft(I + N)
    Rs = np.einsum("mft,nft->fmn", XT, XT.conj()) / XT.shape[2]
    Rv = np.einsum("mft,nft->fmn", XV, XV.conj()) / XV.shape[2]
    Ry = Rs + Rv; Ry = Ry + 1e-3 * np.real(np.trace(Ry, axis1=1, axis2=2))[:, None, None] / 7 * np.eye(7)
    w = np.linalg.solve(Ry, Rs[:, :, 0:1])[..., 0]          # (F,M): output = w^H y
    outs["oracle_mwf"] = {k: apply_stft_w(w, v) for k, v in comps.items()}
    hc, hb = anc["companion"], anc["babble"]
    a_T, a_I, a_N = lfilter(hc, 1, T[0]), lfilter(hb, 1, I[0]), lfilter(hb, 1, N[0])
    outs["anc_sim"] = dict(mix=a_T + a_I + a_N, T=a_T, I=a_I, N=a_N)
    for mode, d in outs.items():
        np.savez_compressed(od / f"{mode}.npz", **{k: v.astype(np.float32) for k, v in d.items()})
    info = dict(gid=g["gid"], n=n, az_est={str(k): v for k, v in az_est.items()},
                sec=time.time() - t0s)
    json.dump(info, open(od / "done.json", "w"), indent=1); print(json.dumps(info), flush=True)


def proc():
    sel = json.load(open(OUTW / "group_selection.json")); anc, _ = anc_filters()
    for g in sel["selected"]:
        try:
            wait_mem(); proc_group(g, anc)
        except Exception as e:
            import traceback; print("FAIL", g["gid"], repr(e), traceback.format_exc()[-1500:], flush=True)


def masks(g, n):
    info = {u["uid"]: u for u in L.read_info(g["rec_dir"]) if u["end"] > g["ws"] and u["start"] < g["we"]}
    utt_channels(g["rec_dir"], list(info.values()))
    gm = np.zeros(n, bool); om = np.zeros(n, bool)
    for u in info.values():
        if u["end"] <= g["ws"] or u["start"] >= g["we"]:
            continue
        a, b = max(int((u["start"] - g["ws"]) * FS), 0), min(int((u["end"] - g["ws"]) * FS), n)
        (gm if u["ch"] in g["group_ch"] else om)[a:b] = True
    return gm, om


def score():
    from ..metrics import si_sdr, stoi
    from ..rtdemo.anc_sim import dba_change
    from ..score_r5 import asr_score
    from .score import db, LEVEL
    from faster_whisper import WhisperModel
    from ..common import MODELS
    sel = {g["gid"]: g for g in json.load(open(OUTW / "group_selection.json"))["selected"]}
    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=1, num_workers=1, download_root=str(MODELS / "whisper"))
    outp = OUTW / "group_metrics_partial.csv"
    done = set(pd.read_csv(outp)["id"]) if outp.exists() else set()
    for gid, g in sel.items():
        od = OUTW / "groups" / gid
        if not (od / "done.json").exists() or gid in done:
            continue
        rows = []
        ld = lambda mo: {k: v.astype(np.float64) for k, v in np.load(od / f"{mo}.npz").items()}
        raw = ld("raw"); n = len(raw["T"]); gm, om = masks(g, n); both = gm & om
        for mode in GMODES + ["target_ref"]:
            o = raw if mode in ("raw", "target_ref") else ld(mode)
            x = o["T"] if mode == "target_ref" else o["mix"]
            r = dict(id=gid, kind="group", cond=g["cond"], session=g["session"], rec=f"{g['cond']}_s{g['session']}", mode=mode)
            if mode != "target_ref":
                r.update(snr=db(o["T"], o["I"] + o["N"]), sir_ov=db(o["T"][both], o["I"][both]) if both.sum() > 0.2 * FS else np.nan,
                         sir_all=db(o["T"], o["I"]), snr_noise=db(o["T"], o["N"]), ov_s=float(both.sum() / FS))
                if mode == "anc_sim":
                    r.update(si_sdr=np.nan, stoi=np.nan, estoi=np.nan, dba_change=dba_change(raw["mix"], o["mix"]))
                else:
                    r.update(si_sdr=si_sdr(raw["T"], x), stoi=stoi(raw["T"], x), estoi=stoi(raw["T"], x, True))
            xx = (x * LEVEL / (np.sqrt(np.mean(x ** 2)) + 1e-12)).astype(np.float32)
            segs, _ = model.transcribe(xx, language="en", beam_size=1, condition_on_previous_text=False,
                                       without_timestamps=True, vad_filter=False, temperature=0.0)
            r.update(asr_score(g["text"], " ".join(s.text for s in segs)))
            rows.append(r)
        pd.DataFrame(rows).to_csv(outp, mode="a", header=not outp.exists(), index=False)
        print(gid, flush=True)
    d = pd.read_csv(outp)
    if d["id"].nunique() >= sum((OUTW / "groups" / k / "done.json").exists() for k in sel):
        d.to_csv(OUTW / "group_metrics_raw.csv", index=False)


if __name__ == "__main__":
    {"select": select, "proc": proc, "score": score}[sys.argv[1]]()
