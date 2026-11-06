"""Export the investor A/B listening set: loudness-matched wavs + metrics.json + self-contained player.

python -m selab.venture_ab.export      -> venture/06_DEMO/ab_set/ and venture/06_DEMO/ab_set_shareable.zip
Only LibriCSS (CC BY 4.0) audio is written.  No EasyCom audio is touched here.
"""
import json, os, shutil, zipfile
from pathlib import Path
import numpy as np, pandas as pd
import soundfile as sf
from .build import OUTW, MODES, meta_all
from .score import load
from ..common import FS

V = Path("/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture")
DEMO = V / "06_DEMO" / "ab_set"
TARGET_DB = -23.0
TRACKS = MODES + ["target_ref"]
GTRACKS = ["raw", "sector_sd8", "sector_ds32", "oracle_mwf", "anc_sim", "target_ref"]

MODE_INFO = {
    "raw": dict(label="Unprocessed (centre mic)", cat="A", short="BEFORE",
                desc="The real recording from the centre microphone of the 7-mic table array. This is the 'before'."),
    "causal_trk_sd8": dict(label="Causal 8 ms, self-steering (deployable)", cat="A", short="CAUSAL 8 ms",
                           desc="Superdirective beamformer, 8 ms total algorithmic delay, steered by a causal tracker that only hears the past. Nothing oracle. This is what a real-time device could do today."),
    "causal_ref_sd8": dict(label="Causal 8 ms, ORACLE direction", cat="A", short="CAUSAL 8 ms + ORACLE DIR",
                           desc="The same causal 8 ms filter, but pointed at the talker using the known loudspeaker direction (ORACLE). Stands in for 'the listener faces the talker'. Not a measured head-steering result."),
    "r5_ds32": dict(label="Non-causal best: delay-and-sum 32 ms, blind direction", cat="A", short="NON-CAUSAL DS 32 ms",
                    desc="Round-5 best real-data method: delay-and-sum with a 32 ms frame and a direction estimated blind from the whole utterance (looks ahead, so not real-time as built)."),
    "oracle_mvdr": dict(label="ORACLE upper bound: MVDR with true noise statistics", cat="A", short="ORACLE MVDR",
                        desc="Offline MVDR built from the TRUE competing-talker and noise signals (only available in the lab). An upper bound on what this 7-mic array could capture; not deployable."),
    "anc_sim": dict(label="SIMULATED ANC at the ear", cat="C", short="SIMULATED ANC",
                    desc="SIMULATED. Applies the lab's simulated open-ear ANC curves (target talker: companion curve; competing talker and noise: babble curve) to the centre-mic signal. Not measured on any head or device. Keeps its level drop."),
    "sector_sd8": dict(label="Causal 8 ms, pointed at the chosen sector", cat="A", short="CAUSAL 8 ms SECTOR",
                       desc="Superdirective beamformer, 8 ms algorithmic delay, pointed at the centre of the chosen group's sector. The sector direction comes from the known loudspeaker layout (stands in for the user pointing at that group); no tracking, no oracle signals."),
    "sector_ds32": dict(label="Delay-and-sum 32 ms, pointed at the chosen sector", cat="A", short="DS 32 ms SECTOR",
                        desc="Round-5 style delay-and-sum (32 ms frames) with the same fixed sector direction."),
    "oracle_mwf": dict(label="ORACLE upper bound: multichannel Wiener filter for the group", cat="A", short="ORACLE MWF",
                       desc="Offline multichannel Wiener filter built from the TRUE group and other-talker signals (lab only). Upper bound for this array; not deployable."),
    "target_ref": dict(label="Reference: estimated target talker(s) alone", cat="ref", short="TARGET ONLY",
                       desc="The scoring reference: the target loudspeaker's dry feed convolved with the system-identified room response at the centre mic. Shows what 'perfect separation' would sound like (it still contains the room's reverberation)."),
}


def gated_rms_db(y, blk=0.4):
    n = int(blk * FS); h = n // 4
    e = np.array([np.mean(y[i:i + n] ** 2) for i in range(0, len(y) - n + 1, h)]) + 1e-12
    e = e[10 * np.log10(e) > -70]
    if len(e) == 0:
        return -70.0
    e = e[10 * np.log10(e) > 10 * np.log10(e.mean()) - 10]
    return float(10 * np.log10(e.mean()))


def r(x, k=2):
    return None if x is None or not np.isfinite(x) else round(float(x), k)


def caption(m, row):
    """plain-English caption from measured numbers only."""
    def g(mode, c):
        q = row.get(mode, {}); return q.get(c)
    c = row
    ov = c["raw"]["ov_s"]
    parts = [f"A LibriSpeech talker read aloud over a loudspeaker in a real meeting room ({m['cond']}: the session is {m['cond'][2:]}% overlapped speech). "
             f"Another talker overlaps this sentence for {ov:.1f} s; the rest is the room's own noise."]
    d = g("causal_trk_sd8", "d_snr"); s = g("causal_trk_sd8", "d_sir_ov")
    if d is not None:
        parts.append(f"The deployable causal 8 ms mode changed the target-to-everything-else ratio by {d:+.1f} dB"
                     + (f" and target-vs-competing-talker by {s:+.1f} dB." if s is not None else "."))
    d2 = g("oracle_mvdr", "d_snr")
    if d2 is not None:
        parts.append(f"The ORACLE upper bound reached {d2:+.1f} dB.")
    w0 = c["raw"].get("word_correct"); w1 = g("causal_trk_sd8", "word_correct")
    if w0 is not None and w1 is not None:
        parts.append(f"Whisper got {100 * w0:.0f}% of the target's words before and {100 * w1:.0f}% after (causal mode).")
    return " ".join(parts)


def group_table():
    from .score import cboot
    p = OUTW / "group_metrics_raw.csv"
    if not p.exists():
        return None, None
    o = pd.read_csv(p)
    base = o[o["mode"] == "raw"].set_index("id")
    for c in ["snr", "sir_ov", "snr_noise", "si_sdr", "stoi", "estoi", "word_correct"]:
        o["d_" + c] = o[c].values - base.loc[o["id"], c].values
    o.to_csv(OUTW / "group_metrics_items.csv", index=False)
    S = {}
    for mode in ["raw", "sector_sd8", "sector_ds32", "oracle_mwf", "anc_sim"]:
        q = o[o["mode"] == mode]; S[mode] = {"n": int(len(q)), "n_rec": int(q["rec"].nunique())}
        if mode == "raw":
            continue
        for c in ["snr", "sir_ov", "snr_noise", "si_sdr", "stoi", "estoi", "word_correct"]:
            v = q["d_" + c].values
            if len(v) == 0 or np.all(~np.isfinite(v)):
                continue
            mn, lo, hi = cboot(v, q["rec"].values)
            S[mode]["d_" + c] = dict(median=float(np.nanmedian(v)), min=float(np.nanmin(v)), max=float(np.nanmax(v)), mean=mn, ci95=[lo, hi])
    json.dump(S, open(OUTW / "group_summary.json", "w"), indent=1)
    return o, S


def add_groups(out, cols):
    o, S = group_table()
    if o is None:
        return
    out["summary"]["groups"] = S
    sel = {g["gid"]: g for g in json.load(open(OUTW / "group_selection.json"))["selected"]}
    k0 = len(out["clips"])
    for k, (gid, g) in enumerate(sel.items()):
        od = OUTW / "groups" / gid
        if not (od / "done.json").exists():
            continue
        ld = lambda mo: {kk: v.astype(np.float64) for kk, v in np.load(od / f"{mo}.npz").items()}
        raw = ld("raw"); g_raw = 10 ** ((TARGET_DB - gated_rms_db(raw["mix"])) / 20)
        for t in GTRACKS:
            x = raw["T"] if t == "target_ref" else (raw["mix"] if t == "raw" else ld(t)["mix"])
            gg = g_raw if t in ("raw", "anc_sim") else 10 ** ((TARGET_DB - gated_rms_db(x)) / 20)
            sf.write(DEMO / "audio" / f"{gid}__{t}.wav", np.clip(x * gg, -0.99, 0.99).astype(np.float32), FS, subtype="PCM_16")
        rowd = {}
        for t in GTRACKS:
            q = o[(o["id"] == gid) & (o["mode"] == t)]
            if not len(q):
                continue
            q = q.iloc[0]
            d = {c: r(q[c], 3) for c in cols if c in q and not isinstance(q[c], str)}
            for c in ["snr", "sir_ov", "snr_noise", "si_sdr", "stoi", "estoi", "word_correct"]:
                if "d_" + c in q:
                    d["d_" + c] = r(q["d_" + c], 3)
            d["ov_s"] = r(q.get("ov_s"), 2); d["hyp"] = q.get("hyp") if isinstance(q.get("hyp"), str) else ""
            rowd[t] = d
        rw, sd, om = rowd.get("raw", {}), rowd.get("sector_sd8", {}), rowd.get("oracle_mwf", {})
        cap = (f"'Hear the group on one side of the table over the others' (sector clip, closest honest proxy: LibriCSS has no two "
               f"concurrent conversations). Target group = loudspeakers within ±50° of {g['sector_centre']:.0f}° "
               f"({len(g['group_utts'])} utterances by group talkers in this window); "
               f"other talker(s) overlap the group for {rw.get('ov_s', 0) or 0:.1f} s. ")
        if sd.get("d_sir_ov") is not None:
            cap += f"The causal 8 ms beam pointed at the sector changed group-vs-other-talkers by {sd['d_sir_ov']:+.1f} dB"
            cap += f" (ORACLE upper bound {om['d_sir_ov']:+.1f} dB). " if om.get("d_sir_ov") is not None else ". "
        if rw.get("word_correct") is not None and sd.get("word_correct") is not None:
            cap += f"Whisper got {100 * rw['word_correct']:.0f}% of the group's words before and {100 * sd['word_correct']:.0f}% after."
        out["clips"].append(dict(id=gid, n=k0 + k + 1, kind="group", tracks=GTRACKS, default_b="sector_sd8", cond=g["cond"],
                                 session=g["session"], group_size=len(g["group_ch"]), group_ch=g["group_ch"],
                                 sector_centre=round(g["sector_centre"], 1), other_ch=g["other_ch"],
                                 dur=round(g["we"] - g["ws"], 1), text=g["text"], best_case=False, caption=cap, metrics=rowd,
                                 files={t: f"audio/{gid}__{t}.wav" for t in GTRACKS}))


def main():
    DEMO.mkdir(parents=True, exist_ok=True)
    (DEMO / "audio").mkdir(exist_ok=True)
    M = meta_all()
    sel = json.load(open(OUTW / "selection.json"))
    o = pd.read_csv(OUTW / "metrics_items.csv")
    S = json.load(open(OUTW / "summary.json"))
    clips = list(sel["selected"])
    best = None
    pool = o[(o["mode"] == "causal_trk_sd8")].sort_values("d_snr", ascending=False)
    if len(pool):
        b = pool.iloc[0]["id"]
        if b not in clips:
            best = b; clips.append(b)
    out = dict(title="Conversation Bubble: real 7-mic before/after set", modes=[dict(id=k, **v) for k, v in MODE_INFO.items()],
               summary=S, clips=[], best_case_id=best,
               attribution="Audio derived from LibriCSS (Chen et al., ICASSP 2020, 'Continuous speech separation: dataset and analysis'), "
                           "which replays LibriSpeech test-clean (Panayotov et al., 2015) in a real room. Both CC BY 4.0. "
                           "Processed (cut, beamformed, filtered, level-matched) by the Conversation Bubble lab; changes are ours.")
    cols = ["snr", "sir_ov", "snr_noise", "si_sdr", "stoi", "estoi", "word_correct", "ins_rate", "dba_change"]
    for k, iid in enumerate(clips):
        m = M[iid]
        raw = load(iid, "raw")
        g_raw = 10 ** ((TARGET_DB - gated_rms_db(raw["mix"])) / 20)
        rowd = {}
        for t in TRACKS:
            if t == "target_ref":
                x = raw["T"]; g = 10 ** ((TARGET_DB - gated_rms_db(x)) / 20)
            elif t == "raw":
                x = raw["mix"]; g = g_raw
            elif t == "anc_sim":
                x = load(iid, t)["mix"]; g = g_raw          # keep the SIMULATED level drop
            else:
                x = load(iid, t)["mix"]; g = 10 ** ((TARGET_DB - gated_rms_db(x)) / 20)
            y = np.clip(x * g, -0.99, 0.99)
            sf.write(DEMO / "audio" / f"{iid}__{t}.wav", y.astype(np.float32), FS, subtype="PCM_16")
        for mode in MODES + ["target_ref"]:
            q = o[(o["id"] == iid) & (o["mode"] == mode)]
            if mode == "target_ref":
                a = pd.read_csv(OUTW / "asr.csv"); a = a[(a.id == iid) & (a["mode"] == "target_ref")]
                rowd[mode] = dict(word_correct=r(a["word_correct"].iloc[0], 3)) if len(a) else {}
                continue
            q = q.iloc[0]
            d = {c: r(q[c], 3) for c in cols if c in q}
            for c in ["snr", "sir_ov", "snr_noise", "si_sdr", "stoi", "estoi", "word_correct"]:
                if "d_" + c in q:
                    d["d_" + c] = r(q["d_" + c], 3)
            d["ov_s"] = r(q["ov_s"], 2)
            d["hyp"] = q.get("hyp") if isinstance(q.get("hyp"), str) else ""
            rowd[mode] = d
        out["clips"].append(dict(id=iid, n=k + 1, kind="single", tracks=TRACKS, default_b="causal_trk_sd8",
                                 cond=m["cond"], session=m["session"], speaker=m["spk"],
                                 dur=round(m["dur"], 1), text=m["text"], best_case=(iid == best),
                                 caption=caption(m, rowd), metrics=rowd,
                                 files={t: f"audio/{iid}__{t}.wav" for t in TRACKS}))
    add_groups(out, cols)
    json.dump(out, open(DEMO / "metrics.json", "w"), indent=1)
    shutil.copy(Path(__file__).with_name("index.html"), DEMO / "index.html")
    (DEMO / "START_DEMO.command").write_text('#!/bin/bash\n# Double-click on a Mac (or run in Terminal). Serves the demo locally and opens it.\n'
                                            'cd "$(dirname "$0")"\n( sleep 1; open "http://localhost:8766/" 2>/dev/null || xdg-open "http://localhost:8766/" ) &\n'
                                            'python3 -m http.server 8766\n')
    os.chmod(DEMO / "START_DEMO.command", 0o755)
    (DEMO / "ATTRIBUTION.txt").write_text(out["attribution"] + "\n\nLibriCSS: https://github.com/chenzhuo1011/libri_css (CC BY 4.0)\n"
                                         "LibriSpeech: https://www.openslr.org/12 (CC BY 4.0)\n"
                                         "License of the derived audio in this folder: CC BY 4.0 (same terms; attribute as above).\n"
                                         "No EasyCom (CC BY-NC) audio is included in this set.\n")
    shutil.copy(Path(__file__).with_name("README_AB.md"), DEMO / "README.md")
    z = V / "06_DEMO" / "ab_set_shareable.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as Z:
        for p in sorted(DEMO.rglob("*")):
            if p.is_file():
                assert "easycom" not in p.name.lower()
                Z.write(p, "ConversationBubble_AB_set/" + str(p.relative_to(DEMO)))
    print("clips", len(clips), "best", best, "zip", z, os.path.getsize(z) // 1024, "KB")


if __name__ == "__main__":
    main()
