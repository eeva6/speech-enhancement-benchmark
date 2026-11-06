"""Round 7 step 4: head-orientation steering accuracy vs time since the talker's turn onset (EasyCom).

"Steer where the wearer faces": the steering direction is array forward (az = 0, el = 0 in the head frame). For every
50 ms pose frame inside a transcribed utterance of a tracked, non-wearer talker, the error is the angle between that
direction and the talker's reference DOA (from the poses; selab/prep_r7 doa). Time since onset = frame time minus
the onset of the talker's turn (selab.prep_r7.turns: same-talker utterances merge across gaps <= 1 s with no other
talker starting in between). One extra bin, "-0.5-0", looks at the 0.5 s BEFORE the turn onset (anticipation).

Step 4b (track mode): the round-6 causal tracker (selab/r6.Tracker, mode rtn = tracks + hysteresis, no enrolment)
run continuously over each minute on frame mics ch1-4 at 16 kHz with free-field 3-D steering at el = 0 ("ff") or
the measured ATF at Theta = 90 deg ("atf"); its steered azimuth (latest output available at the frame time) is
scored the same way (azimuth error only).

python -m selab.onset_r7 head                 -> results/r7/head_onset.csv, head_onset_frames.parquet
python -m selab.onset_r7 track --steer ff|atf --sess 4,12   (resumable per minute, outputs/r7/tracks/)
python -m selab.onset_r7 report               -> results/r7/onset_r7.csv (head + any tracker runs), figs/head_onset.png
"""
import argparse, json, time
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .common import FS, OUT, RES
from . import ec_r7 as E
from .prep_r7 import turns, tag_target, doa_load

R7 = RES / "r7"
BINS = [-0.5, 0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 1e9]
LAB = ["-0.5-0", "0-0.25", "0.25-0.5", "0.5-1", "1-2", "2-4", ">4"]
THR = (10, 15, 30, 45)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def frame_table(sessions):
    """one row per (utterance, 50 ms pose frame) for tracked non-wearer talkers, incl. 0.5 s before turn onsets."""
    rows = []
    for s in sessions:
        for seg in E.segs(s):
            d = doa_load(s, seg); utts = E.transcripts(s, seg)
            if d is None or not utts:
                continue
            w = int(d["wearer"]); on = turns(utts)
            T = len(d["fwd_world"]); tf = (np.arange(T) + 0.5) / E.POSE_FPS
            act = {}
            for u in utts:
                act.setdefault(u["pid"], np.zeros(T, bool))[(tf >= u["start"]) & (tf < u["end"])] = True
            first_of_turn = {}
            for i, u in enumerate(utts):
                if u["pid"] == w or f"az_{u['pid']}" not in d:
                    continue
                p = u["pid"]; az, el = d[f"az_{p}"], d[f"el_{p}"]
                turn_id = f"S{s}_{seg}_P{p}_{on[i]:.2f}"
                lo = u["start"]
                if on[i] == u["start"]:          # turn-initial utterance: also take 0.5 s before onset
                    lo = u["start"] - 0.5
                m = (tf >= lo) & (tf < u["end"])
                others = np.zeros(T, bool)
                for q, a in act.items():
                    if q != p:
                        others |= a
                tgt = tag_target(u["target"], w)
                for k in np.where(m)[0]:
                    if np.isnan(az[k]):
                        continue
                    rows.append((s, E.SPLIT[s], seg, p, turn_id, tgt, float(tf[k]), tf[k] - on[i], float(az[k]), float(el[k]),
                                 bool(others[k]), bool(tf[k] >= u["start"])))
    return pd.DataFrame(rows, columns=["sess", "split", "seg", "pid", "turn", "target", "t", "t_on", "az", "el", "overlap", "speaking"])


def score(df, err_col, label, rng, nboot=1000):
    """per turn: fraction of frames within each threshold per bin; mean over turns; cluster bootstrap over minutes."""
    df = df.copy(); df["bin"] = np.digitize(df.t_on, BINS) - 1
    df = df[(df.bin >= 0) & (df.bin < len(LAB))]
    for t in THR:
        df[f"w{t}"] = (df[err_col] <= t).astype(float)
    out = []
    groups = [("all", df), ("wearer", df[df.target == "wearer"]), ("group", df[df.target == "group"]),
              ("other", df[df.target.isin(["other", "none"])]),
              ("all_single", df[~df.overlap]), ("all_overlap", df[df.overlap])]
    for gname, g in groups:
        per = g.groupby(["turn", "bin"]).agg(**{f"w{t}": (f"w{t}", "mean") for t in THR}, n=("t_on", "size"),
                                             cl=("seg", "first"), sess=("sess", "first"), med=(err_col, "median")).reset_index()
        per["cl"] = per.sess.astype(str) + "_" + per.cl
        for b in range(len(LAB)):
            pb = per[per.bin == b]
            if len(pb) < 5:
                continue
            rec = dict(steer=label, group=gname, bin=LAB[b], bin_idx=b, n_turns=len(pb), n_frames=int(pb.n.sum()),
                       median_err=float(np.median(g[g.bin == b][err_col])))
            cls = pb.cl.unique(); idx = {c: np.where(pb.cl.values == c)[0] for c in cls}
            for t in THR:
                v = pb[f"w{t}"].values; rec[f"within{t}"] = float(v.mean())
                bs = []
                for _ in range(nboot):
                    pick = np.concatenate([idx[c] for c in rng.choice(cls, len(cls))])
                    bs.append(v[pick].mean())
                rec[f"within{t}_lo"], rec[f"within{t}_hi"] = (float(x) for x in np.quantile(bs, [0.025, 0.975]))
            out.append(rec)
    return pd.DataFrame(out)


def head(sessions):
    rng = np.random.default_rng(0)
    F = frame_table(sessions)
    F["err_az"] = np.abs(E.wrap(F.az)); F["err_3d"] = E.ang3(0.0, 0.0, F.az.values, F.el.values)
    F.to_csv(R7 / "head_onset_frames.csv.gz", index=False)
    O = pd.concat([score(F, "err_az", "head_az", rng), score(F, "err_3d", "head_3d", rng)])
    O.to_csv(R7 / "head_onset.csv", index=False)
    # split-wise (val vs test) for the azimuth metric, all-target group
    S = []
    for sp in ("val", "test"):
        o = score(F[F.split == sp], "err_az", f"head_az_{sp}", rng, nboot=300); S.append(o[o.group.isin(["all", "wearer", "group"])])
    pd.concat(S).to_csv(R7 / "head_onset_by_split.csv", index=False)
    print(O[(O.steer == "head_az") & O.group.isin(["all", "wearer", "group", "other"])][
        ["group", "bin", "n_turns", "median_err", "within10", "within15", "within30", "within45"]].round(3).to_string())
    return O


# ---------------------------------------------------------------------------------------------- tracker
def make_tracker(steer):
    from . import r6
    xy = E.MIC_POS[:, [0, 2]]           # placeholder 2-D geometry (x left, z fwd); D is replaced below
    tr = r6.Tracker(xy, mode="rtn")
    f = np.fft.rfftfreq(r6.TN, 1 / FS)
    az = np.arange(360.0)
    u = E.unit(az, np.zeros_like(az))                       # (A,3)
    tau = -(u @ E.MIC_POS.T) / E.C                          # (A,M)
    Dff = np.exp(-2j * np.pi * f[None, :, None] * tau[:, None, :])     # (A,F,M)
    if steer == "atf":
        azg, elg, H = E.load_atf(nfft=r6.TN)                # (D,), (D,), (D,F,M)
        row = np.where(np.abs(elg) < 1e-6)[0]
        row = row[np.argsort(azg[row] % 360)]
        a6 = azg[row] % 360
        tau6 = -(E.unit(a6, 0 * a6) @ E.MIC_POS.T) / E.C
        R6 = H[row] / np.exp(-2j * np.pi * f[None, :, None] * tau6[:, None, :])   # residual after free-field phase
        R6 = R6 / (R6[:, :, [1]] / np.abs(R6[:, :, [1]]) + 1e-12)          # reference phase to ch2
        a6c = np.concatenate([a6, [a6[0] + 360]]); R6c = np.concatenate([R6, R6[:1]])
        Ri = np.empty((360,) + R6.shape[1:], complex)
        for i, a in enumerate(az):
            j = np.searchsorted(a6c, a, side="right") - 1; j = min(j, len(a6c) - 2)
            wgt = (a - a6c[j]) / (a6c[j + 1] - a6c[j])
            Ri[i] = (1 - wgt) * R6c[j] + wgt * R6c[j + 1]
        D = Dff * Ri / (np.abs(Ri) + 1e-12)                 # unit-modulus ATF steering (PHAT)
    else:
        D = Dff
    tr.D = D[:, tr.k, :]
    return tr


def track(steer, sessions):
    from . import r6
    od = OUT / "r7" / "tracks" / f"rtn_{steer}"; od.mkdir(parents=True, exist_ok=True)
    for s in sessions:
        for seg in E.segs(s):
            p = od / f"S{s}_{seg}.npz"
            if p.exists():
                continue
            x = E.load_array16(s, seg)[:4].astype(np.float64)
            tr = make_tracker(steer)
            n = x.shape[1]; az, av = [], []
            t0 = time.perf_counter()
            for j in range(0, (n - r6.TN) // r6.TH + 1):
                a, _ = tr.step(x[:, j * r6.TH: j * r6.TH + r6.TN]); az.append(a); av.append(j * r6.TH + r6.TN)
            np.savez(p, az=np.array(az), avail=np.array(av), sec=time.perf_counter() - t0)
            log("track", steer, s, seg, f"{time.perf_counter() - t0:.1f}s")


def track_frames(steer, F):
    """attach the tracker's steered az (latest available output at each pose-frame time) to the frame table."""
    od = OUT / "r7" / "tracks" / f"rtn_{steer}"
    parts = []
    for (s, seg), g in F.groupby(["sess", "seg"]):
        p = od / f"S{s}_{seg}.npz"
        if not p.exists():
            continue
        z = np.load(p)
        t = g.t.values
        j = np.searchsorted(z["avail"] / FS, t, side="right") - 1
        ok = j >= 0
        a = np.where(ok, z["az"][np.clip(j, 0, None)], np.nan)
        a = np.where(a > 180, a - 360, a)
        gg = g.copy(); gg["trk_az"] = a; gg["err_trk"] = np.abs(E.wrap(gg.trk_az - gg.az))
        parts.append(gg[ok])
    return pd.concat(parts) if parts else None


def report():
    rng = np.random.default_rng(1)
    O = pd.read_csv(R7 / "head_onset.csv")
    F = pd.read_csv(R7 / "head_onset_frames.csv.gz")
    allo = [O]
    for steer in ("ff", "atf"):
        T = track_frames(steer, F)
        if T is None or not len(T):
            continue
        allo.append(score(T, "err_trk", f"tracker_rtn_{steer}", rng))
        Tv = T[T.split == "val"]
        allo.append(score(Tv, "err_trk", f"tracker_rtn_{steer}_val", rng))
        allo.append(score(Tv, "err_az", f"head_az_val", rng)) if steer == "atf" else None
        # frames where the steering error is within 15 deg for EITHER head or tracker (complementarity)
        if steer == "atf":
            T2 = T.copy(); T2["err_min"] = np.minimum(T2.err_az, T2.err_trk)
            allo.append(score(T2, "err_min", "best_of_head_or_tracker_atf", rng))
    A = pd.concat(allo); A.to_csv(R7 / "onset_r7.csv", index=False)
    (R7 / "figs").mkdir(exist_ok=True)
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
    r6o = pd.read_csv(RES / "r6" / "tracker_onset.csv")
    for ax, thr in zip(axs, (15, 30, 45)):
        for (steer, grp), c, lab in ((("head_az", "all"), "#222", "head (all)"), (("head_az", "wearer"), "#c44", "head (to wearer)"),
                                     (("head_az", "group"), "#269", "head (to group)"), (("head_az", "other"), "#999", "head (other)"),
                                     (("tracker_rtn_atf", "all"), "#e90", "R6 tracker (rtn), ATF steering"),
                                     (("tracker_rtn_ff", "all"), "#7a3", "R6 tracker (rtn), free-field steering")):
            s = A[(A.steer == steer) & (A.group == grp)].sort_values("bin_idx")
            if not len(s):
                continue
            ax.errorbar(s.bin_idx, s[f"within{thr}"], yerr=[s[f"within{thr}"] - s[f"within{thr}_lo"], s[f"within{thr}_hi"] - s[f"within{thr}"]],
                        fmt="o-", color=c, capsize=2, ms=3, label=lab)
        ax.set_xticks(range(len(LAB))); ax.set_xticklabels(LAB, rotation=45, fontsize=7)
        ax.set_xlabel("time since talker turn onset (s)", fontsize=8); ax.set_title(f"within ±{thr}°", fontsize=9)
        ax.set_ylim(0, 1); ax.grid(alpha=0.3)
    axs[0].set_ylabel("fraction of 50 ms frames", fontsize=8)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=6, fontsize=7, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("EasyCom, sessions 4/10/11/12: steering error vs time since talker turn onset (95% cluster-bootstrap CI over minutes)", fontsize=9)
    fig.tight_layout(); fig.savefig(R7 / "figs" / "head_onset.png", dpi=150, bbox_inches="tight"); plt.close(fig)
    return A


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what")
    ap.add_argument("--sess", default="4,12,10,11")
    ap.add_argument("--steer", default="atf")
    a = ap.parse_args()
    S = [int(x) for x in a.sess.split(",")]
    if a.what == "head":
        head(S)
    elif a.what == "track":
        track(a.steer, S)
    elif a.what == "report":
        report()


if __name__ == "__main__":
    main()
