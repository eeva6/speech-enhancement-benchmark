"""Read members of a remote zip via HTTP Range requests (download only what is needed)."""
import io, sys, zipfile, urllib.request

class HTTPFile(io.RawIOBase):
    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            self.size = int(r.headers["Content-Range"].split("/")[-1])
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos
    def readinto(self, b):
        n = len(b)
        if self.pos >= self.size or n == 0: return 0
        end = min(self.size, self.pos + n) - 1
        for attempt in range(5):
            try:
                req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
                with urllib.request.urlopen(req, timeout=120) as r: data = r.read()
                break
            except Exception as e:
                if attempt == 4: raise
        b[:len(data)] = data; self.pos += len(data); return len(data)

def open_zip(url):
    return zipfile.ZipFile(io.BufferedReader(HTTPFile(url), buffer_size=8 << 20))
