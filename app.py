"""
VibeMix — tiny local server. Double-click the launcher, it opens your browser.
Put songs in the `tracks` folder next to this file (or use "Add songs" in the app).
Mixes land in `mixes`. Saved arrangements are `mixes/*.vibemix.json`.
"""
import os, re, sys, json, socket, threading, webbrowser, traceback, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote

import engine

VERSION = "0.2"
PORT = 8765

BASE = os.path.dirname(os.path.abspath(sys.argv[0]))
if getattr(sys, "frozen", False):            # packaged app: folders live next to the app
    BASE = os.path.dirname(sys.executable)
    if sys.platform == "darwin" and ".app/Contents/MacOS" in BASE:   # inside VibeMix.app → next to the .app
        BASE = os.path.dirname(BASE.split(".app/Contents/MacOS")[0] + ".app")
TRACKS = os.path.join(BASE, "tracks")
MIXES = os.path.join(BASE, "mixes")
CACHE = os.path.join(BASE, ".cache")
os.makedirs(TRACKS, exist_ok=True)
os.makedirs(MIXES, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)
HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
if getattr(sys, "frozen", False):
    HTML = os.path.join(sys._MEIPASS, "index.html")
AUDITION_WAV = os.path.join(CACHE, "audition.wav")

MIME = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".flac": "audio/flac", ".ogg": "audio/ogg",
        ".opus": "audio/ogg", ".aiff": "audio/aiff", ".aif": "audio/aiff", ".m4a": "audio/mp4",
        ".aac": "audio/aac", ".wma": "audio/x-ms-wma"}

state = {"running": False, "job": None, "progress": None, "result": None, "error": None}
lock = threading.Lock()


# ---------- helpers ----------

def list_tracks():
    out = []
    for name in sorted(os.listdir(TRACKS), key=str.lower):
        if name.lower().endswith(engine.AUDIO_EXT) and not name.startswith("."):
            try:
                out.append(engine.track_info(os.path.join(TRACKS, name)))
            except Exception as e:
                out.append({"file": name, "error": str(e)})
    return out


def list_mixes():
    out = []
    for name in sorted(os.listdir(MIXES), key=str.lower):
        if name.endswith(".vibemix.json"):
            try:
                pl = json.load(open(os.path.join(MIXES, name), encoding="utf-8"))
                out.append({"name": name[:-len(".vibemix.json")], "songs": len(pl.get("tracks", [])),
                            "saved": pl.get("saved")})
            except Exception:
                pass
    return out


def mix_path(name):
    return os.path.join(MIXES, engine.safe_name(name) + ".vibemix.json")


def safe_track_path(name):
    name = os.path.basename(unquote(name))
    path = os.path.join(TRACKS, name)
    return path if os.path.isfile(path) else None


def run_job(kind, fn):
    def go():
        try:
            state["result"] = fn()
        except Exception as e:
            traceback.print_exc()
            state["error"] = str(e)
        finally:
            state["running"] = False
    with lock:
        if state["running"]:
            return False
        state.update(running=True, job=kind, progress=None, result=None, error=None)
    threading.Thread(target=go, daemon=True).start()
    return True


def open_folder(folder):
    try:
        if sys.platform == "darwin":
            os.system(f'open "{folder}"')
        elif sys.platform.startswith("win"):
            os.startfile(folder)
        else:
            os.system(f'xdg-open "{folder}" >/dev/null 2>&1 &')
    except Exception:
        pass


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):            # keep the console quiet
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n) if n else b""

    def send_file(self, path, ctype):
        """Serve a file with byte-range support (Safari refuses to play audio without it)."""
        size = os.path.getsize(path)
        start, end = 0, size - 1
        rng = self.headers.get("Range")
        partial = False
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    if m.group(2):
                        end = min(int(m.group(2)), size - 1)
                elif m.group(2):
                    start = max(size - int(m.group(2)), 0)
                partial = True
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-store")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            self.send_file(HTML, "text/html; charset=utf-8")
        elif p == "/api/tracks":
            self.send_json({"tracks": list_tracks(), "folder": TRACKS, "mixes": MIXES,
                            "ffmpeg": engine.ffmpeg_path() is not None, "version": VERSION})
        elif p == "/api/status":
            self.send_json(state)
        elif p == "/api/mixes":
            self.send_json({"mixes": list_mixes()})
        elif p.startswith("/api/mix/"):
            path = mix_path(unquote(p[len("/api/mix/"):]))
            if not os.path.isfile(path):
                return self.send_json({"error": "not found"}, 404)
            self.send_json(json.load(open(path, encoding="utf-8")))
        elif p.startswith("/api/preview/"):
            path = safe_track_path(p[len("/api/preview/"):])
            if not path:
                return self.send_json({"error": "not found"}, 404)
            self.send_file(path, MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream"))
        elif p.startswith("/api/peaks/"):
            path = safe_track_path(p[len("/api/peaks/"):])
            if not path:
                return self.send_json({"error": "not found"}, 404)
            try:
                self.send_json(engine.peaks(path, CACHE))
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        elif p == "/api/audition.wav":
            if not os.path.isfile(AUDITION_WAV):
                return self.send_json({"error": "not found"}, 404)
            self.send_file(AUDITION_WAV, "audio/wav")
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        p = self.path.split("?")[0]
        if p == "/api/render":
            playlist = json.loads(self.read_body())
            ok = run_job("render", lambda: engine.render(playlist, TRACKS, MIXES,
                                                        progress=lambda pr: state.update(progress=pr)))
            self.send_json({"ok": True} if ok else {"error": "Something is already rendering"}, 200 if ok else 409)
        elif p == "/api/audition":
            body = json.loads(self.read_body())
            a, b, norm = body["a"], body["b"], body.get("normalize", True)
            ok = run_job("audition", lambda: engine.audition(a, b, TRACKS, AUDITION_WAV, norm,
                                                            progress=lambda pr: state.update(progress=pr)))
            self.send_json({"ok": True} if ok else {"error": "Something is already rendering"}, 200 if ok else 409)
        elif p == "/api/upload":
            name = os.path.basename(unquote(self.headers.get("X-Filename", "")))
            if not name or not name.lower().endswith(engine.AUDIO_EXT):
                self.read_body()
                return self.send_json({"error": "not an audio file"}, 400)
            dest = os.path.join(TRACKS, name)
            n = int(self.headers.get("Content-Length", 0))
            with open(dest + ".part", "wb") as f:
                left = n
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        break
                    f.write(chunk)
                    left -= len(chunk)
            os.replace(dest + ".part", dest)
            self.send_json({"ok": True, "file": name})
        elif p == "/api/save-mix":
            body = json.loads(self.read_body())
            name = engine.safe_name(body.get("name"))
            pl = body.get("playlist", {})
            pl["saved"] = time.strftime("%Y-%m-%d %H:%M")
            json.dump(pl, open(mix_path(name), "w", encoding="utf-8"), indent=2)
            self.send_json({"ok": True, "name": name})
        elif p == "/api/delete-mix":
            body = json.loads(self.read_body())
            path = mix_path(body.get("name"))
            if os.path.isfile(path):
                os.remove(path)
            self.send_json({"ok": True})
        elif p == "/api/open-folder":
            which = json.loads(self.read_body() or b"{}").get("which", "tracks")
            open_folder(TRACKS if which == "tracks" else MIXES)
            self.send_json({"ok": True})
        elif p == "/api/quit":
            self.send_json({"ok": True})
            threading.Timer(0.3, lambda: os._exit(0)).start()
        else:
            self.send_json({"error": "not found"}, 404)


def main():
    url = f"http://127.0.0.1:{PORT}/"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        # Already running (launcher double-clicked twice) — just bring the browser back.
        print(f"VibeMix is already running — opening {url}")
        webbrowser.open(url)
        return
    server.daemon_threads = True
    print(f"VibeMix {VERSION} running at {url}\nSongs folder: {TRACKS}\nMixes folder: {MIXES}\n(close this window to quit)")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
