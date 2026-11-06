"""Routes for the listening page (mounted into app.py on port 7860, or standalone).

  GET  /rtdemo/            -> selab/rtdemo/web/index.html
  GET  /rtdemo/data/...    -> listening/rtdemo/web/data (pre-rendered tracks, scene json)
  POST /rtdemo/api/pref    -> appends a blind A/B vote to results/rtdemo/blind_prefs.csv

Standalone (no Gradio):  python -m selab.rtdemo.server --port 7861   (binds 127.0.0.1 by default; local only)
"""
import csv, json, threading
from pathlib import Path
from ..common import ROOT

PAGE = Path(__file__).resolve().parent / "web" / "index.html"
DATA = ROOT / "listening" / "rtdemo" / "web" / "data"
PREFS = ROOT / "results" / "rtdemo" / "blind_prefs.csv"
FIELDS = ["ts", "scene", "x_mode", "y_mode", "choice", "preferred_mode", "level_match", "n_toggles", "listen_s", "pool", "comment"]
_lock = threading.Lock()


def add_routes(app):
    from fastapi import Request
    from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles

    @app.get("/rtdemo")
    def _redir():
        return RedirectResponse("/rtdemo/")

    @app.get("/rtdemo/")
    def _page():
        return FileResponse(PAGE, media_type="text/html", headers={"Cache-Control": "no-store"})

    @app.post("/rtdemo/api/pref")
    async def _pref(req: Request):
        rec = await req.json()
        row = {k: str(rec.get(k, ""))[:500] for k in FIELDS}
        with _lock:
            PREFS.parent.mkdir(parents=True, exist_ok=True)
            new = not PREFS.exists()
            with open(PREFS, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                if new:
                    w.writeheader()
                w.writerow(row)
            n = sum(1 for _ in open(PREFS)) - 1
        return JSONResponse({"ok": True, "n": n})

    DATA.mkdir(parents=True, exist_ok=True)
    app.mount("/rtdemo/data", StaticFiles(directory=str(DATA)), name="rtdemo_data")
    return app


def main():
    import argparse, uvicorn
    from fastapi import FastAPI
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=7861); ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    app = add_routes(FastAPI())
    print(f"open http://{a.host}:{a.port}/rtdemo/", flush=True)
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
