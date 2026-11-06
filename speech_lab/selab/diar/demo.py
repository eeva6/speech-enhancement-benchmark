"""Demo transcripts (text only; no audio is exported): python -m selab.diar.demo <uri> <variant> [seconds]
Writes results/diar/demo_<dataset>.txt: the system's speaker-attributed transcript for the first N seconds next to the
human reference turns of the same span. For EasyCom (CC-BY-NC) this is text derived for research use only."""
import sys
from . import data
from ..common import RES

OUT = RES / "diar"


def main():
    uri, variant = sys.argv[1], sys.argv[2]
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 120.0
    ds = "libricss" if uri.startswith("lc_") else "easycom"
    it = [i for sp in (("lc_test",) if ds == "libricss" else ("ec_test",)) for i in data.items(sp) if i["uri"] == uri][0]
    hyp = open(OUT / "transcripts" / variant / f"{uri}.txt").read().splitlines()
    keep = []
    for ln in hyp:
        mm, ss = ln[1:6], ln[7:11]
        try:
            t = int(ln[1:3]) * 60 + float(ln[4:8])
        except ValueError:
            continue
        if t <= secs:
            keep.append(ln)
    if ds == "libricss":
        from ..libricss import read_info
        import numpy as np
        A = data.libricss_clock(it)
        ref = [(r["start"] + np.polyval(A, r["start"]) / 16000, r["spk"], r["text"].lower()) for r in read_info(it["dir"])]
    else:
        from .. import ec_r7 as E
        import soundfile as sf
        ref = []; off = 0.0
        for seg in data.easycom_segs(it):
            n = sf.info(str(E.CACHE / f"Session_{it['sess']}" / f"{seg}.wav")).frames / 16000
            ref += [(off + u["start"], f"P{u['pid']}" + (" (wearer)" if u["pid"] == 2 else ""), u["text"]) for u in E.transcripts(it["sess"], seg)]
            off += n
            if off > secs:
                break
    ref = [r for r in sorted(ref) if r[0] <= secs]
    lines = [f"# Demo: {uri}, system variant {variant}, first {secs:.0f} s",
             "# Speaker labels are anonymous cluster ids; they are matched to people only through the scoring.",
             "" if ds == "libricss" else "# EasyCom (CC-BY-NC 4.0): transcript text for research use only, no audio exported.",
             "", "## System output (faster-whisper base.en words + diarization)", *keep, "",
             "## Human reference (speaker ids from the dataset)"]
    lines += [f"[{int(t // 60):02d}:{t % 60:04.1f}] {s}: {txt}" for t, s, txt in ref]
    (OUT / f"demo_{ds}.txt").write_text("\n".join(lines) + "\n")
    print("wrote", OUT / f"demo_{ds}.txt", len(keep), len(ref))


if __name__ == "__main__":
    main()
