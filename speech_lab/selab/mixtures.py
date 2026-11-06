"""Build the synthetic test set (single-channel + 4-mic array) from documented public sources.

Sources (see scripts/get_data.sh):
  speech  : Mini LibriSpeech dev-clean-2 (OpenSLR SLR31, CC BY 4.0)
  traffic : ESC-50 classes engine / car_horn / siren / train (CC BY-NC 3.0) -> composite street scene
  broadband environmental : MUSAN noise/free-sound "Background noises" subset (CC licences per MUSAN)
  pink    : synthetic stationary pink noise (1/f), generated here
  babble  : 6 LibriSpeech talkers (disjoint speaker pool from targets)
  competing speaker : 1 LibriSpeech talker (disjoint pool)
  reverb  : pyroomacoustics image-method shoebox rooms, RT60 0.4-0.8 s, + 6-talker spatialised babble

Everything is seeded; re-running produces identical files.
Usage: python -m selab.mixtures [--n_per 8] [--snrs -5 0 5] [--tag r1]
"""
import argparse, csv, glob, json, random
from pathlib import Path
import numpy as np
import pyroomacoustics as pra
from .common import DATA, MIX, FS, load, save, rms, match_len

LS = DATA / "LibriSpeech" / "dev-clean-2"


def librispeech_index():
    items = []
    for tf in sorted(LS.glob("*/*/*.trans.txt")):
        for line in open(tf):
            uid, text = line.strip().split(" ", 1)
            spk = uid.split("-")[0]
            items.append(dict(uid=uid, spk=spk, text=text, path=str(tf.parent / f"{uid}.flac")))
    return items


def esc_files(cats):
    rows = list(csv.DictReader(open(DATA / "ESC-50-master/meta/esc50.csv")))
    return {c: [str(DATA / "ESC-50-master/audio" / r["filename"]) for r in rows if r["category"] == c] for c in cats}


def pink(n, rng):
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.arange(len(X)); f[0] = 1
    y = np.fft.irfft(X / np.sqrt(f), n)
    return (y / rms(y)).astype(np.float32)


def fill(seglist, n, rng, loader):
    """Concatenate random clips until length n (random start offset)."""
    out = []
    tot = 0
    while tot < n + FS:
        try:
            x = loader(rng.choice(seglist))
        except Exception:  # 3 MUSAN files are missing on the HF mirror ("Entry not found" stubs): redraw
            continue
        x = x / (rms(x) + 1e-9)
        out.append(x); tot += len(x)
    y = np.concatenate(out)
    s = rng.integers(0, len(y) - n)
    return y[s:s + n]


def make_babble(pool, n, rng, k=6):
    spks = rng.choice(sorted(pool), size=k, replace=False)
    srcs = [fill(pool[s], n, rng, lambda p: load(p)) for s in spks]
    return srcs


def make_traffic(esc, n, rng):
    bed = fill(esc["engine"] + esc["train"], n, rng, load)
    ev = np.zeros(n, np.float32)
    for _ in range(rng.integers(2, 5)):  # sparse horn / siren events
        c = load(rng.choice(esc["car_horn"] + esc["siren"]))
        c = c / (rms(c) + 1e-9)
        s = rng.integers(0, max(1, n - len(c)))
        seg = c[: n - s]
        ev[s:s + len(seg)] += 0.7 * seg
    y = bed + ev
    return y / rms(y)


def scale_to_snr(s, n, snr):
    return n * (rms(s) / (rms(n) + 1e-12)) / (10 ** (snr / 20))


def rir_room(rng, rt60, n_mics=1, spacing=0.04):
    dims = np.array([rng.uniform(5, 9), rng.uniform(4, 7), rng.uniform(2.7, 3.3)])
    e_abs, max_order = pra.inverse_sabine(rt60, dims)
    room = pra.ShoeBox(dims, fs=FS, materials=pra.Material(e_abs), max_order=min(max_order, 40))
    c = np.array([rng.uniform(1.5, dims[0] - 1.5), rng.uniform(1.5, dims[1] - 1.5), 1.5])
    if n_mics == 1:
        mics = c[:, None]
    else:
        mics = np.stack([c + np.array([(i - (n_mics - 1) / 2) * spacing, 0, 0]) for i in range(n_mics)], 1)
    room.add_microphone_array(mics)
    return room, dims, c


def spatialise(room_fn, sources, positions, n, early_ms=50):
    """Return per-source mic images (n_src, n_mics, n) and the early-reverb image of source 0."""
    room = room_fn()
    for s, p in zip(sources, positions):
        room.add_source(p, signal=s)
    room.compute_rir()
    imgs = []
    early0 = None
    for k, s in enumerate(sources):
        chans = []
        for m in range(room.mic_array.R.shape[1]):
            h = room.rir[m][k]
            chans.append(match_len(np.convolve(s, h)[: n], n))
            if k == 0 and m == 0:
                d = int(np.argmax(np.abs(h)))
                he = h[: d + int(early_ms * FS / 1000)]
                early0 = match_len(np.convolve(s, he), n)
        imgs.append(np.stack(chans))
    return np.stack(imgs).astype(np.float32), early0.astype(np.float32)


def pos_at(c, dims, rng, az_deg=None, dist=None):
    az = np.deg2rad(az_deg if az_deg is not None else rng.uniform(0, 360))
    d = dist if dist is not None else rng.uniform(1.0, 2.5)
    p = c + np.array([d * np.cos(az), d * np.sin(az), rng.uniform(-0.2, 0.3)])
    return np.clip(p, [0.3, 0.3, 0.5], dims - 0.3)


def build(n_per=8, snrs=(-5, 0, 5), tag="r1", seed=0, conds=None, multichannel=True, exclude_tag=None):
    rng = np.random.default_rng(seed)
    items = librispeech_index()
    spks = sorted({i["spk"] for i in items})
    random.Random(seed).shuffle(spks)
    tgt_spk, int_spk = spks[: len(spks) // 2], spks[len(spks) // 2:]
    by_spk = {}
    for it in items:
        by_spk.setdefault(it["spk"], []).append(it)
    pool = {s: [i["path"] for i in by_spk[s]] for s in int_spk}
    # candidate targets: 4-8 s utterances, with a second utterance of same speaker for enrolment
    cand = []
    for s in tgt_spk:
        u = [i for i in by_spk[s]]
        good = [i for i in u if 4 * FS <= len(load(i["path"])) <= 8 * FS]
        for g in good:
            enr = [i for i in u if i["uid"] != g["uid"]]
            cand.append((g, enr[0]))
    if exclude_tag:  # round 2: use target utterances never seen in round 1
        used = {m["uid"] for m in json.load(open(MIX / exclude_tag / "meta.json"))}
        cand = [c for c in cand if c[0]["uid"] not in used]
        print(f"{len(cand)} unused target utterances available")
    esc = esc_files(["engine", "train", "car_horn", "siren"])
    musan = sorted(glob.glob(str(DATA / "musan_bg" / "*.wav")))
    conds = conds or ["babble", "traffic", "broadband_env", "pink", "competing", "reverb_babble"]
    out_dir = MIX / tag
    meta = []
    for cond in conds:
        for snr in snrs:
            picks = rng.choice(len(cand), size=min(n_per, len(cand)), replace=False)
            for j, pi in enumerate(picks):
                tgt, enr = cand[pi]
                s = load(tgt["path"]); n = len(s)
                ref = s.copy()
                if cond == "babble":
                    noise = sum(make_babble(pool, n, rng))
                elif cond == "traffic":
                    noise = make_traffic(esc, n, rng)
                elif cond == "broadband_env":
                    noise = fill(musan, n, rng, load)
                elif cond == "pink":
                    noise = pink(n, rng)
                elif cond == "competing":
                    noise = make_babble(pool, n, rng, k=1)[0]
                elif cond == "reverb_babble":
                    rt60 = float(rng.uniform(0.4, 0.8))
                    room, dims, c = rir_room(rng, rt60)
                    bab = make_babble(pool, n, rng)
                    pos = [pos_at(c, dims, rng, dist=rng.uniform(1.0, 2.0))] + [pos_at(c, dims, rng, dist=rng.uniform(2.0, 3.5)) for _ in bab]
                    imgs, early = spatialise(lambda: room, [s] + bab, pos, n)
                    s_rev = imgs[0, 0]
                    noise = imgs[1:, 0].sum(0)
                    # SNR defined w.r.t. the full reverberant target at the mic; reference = early (direct+50 ms)
                    noise = scale_to_snr(s_rev, noise, snr)
                    mix = s_rev + noise
                    ref = early
                    s = s_rev
                if cond != "reverb_babble":
                    noise = scale_to_snr(s, match_len(noise, n), snr)
                    mix = s + noise
                g = 0.9 / max(np.max(np.abs(mix)), 1e-9)
                mid = f"{cond}_snr{snr:+d}_{j:02d}"
                save(out_dir / mid / "mix.wav", mix * g)
                save(out_dir / mid / "ref.wav", ref * g)
                save(out_dir / mid / "noise.wav", (mix - s) * g)
                save(out_dir / mid / "enrol.wav", load(enr["path"]))
                meta.append(dict(id=mid, cond=cond, snr=snr, uid=tgt["uid"], spk=tgt["spk"], enrol_uid=enr["uid"],
                                 text=tgt["text"], dur=n / FS, gain=g))
    if multichannel:
        meta += build_array(rng, cand, pool, snrs, n_per, out_dir)
    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=1, default=float)
    print(f"wrote {len(meta)} mixtures to {out_dir}")
    return meta


def build_array(rng, cand, pool, snrs, n_per, out_dir, n_mics=4, spacing=0.04):
    """4-mic linear array (4 cm spacing), RT60 0.3 s. Target broadside-ish, interferers at other azimuths."""
    meta = []
    for cond in ["array_babble", "array_competing"]:
        for snr in snrs:
            picks = rng.choice(len(cand), size=n_per, replace=False)
            for j, pi in enumerate(picks):
                tgt, enr = cand[pi]
                s = load(tgt["path"]); n = len(s)
                room, dims, c = rir_room(rng, 0.3, n_mics, spacing)
                tgt_az = float(rng.uniform(70, 110))  # near broadside (90 deg = +y)
                k = 4 if cond == "array_babble" else 1
                ints = make_babble(pool, n, rng, k=k)
                int_az = [float((tgt_az + rng.uniform(40, 320)) % 360) for _ in ints]
                pos = [pos_at(c, dims, rng, az_deg=tgt_az, dist=1.5)] + [pos_at(c, dims, rng, az_deg=a, dist=rng.uniform(1.5, 3.0)) for a in int_az]
                imgs, early = spatialise(lambda: room, [s] + ints, pos, n)
                s_img = imgs[0]
                noise = imgs[1:].sum(0)
                noise = noise * (rms(s_img[0]) / rms(noise[0])) / (10 ** (snr / 20))
                mix = s_img + noise
                g = 0.9 / np.max(np.abs(mix))
                mid = f"{cond}_snr{snr:+d}_{j:02d}"
                save(out_dir / mid / "mix_mc.wav", mix * g)          # (4, n)
                save(out_dir / mid / "mix.wav", mix[0] * g)          # reference mic only
                save(out_dir / mid / "ref.wav", early * g)           # early image at mic 0
                save(out_dir / mid / "target_mc.wav", s_img * g)     # oracle (for oracle-MVDR upper bound only)
                save(out_dir / mid / "noise_mc.wav", noise * g)
                save(out_dir / mid / "noise.wav", noise[0] * g)
                save(out_dir / mid / "enrol.wav", load(enr["path"]))
                meta.append(dict(id=mid, cond=cond, snr=snr, uid=tgt["uid"], spk=tgt["spk"], enrol_uid=enr["uid"],
                                 text=tgt["text"], dur=n / FS, gain=float(g), tgt_az=tgt_az, mic_spacing=spacing,
                                 mic_x=[(i - (n_mics - 1) / 2) * spacing for i in range(n_mics)]))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_per", type=int, default=8)
    ap.add_argument("--snrs", type=int, nargs="+", default=[-5, 0, 5])
    ap.add_argument("--tag", default="r1")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no_array", action="store_true")
    ap.add_argument("--exclude_tag", default=None)
    a = ap.parse_args()
    build(a.n_per, tuple(a.snrs), a.tag, a.seed, multichannel=not a.no_array, exclude_tag=a.exclude_tag)


# ---------------------------------------------------------------------------------------------
# Round 3: OUT-OF-DOMAIN set. Different speech corpus (CMU ARCTIC: studio read speech, US / Scottish /
# Canadian / Indian-English talkers) and RECORDED noise (MS-SNSD test noise, MIT licence).
# None of the pretrained models here saw ARCTIC or MS-SNSD in training (to our knowledge; DNS64 was trained
# on DNS-Challenge data, which draws noise from AudioSet/Freesound/DEMAND, not MS-SNSD's test split).
ARCTIC = DATA / "arctic"
SNSD = DATA / "mssnsd" / "noise_test"
OOD_TARGETS = ["awb", "clb", "ksp", "slt"]       # Scottish m, US f, Indian m, US f
OOD_INTERFERERS = ["bdl", "jmk", "rms", "aew"]   # US m, Canadian m, US m, US m


def arctic_index(spk):
    d = ARCTIC / f"cmu_us_{spk}_arctic"
    out = []
    for line in open(d / "etc" / "txt.done.data"):
        line = line.strip().strip("()").strip()
        uid, text = line.split(" ", 1)
        out.append(dict(uid=f"{spk}_{uid}", spk=spk, text=text.strip().strip('"'), path=str(d / "wav" / f"{uid}.wav")))
    return out


def snsd(prefixes):
    return sorted(str(p) for p in SNSD.glob("*.wav") if any(p.name.startswith(x + "_") for x in prefixes))


def build_ood(n_per=8, snrs=(-5, 0, 5), tag="r3", seed=3):
    rng = np.random.default_rng(seed)
    idx = {s: arctic_index(s) for s in OOD_TARGETS + OOD_INTERFERERS}
    pool = {s: [i["path"] for i in idx[s]] for s in OOD_INTERFERERS}
    noises = {"rec_babble": snsd(["Babble"]), "rec_hvac": snsd(["AirConditioner", "VacuumCleaner"]),
              "rec_transient": snsd(["ShuttingDoor", "Munching", "Typing", "CopyMachine"]),
              "rec_announcements": snsd(["AirportAnnouncements"])}
    conds = list(noises) + ["ood_competing", "ood_reverb_rec_babble"]
    out_dir = MIX / tag
    meta = []
    for cond in conds:
        for snr in snrs:
            for j in range(n_per):
                spk = OOD_TARGETS[j % len(OOD_TARGETS)]
                u = idx[spk]
                k = int(rng.integers(0, len(u) - 3))
                # ARCTIC prompts are 2-4 s: concatenate two consecutive prompts (0.3 s gap) -> 4-8 s target
                s = np.concatenate([load(u[k]["path"]), np.zeros(int(0.3 * FS), np.float32), load(u[k + 1]["path"])])
                text = u[k]["text"] + " " + u[k + 1]["text"]
                enr = np.concatenate([load(u[k + 2]["path"]), load(u[k + 3]["path"])])
                n = len(s); ref = s.copy()
                if cond in noises:
                    noise = fill(noises[cond], n, rng, load)
                    noise = scale_to_snr(s, noise, snr); mix = s + noise
                elif cond == "ood_competing":
                    noise = make_babble(pool, n, rng, k=1)[0]
                    noise = scale_to_snr(s, noise, snr); mix = s + noise
                else:  # target reverberated in a simulated room + recorded (already-reverberant) babble added
                    rt60 = float(rng.uniform(0.4, 0.8))
                    room, dims, c = rir_room(rng, rt60)
                    imgs, early = spatialise(lambda: room, [s], [pos_at(c, dims, rng, dist=rng.uniform(1.0, 2.0))], n)
                    s_rev = imgs[0, 0]; ref = early
                    noise = scale_to_snr(s_rev, fill(noises["rec_babble"], n, rng, load), snr)
                    mix = s_rev + noise; s = s_rev
                g = 0.9 / max(np.max(np.abs(mix)), 1e-9)
                mid = f"{cond}_snr{snr:+d}_{j:02d}"
                save(out_dir / mid / "mix.wav", mix * g); save(out_dir / mid / "ref.wav", ref * g)
                save(out_dir / mid / "noise.wav", (mix - s) * g); save(out_dir / mid / "enrol.wav", enr)
                meta.append(dict(id=mid, cond=cond, snr=snr, uid=u[k]["uid"], spk=spk, text=text, dur=n / FS, gain=float(g)))
    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=1, default=float)
    print(f"wrote {len(meta)} OOD mixtures to {out_dir}")
