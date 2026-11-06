"""Curate original-vs-processed listening examples + an offline HTML player page.
python -m selab.listening --tag r1   -> listening/<tag>/<condition>/*.wav, listening/index.html
Selection rule (fixed in advance, not cherry-picked): utterance index 00 of every condition at 0 dB,
plus index 00 at the hardest SNR (-5 dB in r1).
"""
import argparse, json, shutil, html
import pandas as pd
from .common import ROOT, MIX, OUT, RES

METHODS = ["wiener_dd", "metricgan_plus", "demucs_dns64", "sepformer_enh", "tse_convtasnet_ecapa",
           "bf_mvdr_ff", "bf_mvdr_mask", "bf_mvdr_oracle", "demucs_then_tse"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="r1"); ap.add_argument("--snrs", default="+0,-5")
    a = ap.parse_args()
    meta = {m["id"]: m for m in json.load(open(MIX / a.tag / "meta.json"))}
    met = pd.read_csv(RES / a.tag / "metrics.csv")
    wer = pd.read_csv(RES / a.tag / "wer.csv") if (RES / a.tag / "wer.csv").exists() else None
    ld = ROOT / "listening" / a.tag
    if ld.exists():
        shutil.rmtree(ld)
    conds = sorted({m["cond"] for m in meta.values()})
    rows = [f"<h1>Listening examples ({a.tag})</h1><p>Fixed selection rule: first utterance of every condition at "
            f"{a.snrs} dB input SNR. Metrics are measured; WER from Whisper base.en (proxy, not a human test). "
            "Use headphones; levels are not loudness-matched (each file is peak-normalised only if it would clip).</p>"]
    for c in conds:
        for s in a.snrs.split(","):
            mid = f"{c}_snr{s}_00"
            if mid not in meta:
                continue
            od = ld / mid; od.mkdir(parents=True)
            items = [("mixture (unprocessed)", MIX / a.tag / mid / "mix.wav", "noisy"), ("clean reference", MIX / a.tag / mid / "ref.wav", None)]
            items += [(m, OUT / a.tag / m / f"{mid}.wav", m) for m in METHODS if (OUT / a.tag / m / f"{mid}.wav").exists()]
            rows.append(f"<h2>{html.escape(mid)}</h2><p><i>{html.escape(meta[mid]['text'].lower())}</i></p><table border=1 cellpadding=4>"
                        "<tr><th>version</th><th>audio</th><th>SI-SDR dB</th><th>ESTOI</th><th>PESQ-WB</th><th>ASR WER</th><th>ASR transcript</th></tr>")
            for name, p, key in items:
                dst = od / (name.split(" ")[0] + ".wav"); shutil.copy(p, dst)
                r = met[(met.method == key) & (met.id == mid)] if key else None
                w = wer[(wer.method == (key or "clean_ref")) & (wer.id == mid)] if wer is not None else None
                cells = [f"{r.iloc[0][k]:.2f}" if r is not None and len(r) else "" for k in ("si_sdr", "estoi", "pesq")]
                wc = f"{w.iloc[0]['wer']:.2f}" if w is not None and len(w) else ""
                hy = html.escape(str(w.iloc[0]["hyp"]))[:160] if w is not None and len(w) else ""
                rows.append(f"<tr><td>{html.escape(name)}</td><td><audio controls preload=none src='{a.tag}/{mid}/{dst.name}'></audio></td>"
                            + "".join(f"<td>{x}</td>" for x in cells) + f"<td>{wc}</td><td>{hy}</td></tr>")
            rows.append("</table>")
    (ROOT / "listening" / f"index_{a.tag}.html").write_text("<html><meta charset=utf-8><body style='font-family:sans-serif'>" + "\n".join(rows) + "</body></html>")
    print("wrote", ROOT / "listening" / f"index_{a.tag}.html")


if __name__ == "__main__":
    main()
