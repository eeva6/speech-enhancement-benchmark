"""Blinded speech-intelligibility listening test (keyword / word-correct scoring) - Gradio app.

    python listening_test.py                 # run the test locally: http://127.0.0.1:7861
    python listening_test.py --build         # (re)build the trial plan from benchmark outputs
    python listening_test.py --analyze       # summarise responses.csv (per method, paired bootstrap CIs)
    python listening_test.py --selftest      # pipeline check with a SYNTHETIC listener (Whisper); not human data
    python listening_test.py --set r5        # ROUND-5 set: REAL LibriCSS meeting-room recordings (see below)
    ./run_listening_test.sh [r5|r3] [--share]   # one-command launch for friends (see LISTENING_TEST.md)

Round-5 set (--set r5): real 7-mic recordings with a second talker overlapping. Each trial first plays a short
"voice to follow" cue (another sentence by the same talker, from the same unprocessed recording), then the
sentence. 5 processing conditions (unprocessed mic, DeepFilterNet3, online MVDR with estimated direction,
target-speaker extraction, online MVDR -> TSE) x 3 overlap levels (OV10/OV20/OV40) x 5 sentences = 15 trials
(+3 practice-free 0S cells are not used). Files: results/listening_test_r5/.

Design
  * Stimuli: round-3 out-of-domain mixtures (CMU ARCTIC talkers, recorded MS-SNSD noise) at 0 and -5 dB,
    conditions rec_babble / rec_hvac / rec_transient / ood_competing; 6 processing conditions.
  * Each listener hears every SENTENCE exactly once (no repeat -> no learning of the sentence), and every
    METHOD equally often: method assignment is a cyclic Latin square over the 6 sentences of each cell,
    rotated by participant number. Trial order is shuffled per participant. Method names are never shown.
  * One play allowed by default (set MAX_PLAYS); listener types every word they heard, then rates effort 1-5.
  * Score = word-correct rate (hits / reference words, after lower-casing and stripping punctuation),
    the same scoring the ASR proxy used, so human and ASR results are directly comparable.
  * Responses append to results/listening_test/responses.csv (participant id is a random code; nothing
    identifying is stored). Calibrate playback to a comfortable fixed level before starting.
"""
import argparse, csv, json, random, re, shutil, time, uuid, os
from pathlib import Path
import numpy as np

for _k in ("NO_PROXY", "no_proxy"):
    os.environ[_k] = ",".join(filter(None, [os.environ.get(_k, ""), "localhost,127.0.0.1"]))

ROOT = Path(__file__).resolve().parent
TAG = "r3"
COND = ["rec_babble", "rec_hvac", "rec_transient", "ood_competing"]
SNRS = [0, -5]
METHODS = ["noisy", "wiener_dd", "rnnoise", "deepfilternet3", "demucs_dns64", "tse_convtasnet_ecapa"]
N_SENT = len(METHODS)  # sentences per cell = number of methods (Latin square)
LT = ROOT / "results" / "listening_test"
STIM = LT / "stimuli"
PLAN = LT / "plan.json"
RESP = LT / "responses.csv"
MAX_PLAYS = 1
CUE = False


def use_set(name):
    """Switch the module to another stimulus set (r3 = default round-3 set, r5 = real LibriCSS recordings)."""
    global TAG, COND, SNRS, METHODS, N_SENT, LT, STIM, PLAN, RESP, CUE
    if name == "r5":
        TAG, COND, SNRS, CUE = "r5", ["OV10", "OV20", "OV40"], [0], True
        METHODS = ["noisy", "deepfilternet3", "mvdr_online_est", "tse", "mvdr_online_est_tse"]
        N_SENT = len(METHODS)
        LT = ROOT / "results" / "listening_test_r5"
        STIM, PLAN, RESP = LT / "stimuli", LT / "plan.json", LT / "responses.csv"


def _sentences(meta, c, s):
    if TAG != "r5":
        return [f"{c}_snr{s:+d}_{j:02d}" for j in range(N_SENT)]
    ids = sorted(m["id"] for m in meta.values() if m["cond"] == c and 3.0 <= m["dur"] <= 9.0
                 and all((ROOT / "outputs" / TAG / me / f"{m['id']}.wav").exists() for me in METHODS if me != "noisy"))
    rng = random.Random(5)
    rng.shuffle(ids)
    return ids[:N_SENT]


def words(s):
    return re.sub(r"[^a-z' ]", " ", str(s).lower()).split()


def wcr(ref, hyp):
    import jiwer
    r, h = " ".join(words(ref)), " ".join(words(hyp)) or "x"
    o = jiwer.process_words(r, h)
    return o.hits / (o.hits + o.substitutions + o.deletions)


def build():
    """Copy stimuli under opaque names (so file names do not reveal the method) and write the plan."""
    import soundfile as sf
    meta = {m["id"]: m for m in json.load(open(ROOT / "mixtures" / TAG / "meta.json"))}
    if STIM.exists():
        shutil.rmtree(STIM)
    STIM.mkdir(parents=True)
    cells, key = [], {}
    rng = random.Random(0)
    for c in COND:
        for s in SNRS:
            sents = _sentences(meta, c, s)
            cell = []
            for mid in sents:
                stim = {}
                for m in METHODS:
                    src = (ROOT / "mixtures" / TAG / mid / "mix.wav") if m == "noisy" else (ROOT / "outputs" / TAG / m / f"{mid}.wav")
                    if not src.exists():
                        raise FileNotFoundError(src)
                    x, fs = sf.read(src, dtype="float32")
                    x = 0.1 * x / (np.sqrt(np.mean(x ** 2)) + 1e-9)  # RMS-normalise: equal loudness across methods
                    x = np.clip(x, -1, 1)
                    code = uuid.UUID(int=rng.getrandbits(128)).hex[:10]
                    sf.write(STIM / f"{code}.wav", x, fs, subtype="PCM_16")
                    stim[m] = code; key[code] = dict(id=mid, method=m)
                cue = None
                if CUE:   # voice-to-follow cue: enrolment clip of the same talker (unprocessed), first 4 s
                    x, fs = sf.read(ROOT / "mixtures" / TAG / mid / "enrol.wav", dtype="float32")
                    x = np.clip(0.1 * x[: 4 * fs] / (np.sqrt(np.mean(x[: 4 * fs] ** 2)) + 1e-9), -1, 1)
                    cue = "cue_" + uuid.UUID(int=rng.getrandbits(128)).hex[:10]
                    sf.write(STIM / f"{cue}.wav", x, fs, subtype="PCM_16")
                cell.append(dict(id=mid, text=meta[mid]["text"], stim=stim, cue=cue))
            cells.append(dict(cond=c, snr=s, sentences=cell))
    json.dump(dict(cells=cells, methods=METHODS), open(PLAN, "w"), indent=1)
    json.dump(key, open(LT / "stimulus_key.json", "w"), indent=1)
    print(f"plan: {len(cells)} cells x {N_SENT} sentences = {len(cells) * N_SENT} trials per listener")


def trials_for(pnum):
    plan = json.load(open(PLAN))
    out = []
    for cell in plan["cells"]:
        for j, sent in enumerate(cell["sentences"]):
            m = plan["methods"][(j + pnum) % len(plan["methods"])]  # cyclic Latin square
            out.append(dict(id=sent["id"], text=sent["text"], method=m, code=sent["stim"][m],
                            cond=cell["cond"], snr=cell["snr"], cue=sent.get("cue")))
    random.Random(pnum).shuffle(out)
    return out


def record(row):
    LT.mkdir(parents=True, exist_ok=True)
    new = not RESP.exists()
    with open(RESP, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


def analyze(path=RESP):
    import pandas as pd
    d = pd.read_csv(path)
    real = d[d.listener_type == "human"]
    for label, g in [("HUMAN", real), ("SYNTHETIC (pipeline test only)", d[d.listener_type != "human"])]:
        if g.empty:
            print(f"{label}: no responses"); continue
        print(f"\n{label}: {g.participant.nunique()} listeners, {len(g)} trials")
        base = g[g.method == "noisy"].groupby(["cond", "snr"]).wcr.mean()
        rows = []
        for m, gm in g.groupby("method"):
            b = np.random.default_rng(0).choice(gm.wcr.values, (2000, len(gm))).mean(1)
            rows.append(dict(method=m, n=len(gm), wcr=gm.wcr.mean(), ci=f"[{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]",
                             effort=gm.effort.mean()))
        print(pd.DataFrame(rows).sort_values("wcr", ascending=False).round(3).to_string(index=False))
        print(g.pivot_table(index="method", columns="cond", values="wcr").round(2).to_string())


def selftest(n_participants=2):
    """Exercise the full pipeline with Whisper as a stand-in listener. Rows are tagged listener_type=synthetic."""
    import sys
    sys.path.insert(0, str(ROOT))
    from selab.evaluate import transcribe
    from selab.common import load
    for p in range(n_participants):
        pid = f"SYNTH{p:02d}"
        for k, t in enumerate(trials_for(p)):
            hyp = transcribe(load(STIM / f"{t['code']}.wav"))
            record(dict(participant=pid, listener_type="synthetic", pnum=p, trial=k, id=t["id"], cond=t["cond"],
                        snr=t["snr"], method=t["method"], response=hyp, wcr=round(wcr(t["text"], hyp), 4),
                        effort=np.nan, plays=1, rt_s=np.nan, ts=time.strftime("%Y-%m-%dT%H:%M:%S")))
    analyze()


def app():
    import gradio as gr
    css = ".gr-button{font-size:18px}"
    with gr.Blocks(title="Listening test", css=css) as demo:
        st = gr.State(dict())
        gr.Markdown("## Speech listening test\nYou will hear short sentences in noise. Each sentence is played once. "
                    "Type **every word you heard**, guessing is fine, then rate how hard it was to listen. "
                    "Set your volume to a comfortable level using the practice clip before you start.")
        with gr.Row():
            pnum = gr.Number(label="Participant number (given to you by the experimenter)", precision=0, value=0)
            start = gr.Button("Start", variant="primary")
        progress = gr.Markdown()
        cue = gr.Audio(label="Voice to follow (listen first)", interactive=False, visible=CUE)
        audio = gr.Audio(label="Sentence", interactive=False, autoplay=not CUE)
        resp = gr.Textbox(label="Words you heard")
        effort = gr.Radio(["1 very easy", "2", "3", "4", "5 very hard"], label="Listening effort")
        nxt = gr.Button("Submit and next")

        def show(s):
            k = s["k"]
            if k >= len(s["trials"]):
                return s, "**Done - thank you.**", gr.update(value=None), "", None, gr.update(value=None)
            t = s["trials"][k]
            s["t0"] = time.time()
            cu = gr.update(value=str(STIM / f"{t['cue']}.wav")) if t.get("cue") else gr.update(value=None)
            return s, f"Trial {k + 1} of {len(s['trials'])}", gr.update(value=str(STIM / f"{t['code']}.wav")), "", None, cu

        def begin(p, s):
            p = int(p or 0)
            s = dict(pid=uuid.uuid4().hex[:8], pnum=p, trials=trials_for(p), k=0)
            return show(s)

        def submit(r, e, s):
            if not s or s.get("k", 0) >= len(s.get("trials", [])):
                return show(s) if s else (s, "Press Start", None, "", None, None)
            t = s["trials"][s["k"]]
            record(dict(participant=s["pid"], listener_type="human", pnum=s["pnum"], trial=s["k"], id=t["id"],
                        cond=t["cond"], snr=t["snr"], method=t["method"], response=r, wcr=round(wcr(t["text"], r), 4),
                        effort=int(str(e)[0]) if e else np.nan, plays=1, rt_s=round(time.time() - s["t0"], 1),
                        ts=time.strftime("%Y-%m-%dT%H:%M:%S")))
            s["k"] += 1
            return show(s)

        start.click(begin, [pnum, st], [st, progress, audio, resp, effort, cue])
        nxt.click(submit, [resp, effort, st], [st, progress, audio, resp, effort, cue])
    demo.launch(server_name="0.0.0.0", server_port=PORT, share=SHARE)


PORT, SHARE = 7861, False


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true"); ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--set", default="r3", choices=["r3", "r5"], help="stimulus set")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--share", action="store_true", help="also create a temporary public gradio link (your choice)")
    a = ap.parse_args()
    use_set(a.set)
    PORT = a.port or (7861 if a.set == "r3" else 7862); SHARE = a.share
    if a.build:
        build()
    elif a.analyze:
        analyze()
    elif a.selftest:
        selftest()
    else:
        if not PLAN.exists():
            build()
        app()
