"""Round 7 phase 1: EasyCom preparation (resumable; every stage skips work whose outputs exist).

python -m selab.prep_r7 resample   [--sess 4,12,10,11]   # 48k -> 16k array cache + close-mic pass-1 lags
python -m selab.prep_r7 align      [--sess ...]          # drift/offset fit, aligned 16k close mics, residuals
python -m selab.prep_r7 doa        [--sess ...]          # per-50 ms reference DOA of every participant (head frame)
python -m selab.prep_r7 validate   [--sess ...]          # SRP (measured ATFs, ch1-4) vs reference DOA on single-talker stretches
python -m selab.prep_r7 items      [--sess ...]          # mixtures/r7/{val,test}/<id>/ + meta.json
Outputs: data/easycom/r7_16k/Session_N/ (cache, EasyCom-derived: never distribute), results/r7/*.csv|json.

Close-mic alignment model.  The close mics are labelled 48 kHz but run at ~48008.6 Hz.  Pass 1 warps each close
mic onto the array clock at the nominal 48008.6 Hz (cubic-spline resampling at 48 kHz, then 48k->16k polyphase),
then measures the lag of array ch2 (front-centre frame mic) relative to the warped close mic with GCC-PHAT
(200-4000 Hz) in 4 s windows (1 s hop) in which the participant is transcribed as talking.  A robust line
lag(t) = a + b t is fitted per (minute, participant); b is the residual clock-rate error and a the offset
(clock offset + acoustic path talker->array).  Pass 2 re-warps with that line, so the aligned close mic is
time-aligned to the DIRECT-PATH ARRIVAL at array ch2 (not to the talker's mouth), and re-measures the window
lags: the alignment residual is the spread of those re-measured lags.
"""
import argparse, json, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd, soundfile as sf
from scipy.signal import resample_poly
from scipy.ndimage import map_coordinates
from .common import FS, MIX, RES
from . import ec_r7 as E

R7 = RES / "r7"
WIN_S, HOP_S, MAXLAG_S = 4.0, 1.0, 0.1


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def write_f32(path, x, fs=FS):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.wav")
    sf.write(str(tmp), np.asarray(x, np.float32).T if np.ndim(x) > 1 else np.asarray(x, np.float32), fs, subtype="FLOAT")
    tmp.replace(path)


# ---------------------------------------------------------------------------------------------- alignment
def warp_close(c48, a=0.0, b=0.0, fs_c=E.CLOSE_FS_NOMINAL, n_out48=2880000):
    """close-mic samples (true rate fs_c) -> array 48 kHz grid with extra lag line a + b t (s): out(t) = c((t - a - b t))."""
    t = np.arange(n_out48) / 48000.0
    idx = (t - a - b * t) * fs_c
    y = map_coordinates(c48.astype(np.float64), [idx], order=3, mode="constant", cval=0.0)
    y[(idx < 0) | (idx > len(c48) - 1)] = 0.0
    return resample_poly(y, 1, 3).astype(np.float32)


def gcc_lag(ref, sig, maxlag):
    """lag (samples, float) by which ref lags sig; and the PHAT peak ratio (peak / rms of correlation)."""
    n = len(ref) + len(sig)
    nf = 1 << int(np.ceil(np.log2(n)))
    A = np.fft.rfft(ref, nf); B = np.fft.rfft(sig, nf)
    f = np.fft.rfftfreq(nf, 1 / FS); band = (f >= 200) & (f <= 4000)
    G = A * np.conj(B); G = G / (np.abs(G) + 1e-12); G[~band] = 0
    r = np.fft.irfft(G, nf)
    r = np.concatenate([r[-maxlag:], r[:maxlag + 1]])
    k = int(np.argmax(r))
    d = 0.0
    if 0 < k < len(r) - 1:
        y0, y1, y2 = r[k - 1], r[k], r[k + 1]
        den = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    return (k - maxlag + d), float(r[k] / (np.sqrt(np.mean(r ** 2)) + 1e-12))


def active_mask(utts, pid, n, fs=FS):
    m = np.zeros(n, bool)
    for u in utts:
        if u["pid"] == pid:
            m[int(u["start"] * fs): int(u["end"] * fs)] = True
    return m


def window_lags(arr_ch, c16, act):
    W, H, L = int(WIN_S * FS), int(HOP_S * FS), int(MAXLAG_S * FS)
    rows = []
    for s in range(0, len(arr_ch) - W + 1, H):
        if act[s:s + W].mean() < 0.5:
            continue
        seg = c16[s:s + W]
        if np.std(seg) < 1e-7:
            continue
        lag, q = gcc_lag(arr_ch[s:s + W], seg, L)
        rows.append((s / FS + WIN_S / 2, lag / FS, q))
    return np.array(rows).reshape(-1, 3)


def robust_line(rows, qmin=6.0, tol=0.5e-3):
    """fit lag = a + b t on windows with PHAT peak ratio >= qmin, iteratively dropping |res| > tol (s)."""
    r = rows[rows[:, 2] >= qmin] if len(rows) else rows
    if len(r) < 4:
        return None
    t, l = r[:, 0], r[:, 1]
    keep = np.abs(l - np.median(l)) <= 2e-3
    for _ in range(5):
        if keep.sum() < 4:
            return None
        if np.ptp(t[keep]) >= 20:
            b, a = np.polyfit(t[keep], l[keep], 1)
        else:
            b, a = 0.0, float(np.median(l[keep]))
        res = l - (a + b * t); k2 = np.abs(res) <= tol
        if (k2 == keep).all():
            break
        keep = k2
    return dict(a=float(a), b=float(b), n_win=int(len(rows)), n_good=int(len(r)), n_fit=int(keep.sum()),
                span_s=float(np.ptp(t[keep])) if keep.sum() else 0.0)


def stage_resample(sessions):
    for s in sessions:
        cd = E.CACHE / f"Session_{s}"; cd.mkdir(parents=True, exist_ok=True)
        for seg in E.segs(s):
            out = cd / f"{seg}.wav"
            if not out.exists():
                x, sr = sf.read(str(E.MAIN / "Glasses_Microphone_Array_Audio" / f"Session_{s}" / f"{seg}.wav"),
                                dtype="float32", always_2d=True)
                assert sr == 48000 and x.shape[1] == 6, (sr, x.shape)
                write_f32(out, resample_poly(x, 1, 3, axis=0).T)
            arr = None
            utts = E.transcripts(s, seg)
            if not utts:
                log("no transcript yet (pass 1 deferred)", s, seg); continue
            for pid in E.close_ids(s, seg):
                pj = cd / f"{seg}_P{pid}.pass1.json"
                if pj.exists():
                    continue
                if arr is None:
                    arr = E.load_array16(s, seg)
                c48, sr = sf.read(str(E.MAIN / "Close_Microphone_Audio" / f"Session_{s}" / f"{seg}_Participant_ID_{pid}.wav"), dtype="float32")
                assert sr == 48000
                c16 = warp_close(c48)
                rows = window_lags(arr[1], c16, active_mask(utts, pid, arr.shape[1]))
                fit = robust_line(rows)
                json.dump(dict(sess=s, seg=seg, pid=pid, fit=fit, rows=rows.tolist()), open(pj, "w"))
            log("resample+pass1", s, seg)


def _dist(s, seg, pid):
    d = doa_load(s, seg)
    k = f"dist_{pid}"
    return float(np.nanmedian(d[k])) if d is not None and k in d and np.isfinite(d[k]).any() else np.nan


def align_loo(sessions):
    """out-of-sample alignment check: predict each fitted participant's lag offset from the OTHER close mics of the
    same minute (shared clock offset) plus the pose-derived talker->array distance; report |error|."""
    errs = []
    for s in sessions:
        cd = E.CACHE / f"Session_{s}"
        p1 = [json.load(open(p)) for p in sorted(cd.glob("*.pass1.json"))]
        by = {}
        for j in p1:
            if j["fit"] and j["fit"]["n_fit"] >= 6 and np.isfinite(_dist(s, j["seg"], j["pid"])):
                by.setdefault(j["seg"], []).append(j["fit"]["a"] - _dist(s, j["seg"], j["pid"]) / E.C)
        for seg, v in by.items():
            for i in range(len(v)):
                if len(v) > 1:
                    errs.append(v[i] - np.median(np.delete(np.array(v), i)))
    e = np.abs(np.array(errs)) * 1e3
    return dict(n=int(len(e)), median_abs_ms=float(np.median(e)), p90_abs_ms=float(np.quantile(e, 0.9)))


def stage_align(sessions):
    rows_out = []
    for s in sessions:
        cd = E.CACHE / f"Session_{s}"
        p1 = {(j["seg"], j["pid"]): j for j in (json.load(open(p)) for p in sorted(cd.glob("*.pass1.json")))}
        bs = [j["fit"]["b"] for j in p1.values() if j["fit"] and j["fit"]["span_s"] >= 30 and j["fit"]["n_fit"] >= 8]
        b_sess = float(np.median(bs)) if bs else 0.0
        for (seg, pid), j in sorted(p1.items()):
            aj = cd / f"{seg}_P{pid}.align.json"
            if aj.exists():
                rows_out.append(json.load(open(aj))); continue
            fit = j["fit"]
            if fit is None:
                a, b, how = None, b_sess, "no_fit"
            elif fit["span_s"] >= 30 and fit["n_fit"] >= 8:
                a, b, how = fit["a"], fit["b"], "minute_line"
            else:
                # offset only, slope from the session median (re-centre a at the session slope)
                r = np.array(j["rows"]); r = r[r[:, 2] >= 6.0]
                a = float(np.median(r[:, 1] - b_sess * r[:, 0])); b = b_sess; how = "session_slope"
            if a is None:
                # minute clock offset from the other close mics of this minute (their fitted lag minus the
                # talker->array distance from the poses) plus this talker's own distance; else session median
                clk = [q["fit"]["a"] - _dist(s, seg, q["pid"]) / E.C for (sg, q2), q in p1.items()
                       if sg == seg and q["fit"] and q["fit"]["n_fit"] >= 6 and np.isfinite(_dist(s, seg, q["pid"]))]
                dp = _dist(s, seg, pid)
                if clk and np.isfinite(dp):
                    a = float(np.median(clk) + dp / E.C); how = "minute_clock_plus_pose"
                else:
                    offs = [q["fit"]["a"] for q in p1.values() if q["pid"] == pid and q["fit"]]
                    a = float(np.median(offs)) if offs else 0.0; how = "no_fit_session_offset"
            c48, _ = sf.read(str(E.MAIN / "Close_Microphone_Audio" / f"Session_{s}" / f"{seg}_Participant_ID_{pid}.wav"), dtype="float32")
            c16 = warp_close(c48, a=a, b=b)
            write_f32(cd / f"{seg}_P{pid}.wav", c16)
            arr = E.load_array16(s, seg)
            rr = window_lags(arr[1], c16, active_mask(E.transcripts(s, seg), pid, arr.shape[1]))
            good = rr[rr[:, 2] >= 6.0] if len(rr) else rr
            res = good[:, 1] if len(good) else np.array([])
            inl = res[np.abs(res) <= 2e-3]
            rec = dict(sess=s, seg=seg, pid=pid, how=how, a_ms=1e3 * a, b_ppm=1e6 * b,
                       fs_close_eff=E.CLOSE_FS_NOMINAL / (1 - b), b_sess_ppm=1e6 * b_sess,
                       n_win=int(len(rr)), n_good=int(len(good)), n_inlier=int(len(inl)),
                       res_med_ms=float(1e3 * np.median(inl)) if len(inl) else None,
                       res_mad_ms=float(1e3 * np.median(np.abs(inl - np.median(inl)))) if len(inl) else None,
                       res_absmed_ms=float(1e3 * np.median(np.abs(inl))) if len(inl) else None,
                       res_p90_ms=float(1e3 * np.quantile(np.abs(inl), 0.9)) if len(inl) else None,
                       frac_outlier=float(1 - len(inl) / len(good)) if len(good) else None,
                       q_med=float(np.median(rr[:, 2])) if len(rr) else None)
            json.dump(rec, open(aj, "w"))
            rows_out.append(rec)
            log("align", s, seg, pid, how, "res_absmed_ms", rec["res_absmed_ms"])
    d = pd.DataFrame(rows_out)
    d.to_csv(R7 / "align.csv", index=False)
    summ = {}
    for s, g in d.groupby("sess"):
        summ[int(s)] = dict(n=len(g), b_ppm_median=float(g.b_ppm.median()), fs_close_eff_median=float(g.fs_close_eff.median()),
                            res_absmed_ms_median=float(g.res_absmed_ms.median()), res_p90_ms_median=float(g.res_p90_ms.median()),
                            how=g.how.value_counts().to_dict())
    allres = d.res_absmed_ms.dropna()
    summ["all"] = dict(n=len(d), res_absmed_ms_median=float(allres.median()), res_absmed_ms_p90=float(allres.quantile(0.9)),
                       res_p90_ms_median=float(d.res_p90_ms.median()), frac_outlier_median=float(d.frac_outlier.median()))
    summ["loo_pose_clock_check"] = align_loo(sessions)
    summ["note"] = ("res_* = lags re-measured on the aligned close mic in the same windows used for the fit (in-sample). "
                    "loo_pose_clock_check = out-of-sample: offset predicted from the other close mics of the minute + "
                    "pose distance. how=no_fit_* / minute_clock_plus_pose rows had < 4 usable windows (talker nearly silent).")
    json.dump(summ, open(R7 / "align_summary.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))


# ---------------------------------------------------------------------------------------------- DOA
def wearer_id(sess, seg, pose_ids):
    cl = set(E.close_ids(sess, seg))
    cand = [i for i in pose_ids if i not in cl]
    return cand


def stage_doa(sessions, inverse=False, tag=""):
    """per pose frame (50 ms): az/el/dist of every tracked participant in the wearer head frame."""
    rows = []
    for s in sessions:
        cd = E.CACHE / f"Session_{s}"
        for seg in E.segs(s):
            out = cd / f"{seg}.doa{tag}.npz"
            if out.exists():
                continue
            P, T = E.poses(s, seg)
            if P is None:
                log("no poses", s, seg); continue
            w = wearer_id(s, seg, list(P))
            if len(w) != 1:
                log("wearer ambiguous", s, seg, w, "close", E.close_ids(s, seg), "pose", list(P)); continue
            w = w[0]
            Pw, Qw, Uw, Vw = P[w]
            res = dict(wearer=w, T=T, ids=np.array([i for i in P if i != w]))
            for i in P:
                if i == w:
                    continue
                Pt, Qt, Ut, Vt = P[i]
                v = E.to_head(Pw, Qw, Pt, inverse=inverse)
                az, el = E.az_el(v)
                ok = Vw & Vt
                az[~ok] = np.nan; el[~ok] = np.nan
                res[f"az_{i}"] = az; res[f"el_{i}"] = el; res[f"dist_{i}"] = np.where(ok, np.linalg.norm(v, axis=1), np.nan)
            # wearer forward axis in the world (for sanity checks)
            Rw = E.quat_to_R(Qw)
            res["fwd_world"] = Rw[:, :, 2] if not inverse else np.transpose(Rw, (0, 2, 1))[:, :, 2]
            res["wearer_valid"] = Vw
            np.savez(out, **res)
            log("doa", s, seg, "wearer", w, "T", T)


def doa_load(s, seg, tag=""):
    p = E.CACHE / f"Session_{s}" / f"{seg}.doa{tag}.npz"
    if not p.exists():
        return None
    z = np.load(p)
    return {k: z[k] for k in z.files}


# ---------------------------------------------------------------------------------------------- validation
def single_talker_blocks(utts, pid_ok, seg_len, blk=0.5):
    """0.5 s blocks in which exactly one transcribed participant talks and it is in pid_ok (tracked, not wearer)."""
    n = int(seg_len / blk)
    who = [set() for _ in range(n)]
    for u in utts:
        for b in range(max(0, int(u["start"] / blk)), min(n, int(np.ceil(u["end"] / blk)))):
            # require full coverage of the block by that utterance for 'talking'
            if u["start"] <= b * blk and u["end"] >= (b + 1) * blk:
                who[b].add(u["pid"])
            else:
                who[b].add(("partial", u["pid"]))
    out = []
    for b, w in enumerate(who):
        if len(w) == 1:
            (p,) = tuple(w)
            if not isinstance(p, tuple) and p in pid_ok:
                out.append((b, p))
    return out


def stage_validate(sessions, tag="", chans=(0, 1, 2, 3), nmax_per_seg=None):
    from scipy.signal import stft
    az_g, el_g, H = E.load_atf(chans=chans)          # (D,), (D,), (D,F,M)
    f = np.fft.rfftfreq(512, 1 / FS); band = (f >= 300) & (f <= 6000)
    Hn = H[:, band, :] / (np.abs(H[:, band, :]) + 1e-12)
    rows = []
    for s in sessions:
        for seg in E.segs(s):
            d = doa_load(s, seg, tag)
            if d is None:
                continue
            x = E.load_array16(s, seg)[list(chans)]
            _, _, X = stft(x, FS, nperseg=512, noverlap=256, boundary=None, padded=False)   # (M,F,T)
            X = X[:, band, :]
            Xn = X / (np.abs(X) + 1e-12)
            tfr = np.arange(X.shape[2]) * 256 / FS + 256 / FS
            utts = E.transcripts(s, seg)
            ids = [int(i) for i in d["ids"]]
            blocks = single_talker_blocks(utts, set(ids), x.shape[1] / FS)
            for b, p in blocks:
                t0, t1 = b * 0.5, (b + 1) * 0.5
                fr = (tfr >= t0) & (tfr < t1)
                if fr.sum() < 5:
                    continue
                # SRP-PHAT: sum over frames and bins of |H^H Xn|^2 (PHAT-weighted, ATF steering, unit-modulus ATF)
                Y = np.einsum("dfm,mft->dft", Hn.conj(), Xn[:, :, fr])
                srp = (np.abs(Y) ** 2).sum((1, 2))
                k = int(np.argmax(srp))
                pf = (np.arange(len(d[f"az_{p}"])) + 0.5) / E.POSE_FPS
                pm = (pf >= t0) & (pf < t1)
                az_r, el_r = d[f"az_{p}"][pm], d[f"el_{p}"][pm]
                if np.isnan(az_r).any() or len(az_r) == 0:
                    continue
                # mean reference direction over the block
                u = E.unit(az_r, el_r).mean(0); az_m, el_m = E.az_el(u)
                rows.append(dict(sess=s, seg=seg, t0=t0, pid=p, az_ref=float(az_m), el_ref=float(el_m),
                                 az_srp=float(az_g[k]), el_srp=float(el_g[k]),
                                 err_az=float(abs(E.wrap(az_g[k] - az_m))),
                                 err_3d=float(E.ang3(az_g[k], el_g[k], az_m, el_m)),
                                 dist=float(np.nanmean(d[f"dist_{p}"][pm]))))
            log("validate", s, seg, len(rows))
    v = pd.DataFrame(rows)
    v.to_csv(R7 / f"doa_validation{tag}.csv", index=False)
    return v


def summarize_validation(v, label):
    out = dict(label=label, n_blocks=int(len(v)))
    if len(v):
        out.update(median_err_az=float(v.err_az.median()), median_err_3d=float(v.err_3d.median()),
                   frac_az_within_15=float((v.err_az <= 15).mean()), frac_az_within_30=float((v.err_az <= 30).mean()),
                   median_signed_az=float(np.median(E.wrap(v.az_srp - v.az_ref))),
                   n_minutes=int(v.groupby(["sess", "seg"]).ngroups))
    return out


# ---------------------------------------------------------------------------------------------- items
def turns(utts, merge_gap=1.0):
    """talker turns: consecutive utterances of the same participant merge if the gap is <= merge_gap s and no other
    participant STARTS an utterance in between. Returns, per utterance index, the onset time of its turn."""
    order = sorted(range(len(utts)), key=lambda i: utts[i]["start"])
    starts = sorted((u["start"], u["pid"]) for u in utts)
    onset = {}
    last = {}   # pid -> (turn onset, end of last utterance)
    for i in order:
        u = utts[i]; p = u["pid"]
        if p in last:
            on, end = last[p]
            other_started = any(end <= st <= u["start"] and q != p for st, q in starts)
            if u["start"] - end <= merge_gap and not other_started:
                onset[i] = on; last[p] = (on, max(end, u["end"])); continue
        onset[i] = u["start"]; last[p] = (u["start"], u["end"])
    return onset


def tag_target(target, wearer):
    """target: list of labels from Target_of_Speech (participant IDs as strings, 'Group', 'None').
    Precedence: addressed to the wearer (wearer ID in the list) > Group > other participant(s) > none."""
    t = [str(x) for x in (target or [])]
    if wearer is not None and str(int(wearer)) in t:
        return "wearer"
    if any(x.lower() == "group" for x in t):
        return "group"
    if any(x.isdigit() for x in t):
        return "other"
    return "none"


def stage_items(sessions, min_dur=1.0, ctx=2.0):
    meta_all = {"val": [], "test": []}
    for s in sessions:
        split = E.SPLIT[s]
        for seg in E.segs(s):
            utts = E.transcripts(s, seg)
            if not utts:
                continue
            d = doa_load(s, seg)
            wearer = int(d["wearer"]) if d is not None else None
            cl = set(E.close_ids(s, seg))
            on = turns(utts)
            arr = None
            al = {pid: json.load(open(E.CACHE / f"Session_{s}" / f"{seg}_P{pid}.align.json")) for pid in cl
                  if (E.CACHE / f"Session_{s}" / f"{seg}_P{pid}.align.json").exists()}
            for i, u in enumerate(utts):
                dur = u["end"] - u["start"]
                if u["pid"] not in cl or dur < min_dur:
                    continue
                iid = f"S{s}_{seg}_P{u['pid']}_{int(round(u['start'] * 1000)):05d}"
                od = MIX / "r7" / split / iid
                # overlap with any other participant's transcribed speech (incl. the wearer and the server)
                ov = 0.0
                for k, w in enumerate(utts):
                    if k != i and w["pid"] != u["pid"]:
                        ov += max(0.0, min(u["end"], w["end"]) - max(u["start"], w["start"]))
                ovl = min(1.0, ov / dur)
                c0 = max(0.0, u["start"] - ctx)
                n0, n1 = int(round(c0 * FS)), int(round(u["end"] * FS))
                rec = dict(id=iid, split=split, session=s, seg=seg, seg_start_s=E.seg_start_s(seg), talker=u["pid"],
                           wearer=wearer, target_raw=u["target"], target=tag_target(u["target"], wearer),
                           text=u["text"], start_s=round(u["start"], 3), end_s=round(u["end"], 3), dur=round(dur, 3),
                           ctx_s=round(u["start"] - c0, 3), utt_offset_samples=int(round(u["start"] * FS)) - n0,
                           n_samples=n1 - n0, overlap=bool(ovl > 0), ovl_frac=round(ovl, 3),
                           t_since_turn_onset=round(u["start"] - on[i], 3),
                           align_res_absmed_ms=al.get(u["pid"], {}).get("res_absmed_ms"),
                           align_how=al.get(u["pid"], {}).get("how"))
                if d is not None and f"az_{u['pid']}" in d:
                    pf = (np.arange(len(d[f"az_{u['pid']}"])) + 0.5) / E.POSE_FPS
                    m = (pf >= u["start"]) & (pf < u["end"])
                    az, el = d[f"az_{u['pid']}"][m], d[f"el_{u['pid']}"][m]
                    ok = ~np.isnan(az)
                    if ok.any():
                        uu = E.unit(az[ok], el[ok]).mean(0); a_m, e_m = E.az_el(uu)
                        rec.update(az_ref_mean=round(float(a_m), 2), el_ref_mean=round(float(e_m), 2),
                                   az_ref_range=round(float(np.ptp(np.unwrap(np.radians(az[ok])) * 180 / np.pi)), 2),
                                   doa_valid_frac=round(float(ok.mean()), 3))
                if not (od / "mix_mc.wav").exists() or not (od / "ref.wav").exists():
                    if arr is None:
                        arr = E.load_array16(s, seg)
                    x = arr[:, n0:n1]
                    c = E.load_close16(s, seg, u["pid"])[n0:n1]
                    write_f32(od / "mix_mc.wav", x)
                    write_f32(od / "ref.wav", c)
                    if d is not None and f"az_{u['pid']}" in d:
                        pf = (np.arange(len(d[f"az_{u['pid']}"])) + 0.5) / E.POSE_FPS
                        m = (pf >= c0) & (pf < u["end"])
                        np.savez(od / "doa_ref.npz", t=pf[m] - c0, az=d[f"az_{u['pid']}"][m], el=d[f"el_{u['pid']}"][m],
                                 dist=d[f"dist_{u['pid']}"][m])
                    json.dump(rec, open(od / "item.json", "w"), indent=1)
                meta_all[split].append(rec)
            log("items", s, seg, sum(len(v) for v in meta_all.values()))
    for split, m in meta_all.items():
        if not m:
            continue
        dfm = pd.DataFrame(m)
        counts = dict(n_items=len(m), by_session=dfm.session.value_counts().sort_index().to_dict(),
                      by_target=dfm.target.value_counts(dropna=False).to_dict(),
                      overlapped=int(dfm.overlap.sum()), total_utt_s=round(float(dfm.dur.sum()), 1),
                      median_dur=float(dfm.dur.median()), ctx_full=int((dfm.ctx_s >= 1.999).sum()),
                      turn_initial=int((dfm.t_since_turn_onset == 0).sum()))
        counts = json.loads(json.dumps(counts, default=lambda o: int(o) if isinstance(o, (np.integer,)) else str(o)))
        out = dict(note="EasyCom-derived, CC-BY-NC 4.0, research only, never redistribute. Times in s, 16 kHz. "
                        "mix_mc.wav: 6 ch (frame mics ch1-4 + left/right ear ch5-6), FLOAT; ref.wav: aligned close mic "
                        "(aligned to the direct-path arrival at array ch2); scoring covers samples "
                        "[utt_offset_samples, n_samples) only; the first utt_offset_samples are causal-warm-up context.",
                   counts=counts, items=m)
        (MIX / "r7" / split).mkdir(parents=True, exist_ok=True)
        json.dump(out, open(MIX / "r7" / split / "meta.json", "w"), indent=1, default=str)
        print(split, json.dumps(counts))


def n_words(text):
    import re
    t = re.sub(r"\[[A-Z]\]", " ", text or "")
    return len([w for w in re.findall(r"[A-Za-z0-9']+", t)])


def stage_qc(splits=("val", "test")):
    """per item: lag of array ch2 vs the aligned reference over the utterance only (GCC-PHAT, +-100 ms) and its
    PHAT peak ratio; word count of the transcript without the [L]/[C]/[T]/[U]/[H] codes. Rewrites meta.json."""
    for split in splits:
        mp = MIX / "r7" / split / "meta.json"
        M = json.load(open(mp)); qc_p = MIX / "r7" / split / "qc.json"
        qc = json.load(open(qc_p)) if qc_p.exists() else {}
        for i, r in enumerate(M["items"]):
            if r["id"] not in qc:
                d = MIX / "r7" / split / r["id"]
                x, _ = sf.read(str(d / "mix_mc.wav"), dtype="float32"); c, _ = sf.read(str(d / "ref.wav"), dtype="float32")
                o = r["utt_offset_samples"]
                lag, q = gcc_lag(x[o:, 1].astype(np.float64), c[o:].astype(np.float64), int(0.1 * FS))
                qc[r["id"]] = dict(item_lag_ms=round(1e3 * lag / FS, 3), item_lag_q=round(q, 2))
                if i % 100 == 0:
                    json.dump(qc, open(qc_p, "w")); log("qc", split, i)
            r.update(qc[r["id"]]); r["n_words"] = n_words(r["text"])
            r["align_suspect"] = bool(r["item_lag_q"] >= 6 and abs(r["item_lag_ms"]) > 2.0)
        json.dump(qc, open(qc_p, "w"))
        d = pd.DataFrame(M["items"]); good = d.item_lag_q >= 6
        M["counts"].update(n_with_words=int((d.n_words > 0).sum()), n_align_suspect=int(d.align_suspect.sum()),
                           item_lag_reliable=int(good.sum()),
                           item_lag_absmed_ms=round(float(d.item_lag_ms[good].abs().median()), 3),
                           item_lag_absp90_ms=round(float(d.item_lag_ms[good].abs().quantile(0.9)), 3),
                           by_target_with_words=d[d.n_words > 0].target.value_counts().to_dict())
        json.dump(M, open(mp, "w"), indent=1, default=str)
        print(split, json.dumps(M["counts"], default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--sess", default="4,12,10,11")
    ap.add_argument("--inverse", action="store_true")
    a = ap.parse_args()
    S = [int(x) for x in a.sess.split(",")]
    R7.mkdir(parents=True, exist_ok=True)
    if a.stage == "resample":
        stage_resample(S)
    elif a.stage == "align":
        stage_align(S)
    elif a.stage == "doa":
        stage_doa(S, inverse=a.inverse, tag="_inv" if a.inverse else "")
    elif a.stage == "validate":
        tag = "_inv" if a.inverse else ""
        v = stage_validate(S, tag=tag)
        print(json.dumps(summarize_validation(v, tag or "R^T"), indent=1))
    elif a.stage == "items":
        stage_items(S)
    elif a.stage == "qc":
        stage_qc()
    else:
        sys.exit("unknown stage")


if __name__ == "__main__":
    main()
