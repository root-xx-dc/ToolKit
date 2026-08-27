"""
rootx.fileshare
===============
HTTP Local File Share + ASCII QR Code.
Serves a file or directory over LAN via built-in http.server.
Generates QR code in terminal (uses 'qrcode' if installed, else text fallback).
"""
from __future__ import annotations

import http.server
import os
import socket
import threading
from pathlib import Path
from typing import Optional, Tuple


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _find_free_port(start: int = 8700, end: int = 8800) -> int:
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    return 8700


def render_qr_ascii(data: str) -> str:
    """Render QR code as ASCII block art. Falls back to text if qrcode not installed."""
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(data)
        qr.make(fit=True)
        lines = []
        for row in qr.modules:
            line = "".join("\u2588\u2588" if cell else "  " for cell in row)
            lines.append("  " + line)
        return "\n".join(lines)
    except ImportError:
        lines = [
            f"  URL: {data}",
            "",
            "  Scan this URL with your phone or install 'qrcode' for QR:",
            "  pip install qrcode",
        ]
        return "\n".join(lines)


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler with suppressed logging."""

    def log_message(self, fmt: str, *args) -> None:
        pass  # Silence access logs in terminal

    def log_error(self, fmt: str, *args) -> None:
        pass


class FileShareServer:
    """
    HTTP file share server.

    Usage:
        server = FileShareServer("/path/to/dir_or_file")
        url, port = server.start()
        print(f"Sharing at {url}")
        server.stop()
    """

    def __init__(self, path: str, port: int = 0) -> None:
        self.path = Path(path).resolve()
        self._requested_port = port
        self._server: Optional[http.server.HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._port: int = 0
        self._local_ip: str = _get_local_ip()

    def start(self) -> Tuple[str, int]:
        """Start server in a background thread. Returns (local_ip, port)."""
        port = self._requested_port or _find_free_port()

        # If sharing a single file, serve its parent directory
        if self.path.is_file():
            serve_dir = str(self.path.parent)
        else:
            serve_dir = str(self.path)

        os.chdir(serve_dir)

        handler = _SilentHandler
        self._server = http.server.HTTPServer(("", port), handler)
        self._port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self._local_ip, self._port

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None

    def is_running(self) -> bool:
        return self._server is not None

    def get_share_url(self) -> str:
        if self.path.is_file():
            return f"http://{self._local_ip}:{self._port}/{self.path.name}"
        return f"http://{self._local_ip}:{self._port}/"


def share_path(path: str, port: int = 0) -> FileShareServer:
    """Create and start a FileShareServer for the given path."""
    server = FileShareServer(path, port)
    server.start()
    return server
