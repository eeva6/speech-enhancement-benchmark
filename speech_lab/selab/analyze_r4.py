"""Summarise round 4 (open-ear / form-factor simulation) into tables + figures."""
import glob
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from .common import RES

R = RES / "r4"; F = R / "figs"; F.mkdir(parents=True, exist_ok=True)


def ci(x):
    x = np.asarray(x); rng = np.random.default_rng(0)
    b = [rng.choice(x, len(x)).mean() for _ in range(1000)]
    return np.percentile(b, 2.5), np.percentile(b, 97.5)


def main():
    files = [f for f in glob.glob(str(R / "openear_raw*.csv")) if "test" not in f]
    d = pd.concat([pd.read_csv(f).assign(src=f) for f in files])
    d["scene_uid"] = d.src + "_" + d.scene.astype(str)
    n_sc = d.scene_uid.nunique()
    lab = {"glasses_sd2ms": "Glasses, 6 mics", "neckband_sd2ms": "Neckband, 6 mics", "tabletop_sd2ms": "Tabletop, 8-mic ring",
           "remote_mic": "Phone/clip mic at friend", "ear_amp_sd2ms": "Plain amplifier (1 mic at ear)", "ideal_clean": "Ideal: perfectly clean voice"}
    # best (shortest) delay per config, +10 and +20 dB gain, open delivery
    rows = []
    for c, name in lab.items():
        x = d[(d.config == c) & (d.delivery == "open")]
        D0 = x.D_ms.min()
        for g in (0, 10, 20):
            y = x[(x.D_ms == D0) & (x.gain_db == g)].benefit_db
            if len(y): lo, hi = ci(y); rows.append(dict(form=name, delay_ms=D0, gain_db=g, benefit_db=y.mean(), lo=lo, hi=hi))
    t1 = pd.DataFrame(rows); t1.to_csv(R / "benefit_by_form.csv", index=False)
    # delay curves at +10 dB
    t2 = d[(d.gain_db == 10) & (d.delivery == "open") & d.config.isin(lab)].groupby(["config", "D_ms"]).benefit_db.mean().reset_index()
    t2.to_csv(R / "benefit_vs_delay.csv", index=False)
    occl = d[(d.gain_db == 10)].groupby(["config", "delivery", "D_ms"]).benefit_db.mean().unstack("delivery").reset_index()
    occl.to_csv(R / "open_vs_inear.csv", index=False)
    pf = d[(d.gain_db == 10) & (d.delivery == "open")].groupby(["config"]).apply(lambda g: g[g.D_ms == g.D_ms.min()].benefit_db.mean()).rename("benefit_at_min_delay").reset_index()
    pf.to_csv(R / "postfilter_effect.csv", index=False)
    dev = d.groupby("config").snr_dev_db.mean().rename("device_snr_minus_ear_snr_dB")
    dev.to_csv(R / "device_snr.csv")

    fig, ax = plt.subplots(figsize=(7, 4.2))
    for c, name in lab.items():
        z = t2[t2.config == c]
        if len(z): ax.plot(z.D_ms, z.benefit_db, "o-", label=name)
    ax.axhline(0, color="k", lw=0.8); ax.axvspan(0, 6, color="g", alpha=0.08)
    ax.set_xlabel("total device delay (ms)"); ax.set_ylabel("equivalent SNR benefit at the ear (dB)")
    ax.set_title("Open-ear delivery, device voice +10 dB over the direct voice"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(F / "benefit_vs_delay.png", dpi=120)

    cap = [pd.read_csv(f) for f in glob.glob(str(R / "capture_sweep_*.csv"))]
    if cap:
        c = pd.concat(cap)
        t3 = c.groupby(["dev_snr", "D_ms", "gain_db"]).benefit_db.mean().reset_index(); t3.to_csv(R / "capture_sweep_summary.csv", index=False)
        fig, ax = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
        for a, g in zip(ax, (10, 20)):
            for D in sorted(t3.D_ms.unique()):
                z = t3[(t3.D_ms == D) & (t3.gain_db == g)]; a.plot(z.dev_snr, z.benefit_db, "o-", label=f"{D} ms")
            a.axhline(0, color="k", lw=.8); a.set_title(f"device voice +{g} dB over direct"); a.set_xlabel("how clean the device signal is (device SNR, dB)")
        ax[0].set_ylabel("equivalent SNR benefit at the ear (dB)"); ax[1].legend(title="delay")
        fig.tight_layout(); fig.savefig(F / "capture_sweep.png", dpi=120)
    with open(R / "summary_r4.md", "w") as f:
        f.write(f"# Round 4 summary ({n_sc} scenes x 2 input SNRs)\n\n## Benefit by form factor (shortest delay)\n")
        f.write(t1.round(2).to_markdown(index=False)); f.write("\n\n## Benefit vs delay (+10 dB)\n")
        f.write(t2.round(2).to_markdown(index=False)); f.write("\n\n## Open vs in-ear (+10 dB)\n")
        f.write(occl.round(2).to_markdown(index=False)); f.write("\n\n## Device SNR advantage over the ear\n")
        f.write(dev.round(2).to_markdown()); f.write("\n\n## Post-filter effect (min delay, +10 dB)\n")
        f.write(pf.round(2).to_markdown(index=False))
        if cap: f.write("\n\n## Capture sweep\n"); f.write(t3.round(2).to_markdown(index=False))
    print(open(R / "summary_r4.md").read()[:6000])


if __name__ == "__main__":
    main()
