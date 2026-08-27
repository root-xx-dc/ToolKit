"""
rootx.webpanel.server
=====================
HTTP server for ROOT//X web panel.
Binds to 127.0.0.1 only. Token-authenticated sessions.
"""
from __future__ import annotations

import json
import os
import platform
import secrets
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional, Set
from urllib.parse import parse_qs, urlparse

# ─── Session management ───────────────────────────────────────────────────────

_valid_tokens: Set[str] = set()
_sessions: Set[str] = set()  # authenticated session tokens


def generate_session_token() -> str:
    token = secrets.token_urlsafe(32)
    _valid_tokens.add(token)
    return token


def _is_authenticated(token: str) -> bool:
    return token in _sessions


def _try_authenticate(token: str) -> bool:
    if token in _valid_tokens or token in _sessions:
        _sessions.add(token)
        return True
    return False


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_token_from_request(handler: "RootXHandler") -> Optional[str]:
    # Check Authorization header
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    # Check query string
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    if "token" in params:
        return params["token"][0]
    # Check cookie
    cookie = handler.headers.get("Cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("rxtoken="):
            return part[8:]
    return None


def _live_stats() -> Dict[str, Any]:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.2)
        vm = psutil.virtual_memory()
        net = psutil.net_io_counters()
        return {
            "cpu_percent": round(cpu, 1),
            "ram_used_mb": round(vm.used / 1024 / 1024, 1),
            "ram_total_mb": round(vm.total / 1024 / 1024, 1),
            "ram_percent": round(vm.percent, 1),
            "net_rx_mb": round(net.bytes_recv / 1024 / 1024, 2),
            "net_tx_mb": round(net.bytes_sent / 1024 / 1024, 2),
        }
    except ImportError:
        return {"error": "psutil not available"}


def _processes_list() -> List[Dict]:
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = p.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"] or "",
                    "cpu": round(info["cpu_percent"] or 0, 1),
                    "mem": round(info["memory_percent"] or 0, 2),
                    "status": info["status"] or "",
                })
            except Exception:
                pass
        procs.sort(key=lambda x: x["cpu"], reverse=True)
        return procs[:20]
    except ImportError:
        return []


def _disks_list() -> List[Dict]:
    try:
        import psutil
        result = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                result.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / 1024 ** 3, 2),
                    "used_gb": round(usage.used / 1024 ** 3, 2),
                    "free_gb": round(usage.free / 1024 ** 3, 2),
                    "percent": usage.percent,
                })
            except Exception:
                pass
        return result
    except ImportError:
        return []


def _status_info(tier: str = "unknown") -> Dict[str, str]:
    return {
        "version": "2.0.0",
        "tier": tier,
        "os": platform.system(),
        "os_version": platform.version(),
        "arch": platform.machine(),
        "hostname": socket.gethostname(),
        "python": sys.version.split()[0],
    }


# ─── HTML Template ────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ROOT//X TOOLKIT - Web Panel</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #000000;
  --bg-card: #080808;
  --border: #222222;
  --border-focus: #00e5ff;
  --text: #aaaaaa;
  --text-bright: #ffffff;
  --text-dim: #444444;
  --accent: #00e5ff;
  --accent-dim: #008899;
  --green: #00ff00;
  --red: #ff0000;
  --yellow: #ffff00;
  --font: 'SF Mono', 'Fira Code', Consolas, Monaco, monospace;
}

body { background: var(--bg); color: var(--text); font-family: var(--font); font-size: 12px; line-height: 1.5; min-height: 100vh; }

input, button, table, td, th { font-family: var(--font); font-size: 12px; }

/* Sharp Flat Elements */
.login-card, input, button, .card, .progress-wrap, .progress-bar, table, th, td, .badge, .info-row, .sidebar, .sidebar-logo, .nav-item, .stop-btn {
  border-radius: 0px !important;
}

/* ── Login ── */
#login-screen {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; padding: 20px;
}
.login-card {
  background: var(--bg-card); border: 1px solid var(--border);
  padding: 35px; width: 100%; max-width: 400px;
}
.login-card h1 { font-size: 13px; color: var(--text-bright); letter-spacing: 2px; margin-bottom: 5px; text-transform: uppercase; }
.login-card p { color: var(--text-dim); font-size: 11px; margin-bottom: 25px; text-transform: uppercase; }
.login-card input {
  width: 100%; background: var(--bg); border: 1px solid var(--border);
  padding: 10px 12px; color: var(--text-bright); outline: none;
}
.login-card input:focus { border-color: var(--border-focus); }
.login-card button {
  margin-top: 15px; width: 100%; padding: 11px;
  background: var(--border); color: var(--text-bright); font-weight: 700;
  border: 1px solid var(--border); cursor: pointer;
  letter-spacing: 1px; text-transform: uppercase;
}
.login-card button:hover { background: var(--accent); color: #000; border-color: var(--accent); }
.login-error { color: var(--red); font-size: 11px; margin-top: 10px; text-transform: uppercase; }

/* ── App layout ── */
#app { display: none; height: 100vh; overflow: hidden; }
.layout { display: flex; height: 100%; }

/* ── Sidebar ── */
.sidebar {
  width: 220px; flex-shrink: 0; background: var(--bg-card);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow-y: auto;
}
.sidebar-logo {
  padding: 20px;
  border-bottom: 1px solid var(--border);
}
.sidebar-logo .brand { color: var(--text-bright); font-weight: 700; font-size: 12px; letter-spacing: 2px; text-transform: uppercase; }
.sidebar-logo .sub { color: var(--text-dim); font-size: 10px; margin-top: 2px; text-transform: uppercase; }

.nav { flex: 1; padding: 10px 0; }
.nav-item {
  display: block; width: 100%; text-align: left; background: none;
  border: none; cursor: pointer; padding: 10px 20px; color: var(--text);
  letter-spacing: 0.5px; text-transform: uppercase;
  border-left: 2px solid transparent;
}
.nav-item:hover { color: var(--text-bright); background: var(--bg); }
.nav-item.active { color: var(--accent); border-left-color: var(--accent); background: var(--bg); }

.sidebar-footer {
  padding: 15px 20px; border-top: 1px solid var(--border);
  font-size: 11px; color: var(--text-dim); text-transform: uppercase;
}
.stop-btn {
  display: block; width: 100%; margin-top: 10px; padding: 8px;
  background: none; border: 1px solid var(--red); color: var(--red);
  cursor: pointer; font-size: 11px; text-transform: uppercase;
}
.stop-btn:hover { background: rgba(255,0,0,.15); }

/* ── Main content ── */
.main { flex: 1; overflow-y: auto; padding: 25px; }

.page { display: none; }
.page.active { display: block; }

h2 { font-size: 12px; letter-spacing: 1.5px; color: var(--text-bright); margin-bottom: 20px; text-transform: uppercase; }

/* ── Stat cards ── */
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }
.card {
  background: var(--bg-card); border: 1px solid var(--border); padding: 15px 20px;
}
.card-label { font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
.card-value { font-size: 20px; font-weight: 700; color: var(--accent); }
.card-sub { font-size: 11px; color: var(--text-dim); margin-top: 4px; }

/* Progress bar */
.progress-wrap { background: var(--bg); border: 1px solid var(--border); height: 8px; margin-top: 10px; overflow: hidden; }
.progress-bar { height: 100%; background: var(--accent); width: 0%; }
.progress-bar.warn { background: var(--yellow); }
.progress-bar.crit { background: var(--red); }

/* ── Tables ── */
.table-wrap { background: var(--bg-card); border: 1px solid var(--border); }
table { width: 100%; border-collapse: collapse; }
th {
  text-align: left; padding: 8px 12px;
  background: var(--bg); color: var(--text-bright);
  font-weight: 700; font-size: 11px; text-transform: uppercase;
  border-bottom: 1px solid var(--border);
}
td { padding: 8px 12px; border-bottom: 1px solid var(--border); color: var(--text); }
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--bg); }

.badge {
  display: inline-block; padding: 2px 6px; border: 1px solid var(--border);
  font-size: 10px; font-weight: 700; text-transform: uppercase;
}
.badge-green { border-color: var(--green); color: var(--green); }
.badge-red { border-color: var(--red); color: var(--red); }
.badge-yellow { border-color: var(--yellow); color: var(--yellow); }
.badge-dim { border-color: var(--text-dim); color: var(--text-dim); }

/* ── Info grid ── */
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.info-row { background: var(--bg-card); border: 1px solid var(--border); padding: 12px 15px; }
.info-key { font-size: 10px; color: var(--text-dim); text-transform: uppercase; }
.info-val { font-size: 12px; margin-top: 4px; color: var(--text-bright); }

/* ── Responsive ── */
@media (max-width: 640px) {
  .sidebar { width: 180px; }
  .info-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<!-- Login screen -->
<div id="login-screen">
  <div class="login-card">
    <h1>ROOT//X SECURITY GATE</h1>
    <p>ENTER SESSION SECURITY TOKEN TO AUTHENTICATE</p>
    <input type="text" id="token-input" placeholder="Session token" autocomplete="off" spellcheck="false">
    <button onclick="doLogin()">AUTHENTICATE</button>
    <div class="login-error" id="login-err"></div>
  </div>
</div>

<!-- Main app -->
<div id="app">
  <div class="layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-logo">
        <div class="brand">ROOT//X SYSTEM</div>
        <div class="sub">CONSOLE PORTAL v2.0.0</div>
      </div>
      <nav class="nav">
        <button class="nav-item active" onclick="showPage('dashboard')">DASHBOARD</button>
        <button class="nav-item" onclick="showPage('processes')">PROCESSES</button>
        <button class="nav-item" onclick="showPage('disks')">DISK STORAGE</button>
        <button class="nav-item" onclick="showPage('system')">SYSTEM INFO</button>
      </nav>
      <div class="sidebar-footer">
        <div id="tier-badge">TIER: --</div>
        <button class="stop-btn" onclick="stopPanel()">SHUTDOWN PANEL</button>
      </div>
    </aside>

    <!-- Content -->
    <main class="main">

      <!-- Dashboard -->
      <div class="page active" id="page-dashboard">
        <h2>DASHBOARD OVERVIEW</h2>
        <div class="cards">
          <div class="card">
            <div class="card-label">CPU CORE LOAD</div>
            <div class="card-value" id="cpu-val">--</div>
            <div class="progress-wrap"><div class="progress-bar" id="cpu-bar"></div></div>
          </div>
          <div class="card">
            <div class="card-label">RAM MEMORY</div>
            <div class="card-value" id="ram-val">--</div>
            <div class="card-sub" id="ram-sub">-- / -- MB</div>
            <div class="progress-wrap"><div class="progress-bar" id="ram-bar"></div></div>
          </div>
          <div class="card">
            <div class="card-label">NETWORK TRAFFIC RX</div>
            <div class="card-value" id="net-rx">--</div>
            <div class="card-sub">TOTAL DOWNLOADED DATA</div>
          </div>
          <div class="card">
            <div class="card-label">NETWORK TRAFFIC TX</div>
            <div class="card-value" id="net-tx">--</div>
            <div class="card-sub">TOTAL UPLOADED DATA</div>
          </div>
        </div>
      </div>

      <!-- Processes -->
      <div class="page" id="page-processes">
        <h2>PROCESS LIST</h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>PID</th><th>PROCESS NAME</th><th>CPU %</th><th>MEM %</th><th>STATUS</th></tr></thead>
            <tbody id="proc-body"></tbody>
          </table>
        </div>
      </div>

      <!-- Disks -->
      <div class="page" id="page-disks">
        <h2>DISK STORAGE PARTITIONS</h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>DEVICE</th><th>MOUNT POINT</th><th>FILESYSTEM</th><th>TOTAL CAPACITY</th><th>USED CAPACITY</th><th>FREE SPACE</th><th>USED %</th></tr></thead>
            <tbody id="disk-body"></tbody>
          </table>
        </div>
      </div>

      <!-- System Info -->
      <div class="page" id="page-system">
        <h2>SYSTEM INFORMATION DATA</h2>
        <div class="info-grid" id="sys-grid"></div>
      </div>

    </main>
  </div>
</div>

<script>
let SESSION_TOKEN = '';
let liveInterval = null;

// DO NOT check url query params to force entering token in the security gate
// This ensures the page always prompts for the session token!

async function doLogin() {
  const input = document.getElementById('token-input').value.trim();
  const ok = await checkToken(input);
  if (ok) {
    SESSION_TOKEN = input;
    showApp();
  } else {
    document.getElementById('login-err').textContent = 'AUTHENTICATION FAILED: INVALID TOKEN';
  }
}

async function checkToken(token) {
  try {
    const resp = await fetch('/api/status', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    return resp.ok;
  } catch { return false; }
}

function showApp() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').style.display = 'flex';
  loadStatus();
  loadDisks();
  loadProcesses();
  startLive();
}

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  event.target.classList.add('active');
  if (name === 'processes') loadProcesses();
  if (name === 'disks') loadDisks();
  if (name === 'system') loadStatus();
}

async function api(endpoint) {
  try {
    const resp = await fetch(endpoint, {
      headers: { 'Authorization': 'Bearer ' + SESSION_TOKEN }
    });
    if (!resp.ok) return null;
    return resp.json();
  } catch { return null; }
}

function fmtMB(mb) {
  if (mb >= 1024) return (mb / 1024).toFixed(2) + ' GB';
  return mb.toFixed(0) + ' MB';
}

function startLive() {
  updateLive();
  liveInterval = setInterval(updateLive, 2000);
}

async function updateLive() {
  const d = await api('/api/live');
  if (!d) return;

  document.getElementById('cpu-val').textContent = d.cpu_percent + '%';
  const cpuBar = document.getElementById('cpu-bar');
  cpuBar.style.width = d.cpu_percent + '%';
  cpuBar.className = 'progress-bar' + (d.cpu_percent > 85 ? ' crit' : d.cpu_percent > 60 ? ' warn' : '');

  document.getElementById('ram-val').textContent = d.ram_percent + '%';
  document.getElementById('ram-sub').textContent = fmtMB(d.ram_used_mb) + ' / ' + fmtMB(d.ram_total_mb);
  const ramBar = document.getElementById('ram-bar');
  ramBar.style.width = d.ram_percent + '%';
  ramBar.className = 'progress-bar' + (d.ram_percent > 85 ? ' crit' : d.ram_percent > 60 ? ' warn' : '');

  document.getElementById('net-rx').textContent = fmtMB(d.net_rx_mb);
  document.getElementById('net-tx').textContent = fmtMB(d.net_tx_mb);
}

async function loadProcesses() {
  const procs = await api('/api/processes');
  if (!procs) return;
  const tbody = document.getElementById('proc-body');
  tbody.innerHTML = procs.map(p => {
    const badge = p.status === 'running' ? 'badge-green' : 'badge-dim';
    return '<tr>' +
      '<td>' + p.pid + '</td>' +
      '<td>' + p.name + '</td>' +
      '<td>' + p.cpu + '%</td>' +
      '<td>' + p.mem + '%</td>' +
      '<td><span class="badge ' + badge + '">' + p.status + '</span></td>' +
      '</tr>';
  }).join('');
}

async function loadDisks() {
  const disks = await api('/api/disks');
  if (!disks) return;
  const tbody = document.getElementById('disk-body');
  tbody.innerHTML = disks.map(d => {
    const cls = d.percent > 90 ? 'badge-red' : d.percent > 70 ? 'badge-yellow' : 'badge-green';
    return '<tr>' +
      '<td>' + d.device + '</td>' +
      '<td>' + d.mountpoint + '</td>' +
      '<td>' + d.fstype + '</td>' +
      '<td>' + d.total_gb + ' GB</td>' +
      '<td>' + d.used_gb + ' GB</td>' +
      '<td>' + d.free_gb + ' GB</td>' +
      '<td><span class="badge ' + cls + '">' + d.percent + '%</span></td>' +
      '</tr>';
  }).join('');
}

async function loadStatus() {
  const d = await api('/api/status');
  if (!d) return;
  document.getElementById('tier-badge').textContent = 'TIER: ' + (d.tier || '--').toUpperCase();
  const grid = document.getElementById('sys-grid');
  const fields = [
    ['VERSION', d.version], ['TIER LEVEL', d.tier],
    ['OPERATING SYSTEM', d.os], ['OS VERSION', d.os_version],
    ['ARCHITECTURE', d.arch], ['HOSTNAME', d.hostname],
    ['PYTHON RUNTIME', d.python],
  ];
  grid.innerHTML = fields.map(([k, v]) =>
    '<div class="info-row"><div class="info-key">' + k + '</div><div class="info-val">' + (v || '--') + '</div></div>'
  ).join('');
}

async function stopPanel() {
  if (!confirm('SHUTDOWN THE ROOT//X WEB PANEL SERVER?')) return;
  try {
    await fetch('/api/stop', { method: 'POST', headers: { 'Authorization': 'Bearer ' + SESSION_TOKEN } });
  } catch {}
  document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;color:#333;font-family:monospace;font-size:11px;background:#000;">PORTAL SHUTDOWN COMPLETE. SESSION TERMINATED.</div>';
  clearInterval(liveInterval);
}
</script>
</body>
</html>
"""


# ─── Request Handler ──────────────────────────────────────────────────────────

class RootXHandler(BaseHTTPRequestHandler):
    tier: str = "unknown"
    _stop_flag: threading.Event = None

    def log_message(self, fmt: str, *args) -> None:
        pass  # Suppress request logs

    def _json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, content: str, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _unauthorized(self) -> None:
        self._json({"error": "Unauthorized"}, 401)

    def _token_from_req(self) -> Optional[str]:
        return _get_token_from_request(self)

    def _authenticated(self) -> bool:
        token = self._token_from_req()
        if token is None:
            return False
        return _is_authenticated(token) or _try_authenticate(token)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            # Try to authenticate from URL token
            token = self._token_from_req()
            if token:
                _try_authenticate(token)
            self._html(HTML_TEMPLATE)
            return

        # All API routes require authentication
        if not self._authenticated():
            self._unauthorized()
            return

        if path == "/api/status":
            self._json(_status_info(RootXHandler.tier))
        elif path == "/api/live":
            self._json(_live_stats())
        elif path == "/api/processes":
            self._json(_processes_list())
        elif path == "/api/disks":
            self._json(_disks_list())
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        if not self._authenticated():
            self._unauthorized()
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/stop":
            self._json({"ok": True, "message": "Stopping panel..."})
            if RootXHandler._stop_flag:
                threading.Thread(target=RootXHandler._stop_flag.set, daemon=True).start()
        else:
            self._json({"error": "Not found"}, 404)


# ─── Server class ─────────────────────────────────────────────────────────────

class WebPanelServer:
    """
    Localhost web panel server.

    Usage:
        server = WebPanelServer(port=7070)
        url = server.start()
        # url = "http://127.0.0.1:7070/?token=..."
        server.stop()
    """

    def __init__(self, port: int = 7070, tier: str = "unknown") -> None:
        self.port = port
        self.tier = tier
        self.token = generate_session_token()
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.url = f"http://127.0.0.1:{self.port}"

    def start(self) -> str:
        """Start server in background thread. Returns full URL with token."""
        RootXHandler.tier = self.tier
        RootXHandler._stop_flag = self._stop_event

        self._server = HTTPServer(("127.0.0.1", self.port), RootXHandler)
        self._thread = threading.Thread(target=self._serve_until_stop, daemon=True)
        self._thread.start()

        # Start stop-watcher thread
        threading.Thread(target=self._watch_stop, daemon=True).start()

        return self.url

    def _serve_until_stop(self) -> None:
        try:
            self._server.serve_forever()
        except Exception:
            pass

    def _watch_stop(self) -> None:
        self._stop_event.wait()
        time.sleep(0.3)
        self.stop()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None

    def is_running(self) -> bool:
        return self._server is not None
