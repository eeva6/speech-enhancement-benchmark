"""Round 7: streaming, resumable selective extraction of the EasyCom split tar.gz.

Reads data/easycom/parts/EasyComDataset.tar.gz.NNN in order (waiting for each part to be
complete, i.e. renamed from .partial by scripts/r7_download.sh), gunzips and untars as a
stream, and writes only the wanted members to data/easycom/. Files already present with
the right size are skipped, so a restart just re-streams. Every member name is logged to
data/easycom/tar_listing.txt. Stops early once the stream has moved past the wanted
Main/ sub-folders (the tar is in alphabetical order), and writes EXTRACT_DONE.
"""
import os, sys, time, tarfile, json, re

ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "easycom")
ROOT = os.path.abspath(ROOT)
PARTS = os.path.join(ROOT, "parts")
SESS = ["Session_4", "Session_10", "Session_11", "Session_12"]
MAIN_DIRS = ["Close_Microphone_Audio", "Glasses_Microphone_Array_Audio", "Metadata",
             "Speech_Transcriptions", "Tracked_Poses"]
NPARTS = 33


def wanted(name):
    if name.startswith("Calibration/"):
        return True
    p = name.split("/")
    if len(p) >= 4 and p[0] == "Main" and p[1] in MAIN_DIRS and p[2] in SESS:
        return True
    if len(p) == 3 and p[0] == "Main" and p[1] == "Metadata" and p[2][:-4] in SESS:
        return True   # added after the first run (Metadata files are Main/Metadata/Session_N.txt)
    return False


class PartStream:
    """File-like object concatenating the parts, blocking until each is complete."""
    def __init__(self):
        self.i = 1; self.f = None; self.pos_total = 0

    def _open(self):
        while True:
            fn = os.path.join(PARTS, "EasyComDataset.tar.gz.%03d" % self.i)
            if os.path.exists(fn):
                self.f = open(fn, "rb"); print(time.strftime("%H:%M:%S"), "reading", fn, flush=True); return True
            if os.path.exists(fn + ".deleted"):
                raise RuntimeError("part %d deleted before extraction finished" % self.i)
            if os.path.exists(os.path.join(ROOT, "EXTRACT_ABORT")):
                raise RuntimeError("abort")
            time.sleep(20)

    def read(self, n=-1):
        out = b""
        while n < 0 or len(out) < n:
            if self.f is None:
                if self.i > NPARTS:
                    break
                self._open()
            b = self.f.read(n - len(out) if n >= 0 else 1 << 24)
            if not b:
                self.f.close(); self.f = None; self.i += 1; continue
            out += b
            if n < 0:
                continue
        self.pos_total += len(out)
        return out


def main():
    if os.path.exists(os.path.join(ROOT, "EXTRACT_DONE")):
        print("already done"); return
    s = PartStream()
    tf = tarfile.open(fileobj=s, mode="r|gz", bufsize=1 << 20)
    lst = open(os.path.join(ROOT, "tar_listing.txt"), "w")
    seen_dirs = set(); n_x = n_skip = 0; t0 = time.time()
    for m in tf:
        lst.write("%d\t%d\t%s\n" % (s.i, m.size, m.name)); lst.flush()
        p = m.name.split("/")
        if len(p) >= 2 and p[0] == "Main":
            seen_dirs.add(p[1])
            # early stop: past every wanted Main sub-folder (alphabetical tar order)
            if p[1] > max(MAIN_DIRS) and all(d in seen_dirs for d in MAIN_DIRS):
                print("past wanted folders at", m.name, "part", s.i, flush=True)
                break
        if not m.isfile() or not wanted(m.name):
            continue
        out = os.path.join(ROOT, m.name)
        if os.path.exists(out) and os.path.getsize(out) == m.size:
            n_skip += 1; continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        src = tf.extractfile(m)
        with open(out + ".tmp", "wb") as g:
            while True:
                b = src.read(1 << 22)
                if not b: break
                g.write(b)
        os.replace(out + ".tmp", out); n_x += 1
        if n_x % 20 == 0:
            print(time.strftime("%H:%M:%S"), "extracted", n_x, "skipped", n_skip, m.name, "%.0fs" % (time.time() - t0), flush=True)
    json.dump({"extracted": n_x, "skipped": n_skip, "last_part_read": s.i, "main_dirs_seen": sorted(seen_dirs),
               "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
              open(os.path.join(ROOT, "EXTRACT_DONE"), "w"), indent=1)
    print("DONE", n_x, n_skip, flush=True)


if __name__ == "__main__":
    main()
