"""Round 4b: how clean must the device's own signal be? (capture-SNR x delay x gain sweep)

Same bar scenes as openear.py. Instead of a specific beamformer, the device emits the friend's signal plus
residual noise at a controlled device SNR (0..30 dB, noise = the remote-mic noise image, i.e. real babble
character).  This maps any capture front-end (beamformer, table array, causal TSE, remote mic) onto the
benefit the listener actually gets once the device copy is mixed with the direct sound at the open ear.
"""
import time, argparse
import numpy as np, pandas as pd
from .openear import build_scene, speech_pool, estoi, equiv_curve, to_equiv, delay, OUTD
from .common import FS, rms


def run(n=10, seed=33):
    tgt, itf, bab = speech_pool(); rows = []; t0 = time.time()
    for si in range(n):
        rng = np.random.default_rng(seed * 1000 + si)
        sc0 = build_scene(rng, tgt, itf, bab)
        for snr in (-5, 0):
            sc = dict(sc0); t_ear = sc0["T"][-1]; k = rms(t_ear) / rms(sc0["N"][-1]) / 10 ** (snr / 20)
            sc["N"] = sc0["N"] * k; mix = t_ear + sc["N"][-1]; e = sc["early"]
            snrs, curve = equiv_curve(sc); b0 = to_equiv(snrs, curve, estoi(e, mix))
            nz = sc0["N"][sc0["idx"]["remote"]][0]  # babble-like residual
            for dsnr in (0, 5, 10, 15, 20, 30):
                y = t_ear + nz * rms(t_ear) / rms(nz) / 10 ** (dsnr / 20)
                for D in (1, 3, 5, 10, 20):
                    for g in (6, 10, 20):
                        ear = mix + delay(y * 10 ** (g / 20), D * FS / 1000)
                        v = estoi(e, ear)
                        rows.append(dict(scene=si, snr_in=snr, dev_snr=dsnr, D_ms=D, gain_db=g, estoi=v,
                                         benefit_db=to_equiv(snrs, curve, v) - b0))
        print(f"scene {si} {time.time()-t0:.0f}s", flush=True)
        pd.DataFrame(rows).to_csv(OUTD / f"capture_sweep_{seed}.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=10); ap.add_argument("--seed", type=int, default=33)
    a = ap.parse_args(); run(a.n, a.seed)
