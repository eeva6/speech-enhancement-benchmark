"""Fetch selected LibriCSS members (raw 7-ch recording + per-speaker dry sources) via HTTP range reads."""
import sys, os, json, time, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from selab.httpzip import open_zip
U = "https://drive.usercontent.google.com/download?id=1Piioxd5G_85K9Bhcr8ebdhXx0CnaHy7l&export=download&confirm=t&uuid=69400818-7d49-4353-9ff8-0f3cf45c4b65"
ROOT = "data/libricss/"
def main(conds, sessions, kinds=("record/raw_recording.wav", "clean/each_spk.wav")):
    z = open_zip(U)
    for i in z.infolist():
        p = i.filename.split("/")
        if len(p) < 4 or p[1] not in conds: continue
        s = int(p[2].split("session")[1].split("_")[0])
        if s not in sessions or not any(i.filename.endswith(k) for k in kinds): continue
        out = ROOT + i.filename
        if os.path.exists(out) and os.path.getsize(out) == i.file_size: continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        t = time.time()
        with z.open(i) as src, open(out + ".part", "wb") as dst: shutil.copyfileobj(src, dst, 8 << 20)
        os.replace(out + ".part", out)
        print(f"{i.filename} {i.compress_size/1e6:.0f}MB {time.time()-t:.0f}s", flush=True)
if __name__ == "__main__":
    main(sys.argv[1].split(","), [int(x) for x in sys.argv[2].split(",")])
