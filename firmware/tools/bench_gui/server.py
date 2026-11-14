"""Kleiner Webserver der Oberfläche: liefert die Seite aus, nimmt Befehle an, schickt Ereignisse.

Nur Standardbibliothek. Der Server lauscht ausschließlich auf 127.0.0.1. Jede Anfrage braucht das
Sitzungs-Token, das beim Start erzeugt und in die Seite geschrieben wird: eine fremde Webseite im
selben Browser kann die Platine damit nicht ansprechen (auf der Konsole gibt es Servo- und Pyro-Befehle).

    GET  /                 Seite (static/index.html, Token eingesetzt)
    GET  /static/<datei>   app.js, style.css
    GET  /events?token=    Server-Sent Events: state, line, test, done, data, capture
    POST /api/<aktion>     JSON, Kopfzeile X-Token; Antwort {"ok": true, ...} oder {"ok": false, "error": "..."}
"""
import json
import queue
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .link import BoardLink, Hub

STATIC = Path(__file__).resolve().parent / "static"
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".svg": "image/svg+xml"}


class App:
    def __init__(self, report_dir):
        self.hub = Hub()
        self.link = BoardLink(self.hub, report_dir)
        self.token = secrets.token_urlsafe(24)

    # Aktionen der Oberfläche: Name -> Funktion(body) -> dict
    def api(self, action, body):
        link = self.link
        if action == "ports":
            return {"ports": link.list_ports()}
        if action == "state":
            return {"state": link.state()}
        if action == "connect":
            link.connect(str(body.get("port", "")))
        elif action == "disconnect":
            link.disconnect()
        elif action == "cmd":
            link.send_command(str(body.get("cmd", "")))
        elif action == "answer":
            link.answer(str(body.get("text", "")))
        elif action == "abort":
            link.abort()
        elif action == "stream":
            link.set_stream(bool(body.get("on", True)), body.get("hz"))
        elif action == "sim_motion":
            link.set_sim_motion(str(body.get("mode", "ruhe")))
        elif action == "capture_start":
            link.capture_start(str(body.get("kind", "")))
        elif action == "capture_stop":
            link.capture_stop()
        elif action == "capture_fit":
            return {"fit": link.capture_fit()}
        elif action == "capture_apply":
            return {"commands": link.capture_apply()}
        elif action == "record":
            return {"path": link.record(bool(body.get("on", True)))}
        elif action == "report":
            return {"path": link.write_report()}
        else:
            raise KeyError(action)
        return {}


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):       # keine Zugriffszeilen im Terminal
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _local(self):
            """Nur Anfragen, die an diese Adresse gerichtet sind (kein DNS-Rebinding)."""
            host = (self.headers.get("Host") or "").split(":")[0]
            return host in ("127.0.0.1", "localhost")

        def do_GET(self):
            url = urlparse(self.path)
            if not self._local():
                return self._send(403, {"ok": False, "error": "nur lokal"})
            if url.path == "/":
                html = (STATIC / "index.html").read_text(encoding="utf-8").replace("{{TOKEN}}", app.token)
                return self._send(200, html.encode("utf-8"), MIME[".html"])
            if url.path.startswith("/static/"):
                f = (STATIC / url.path[len("/static/"):]).resolve()
                if STATIC not in f.parents or not f.is_file() or f.suffix not in MIME:
                    return self._send(404, {"ok": False, "error": "nicht gefunden"})
                return self._send(200, f.read_bytes(), MIME[f.suffix])
            if url.path == "/events":
                if parse_qs(url.query).get("token", [""])[0] != app.token:
                    return self._send(403, {"ok": False, "error": "Token fehlt"})
                return self._events()
            self._send(404, {"ok": False, "error": "nicht gefunden"})

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = app.hub.subscribe()
            try:
                self._event({"type": "state", "state": app.link.state()})
                while True:
                    try:
                        ev = q.get(timeout=10.0)
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")      # hält die Verbindung offen, erkennt ein geschlossenes Fenster
                        self.wfile.flush()
                        continue
                    self._event(ev)
            except (BrokenPipeError, ConnectionError, OSError):
                pass
            finally:
                app.hub.unsubscribe(q)

        def _event(self, ev):
            self.wfile.write(b"data: " + json.dumps(ev, ensure_ascii=False).encode("utf-8") + b"\n\n")
            self.wfile.flush()

        def do_POST(self):
            url = urlparse(self.path)
            if not self._local() or not url.path.startswith("/api/"):
                return self._send(403, {"ok": False, "error": "nur lokal"})
            if not secrets.compare_digest(self.headers.get("X-Token") or "", app.token):
                return self._send(403, {"ok": False, "error": "Token fehlt"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}") if n else {}
                out = app.api(url.path[len("/api/"):], body if isinstance(body, dict) else {})
                self._send(200, {"ok": True, **out})
            except KeyError:
                self._send(404, {"ok": False, "error": "unbekannte Aktion"})
            except Exception as e:               # Fehler als Text an die Oberfläche, nicht als Absturz
                self._send(200, {"ok": False, "error": str(e)})

    return Handler


def serve(app, http_port=8765):
    """Server starten; nimmt den nächsten freien Port ab http_port. Liefert (server, url)."""
    last = None
    for port in range(http_port, http_port + 20):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
            break
        except OSError as e:
            last = e
    else:
        raise last
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True, name="http").start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/"
