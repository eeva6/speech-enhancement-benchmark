"""Figures + summary for privacy-bubble experiments. Run: python -m selab.privacy.analyze_p"""
import json, numpy as np
from collections import defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .common_p import OUT, BAND_NAMES, load_json, save_json

S = {}


def fig_e1():
    r = load_json("e1_results.json"); D = [0.0, 0.5, 1.0, 2.0, 5.0]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for c, col in (("collar4", "C0"), ("table_ring8", "C1"), ("single_mouth5cm", "C2")):
        for mode, ls in (("free", "-"), ("preserve_partner", "--")):
            y = [r[f"{c}|{mode}|D{d}"]["eaves_3.0m_mean"][-1] for d in D]
            ax[0].plot(D, y, ls, color=col, marker="o", label=f"{c} ({mode})")
            yp = [r[f"{c}|{mode}|D{d}"]["partner_ear"][-1] for d in D]
            ax[1].plot(D, yp, ls, color=col, marker="o")
    ax[0].set(xlabel="system latency D (ms), no prediction", ylabel="speech-weighted change at 3 m (dB)",
              title="E1 eavesdropper (3 m, mean of 16 az)"); ax[0].axhline(0, c="k", lw=.5); ax[0].legend(fontsize=7)
    ax[1].set(xlabel="latency D (ms)", ylabel="change at partner's ear (dB)", title="E1 spillover: partner's ear"); ax[1].axhline(0, c="k", lw=.5)
    x = np.arange(6)
    for c, col in (("collar4", "C0"), ("table_ring8", "C1")):
        for dist, mk in ((2.0, "o"), (5.0, "s")):
            ax[2].plot(x, r[f"{c}|preserve_partner|D0.0"][f"eaves_{dist}m_mean"][:6], color=col, marker=mk, label=f"{c} D=0 {dist} m")
    ax[2].set_xticks(x); ax[2].set_xticklabels(BAND_NAMES, rotation=30); ax[2].axhline(0, c="k", lw=.5)
    ax[2].set(ylabel="dB", title="E1 per band, partner preserved, ideal zero latency"); ax[2].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "e1_anc.png", dpi=120); plt.close(fig)
    mp = load_json("e1_map.json")
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    for a, key in zip(ax, ["collar4|D0.0", "collar4|D1.0", "table_ring8|D0.0"]):
        g = np.array(mp[key]["speech"], float); xs = mp[key]["xs"]
        im = a.imshow(g.T, origin="lower", extent=[xs[0], xs[-1], xs[0], xs[-1]], cmap="RdBu_r", vmin=-20, vmax=20)
        a.plot([-0.45, 0.45], [0, 0], "k^"); a.set_title(f"{key} (free): speech-wtd dB change, z=1.2 m"); plt.colorbar(im, ax=a)
    fig.tight_layout(); fig.savefig(OUT / "e1_map.png", dpi=110); plt.close(fig)
    S["E1"] = {k: {"3m_speech": v["eaves_3.0m_mean"][-1], "2m": v["eaves_2.0m_mean"][-1], "5m": v["eaves_5.0m_mean"][-1],
                   "3m_worst_az": v["eaves_3.0m_worst"][-1], "partner": v["partner_ear"][-1], "own_ear": v["own_ear"][-1],
                   "3m_bands": v["eaves_3.0m_mean"][:6]} for k, v in r.items()}


def fig_e2():
    r = load_json("e2_results.json"); H = r["horizons_ms"]
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.3))
    for meth, col in (("none", "k"), ("lpc32", "C0"), ("nn_mlp", "C3")):
        for bi, ls in ((1, "-"), (3, "--"), (6, ":")):
            y = [r[f"{meth}|{h}|scaled"][bi] for h in H]
            ax[0].semilogx(H, y, ls, color=col, marker="o", label=f"{meth} {r['bands'][bi]}")
    ax[0].set(xlabel="prediction horizon (ms)", ylabel="achievable residual (dB, best gain)", title="E2 waveform prediction -> cancellation")
    ax[0].legend(fontsize=6); ax[0].axhline(0, c="k", lw=.5)
    ph = np.linspace(0, 180, 361); res = 10 * np.log10(np.maximum(4 * np.sin(np.radians(ph) / 2) ** 2, 1e-6))
    ax[1].plot(ph, res); ax[1].axhline(0, c="k", lw=.5); ax[1].axhline(3, c="r", lw=.5, ls="--")
    ax[1].set(xlabel="phase error (deg), equal amplitude", ylabel="residual re uncancelled (dB)", title="Phase error -> cancellation", ylim=(-40, 8))
    f = np.logspace(2, np.log10(4000), 200)
    for sig in (0.01, 0.05, 0.2, 1.0, 10.0):
        e = 2 - 2 * np.exp(-((2 * np.pi * f * sig / 1000) ** 2) / 2)
        ax[2].semilogx(f, 10 * np.log10(np.maximum(e, 1e-6)), label=f"timing jitter sigma={sig} ms")
    ax[2].axhline(3, c="r", lw=.5, ls="--"); ax[2].set(xlabel="frequency (Hz)", ylabel="residual (dB)", title="Timing uncertainty -> residual (word-level LLM ~10-100 ms)", ylim=(-40, 6))
    ax[2].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "e2_prediction.png", dpi=120); plt.close(fig)
    S["E2"] = {k: v for k, v in r.items() if k.endswith("scaled") or k.startswith("nn_train")}
    S["E2"]["phase_for_10dB_deg"] = float(np.degrees(2 * np.arcsin(10 ** (-10 / 20) / 2)))
    S["E2"]["phase_for_20dB_deg"] = float(np.degrees(2 * np.arcsin(10 ** (-20 / 20) / 2)))
    S["E2"]["timing_for_10dB_at_1kHz_us"] = S["E2"]["phase_for_10dB_deg"] / 360 / 1000 * 1e6


def interp_cross(lv, y, thr):
    """first masker level where y <= thr (linear interp); None if never."""
    for i in range(len(lv) - 1):
        if y[i] > thr >= y[i + 1]:
            return round(lv[i] + (y[i] - thr) / (y[i] - y[i + 1]) * (lv[i + 1] - lv[i]), 1)
    return None if y[-1] > thr else lv[0]


def fig_e3():
    o = load_json("e3_obj.json"); a = load_json("e3_asr.json"); c = load_json("e3_cost.json")
    MK = ["ssn", "babble6", "adapt_lag20", "adapt_oracle", "samevoice3"]; LV = [-10, -5, 0, 5, 10]
    dists = ["2.0", "3.0", "5.0"]
    def ob(mk, lv, d, j):
        key = (lambda az: f"{mk}|{lv}|{d}m_az{az}") if lv is not None else (lambda az: f"none|None|{d}m_az{az}")
        return np.mean([o[key(az)][j] for az in (30, 120)])
    asr = defaultdict(list)
    for k, v in a.items():
        mk, lv, rcv, spk = k.split("|"); asr[(mk, lv, rcv)].append(v)
    fig, ax = plt.subplots(1, 4, figsize=(19, 4.3))
    req = {}
    for mk, col in zip(MK, ["C0", "C1", "C2", "C4", "C3"]):
        for d, ls in (("2.0", "-"), ("5.0", ":")):
            es = [ob(mk, lv, d, 1) for lv in LV]; si = [ob(mk, lv, d, 2) for lv in LV]
            ax[0].plot(LV, es, ls, color=col, marker="o", label=f"{mk} {d} m"); ax[1].plot(LV, si, ls, color=col, marker="o")
        for d in dists:
            si = [ob(mk, lv, d, 2) for lv in LV]; es = [ob(mk, lv, d, 1) for lv in LV]
            req[f"{mk}|{d}m"] = {"SII<=0.2": interp_cross(LV, si, 0.2), "SII<=0.1": interp_cross(LV, si, 0.1), "ESTOI<=0.2": interp_cross(LV, es, 0.2)}
        for rcv, ls in (("2.0m_az30", "-"), ("5.0m_az120", ":")):
            y = [np.mean(asr[(mk, str(lv), rcv)]) for lv in (-5, 0, 5)]
            base = np.mean(asr[("none", "None", rcv)])
            ax[2].plot([-10, -5, 0, 5], [base] + y, ls, color=col, marker="o")
            req[f"{mk}|{rcv}"] = req.get(f"{mk}|{rcv}", {}); req[f"{mk}|{rcv}"]["whisper_wc<=0.2"] = interp_cross([-10, -5, 0, 5], [base] + y, 0.2)
            req[f"{mk}|{rcv}"]["whisper_wc"] = [round(base, 3)] + [round(v, 3) for v in y]
        pb = [c[f"{mk}|{lv}"][1] for lv in LV]; pc = [c[f"{mk}|{lv}"][4] for lv in LV]
        ax[3].plot(LV, pb, "-", color=col, marker="o", label=f"{mk} no cancel"); ax[3].plot(LV, pc, "--", color=col, marker="x", label=f"{mk} earbud cancel (4096 taps)")
    for i, t in enumerate(["ESTOI at eavesdropper (human proxy)", "SII proxy at eavesdropper", "Whisper base.en word-correct (machine), -10 = no masker", "Partner's STOI (talker cost)"]):
        ax[i].set(xlabel="masker source level re speech (dB)", title=t)
    ax[1].axhline(0.2, c="k", ls="--", lw=.6); ax[1].axhline(0.1, c="k", ls=":", lw=.6); ax[2].axhline(0.2, c="k", ls="--", lw=.6)
    ax[0].legend(fontsize=6); ax[3].legend(fontsize=6)
    fig.tight_layout(); fig.savefig(OUT / "e3_masking.png", dpi=115); plt.close(fig)
    base = {d: [ob("none", None, d, j) for j in range(5)] for d in dists}
    S["E3"] = {"no_masker": {d: {"STOI": round(base[d][0], 3), "ESTOI": round(base[d][1], 3), "SII": round(base[d][2], 3), "speech_db": round(base[d][3], 1)} for d in dists},
               "required_masker_level_db": req,
               "masker_level_at_eaves_db": {f"{mk}|{lv}": round(np.mean([o[f'{mk}|{lv}|{d}m_az{az}'][4] for d in dists for az in (30, 120)]), 1) for mk in MK for lv in LV},
               "partner_cost": {k: dict(zip(c["_cols"], v)) for k, v in c.items() if k != "_cols"},
               "obj_table": {f"{mk}|{lv}|{d}": [round(ob(mk, lv, d, j), 3) for j in range(3)] for mk in MK for lv in LV for d in dists}}
    w = load_json("e3_whisper.json"); ae = load_json("e3_asr_effort.json")
    eff = defaultdict(list)
    for k, v in ae.items():
        n, rcv, spk = k.split("|"); eff[(n, rcv)].append(v)
    S["E3"]["effort"] = {k: v for k, v in w.items()}
    S["E3"]["effort_whisper_asr"] = {f"{n}|{rcv}": round(np.mean(v), 3) for (n, rcv), v in eff.items()}
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for name, col in (("normal", "k"), ("quiet", "C0"), ("whisper", "C1")):
        lv = [np.mean([w[f"{name}|{d}m_az{az}"][0] for az in (30, 120)]) for d in dists]
        si = [np.mean([w[f"{name}|{d}m_az{az}"][2] for az in (30, 120)]) for d in dists]
        ax[0].plot([2, 3, 5], lv, color=col, marker="o", label=name); ax[1].plot([2, 3, 5], si, color=col, marker="o", label=name)
    for lvl, col in ((-15, "C2"), (-10, "C3")):
        si = [np.mean([w[f"whisper+babble{lvl}|{d}m_az{az}"][1] for az in (30, 120)]) for d in dists]
        ax[1].plot([2, 3, 5], si, "--", color=col, marker="s", label=f"whisper + babble masker {lvl} dB")
    ax[0].axhline(42, c="gray", ls=":", label="ambient 42 dB"); ax[0].set(xlabel="distance (m)", ylabel="speech level (dB)", title="Leaked speech level by vocal effort (room RT60 0.5 s)"); ax[0].legend(fontsize=7)
    ax[1].axhline(0.2, c="k", ls="--", lw=.6); ax[1].axhline(0.1, c="k", ls=":", lw=.6); ax[1].set(xlabel="distance (m)", ylabel="SII proxy", title="Eavesdropper SII: whisper + near-field mic relay"); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "e3_whisper_relay.png", dpi=115); plt.close(fig)


if __name__ == "__main__":
    fig_e1(); fig_e2(); fig_e3()
    save_json(S, "summary.json"); print(json.dumps({k: (v if k != "E1" else "...") for k, v in S.items()}, indent=0)[:6000])
