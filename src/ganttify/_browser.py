"""Deliver browser previews over loopback without temporary-file lifetime races."""

from __future__ import annotations

import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer
from threading import Event, Thread
from uuid import uuid4


class _PreviewServer(ThreadingHTTPServer):
    """Bind a loopback preview without an unnecessary reverse-DNS lookup."""

    def server_bind(self) -> None:
        TCPServer.server_bind(self)
        self.server_name = "127.0.0.1"
        self.server_port = self.server_address[1]


def open_html_in_browser(html: str, *, timeout: float = 30.0) -> None:
    """Keep the preview available until a browser receives its HTML.

    The server binds only to loopback, serves one generated page, and closes
    after delivery or a launch/connection failure. No preview files are created.
    """
    payload = html.encode("utf-8")
    route = "/" + uuid4().hex
    delivered = Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != route:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(payload)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            delivered.set()

        def log_message(self, format: str, *args: object) -> None:
            pass

    with _PreviewServer(("127.0.0.1", 0), Handler) as server:
        server.daemon_threads = True
        worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        worker.start()
        url = f"http://127.0.0.1:{server.server_port}{route}"
        try:
            try:
                opened = webbrowser.open(url)
            except webbrowser.Error as exc:
                raise RuntimeError(
                    "Unable to launch a browser; save the chart with write_html() instead"
                ) from exc
            if not opened:
                raise RuntimeError(
                    "Unable to launch a browser; save the chart with write_html() instead"
                )
            if not delivered.wait(timeout):
                raise TimeoutError(
                    f"The browser did not load the chart within {timeout:g} seconds; "
                    "save the chart with write_html() instead"
                )
        finally:
            server.shutdown()
            worker.join()
