# ROOT//X TOOLKIT

**The system toolkit that doesn't mess around.**

A blazing-fast TUI (Terminal User Interface) console for Linux, macOS and Windows —
one place to diagnose, manage, harden and monitor your whole system. 28 modules,
3 license tiers, a live web panel, and a proper CLI that respects your terminal.

`Version 2.0.0`

---

## What it does

Built by people who actually use terminals, ROOT//X packs a full admin workshop
into a single `rootx` command:

- **Diagnose & fix** — catch broken setups, missing tools and junk state in one pass
- **Manage the machine** — processes, services, packages, disks, users, network, ports
- **Harden everything** — firewall rules, debloat & telemetry stripping, autostart
  auditing, SSL/TLS & domain inspection
- **Go deeper** — Docker, backups, full system updates, CPU/RAM/disk benchmarks,
  live resource monitoring and S.M.A.R.T. disk health
- **Have a nice GUI without leaving the box** — built-in Web Panel at `localhost:7070`

Licensing runs on **3 tiers**: **Bronze → Silver → Gold**. Verify online, then enjoy
up to **7 days of offline** use from the cache.

---

## Features

### Accessible to everyone (Bronze)

| # | Module | What it does |
|---|--------|--------------|
| 1 | **ROOT//X DOCTOR** | Automatic diagnosis and repair |
| 2 | **APP INSTALLER** | Install Git, Python, Node, Docker, VS Code and more |
| 3 | **NETWORK CENTER** | Interfaces, doctor, ping, DNS, traceroute, public IP, active connections |
| 4 | **DISK CENTER** | Disk usage, block devices, large-file finder |
| 5 | **PROCESS CENTER** | Sort, search and kill processes |
| 6 | **SERVICE MANAGER** | status / start / stop / restart |
| 7 | **PACKAGE MANAGER** | Update, upgrade, search and install packages |
| 8 | **SYSTEM INFORMATION** | Full hardware & OS spec |
| 9 | **DIAGNOSTIC REPORT** | Export a full diagnostic report |
| 10 | **HASH & PASSWORD GENERATOR** | File hashes, password & API key generation |

### Silver (higher license level)

| # | Module | What it does |
|---|--------|--------------|
| 11 | **FIREWALL CENTER** | Status, rules, add/remove rules |
| 12 | **LOG VIEWER** | System & service logs |
| 13 | **TASK SCHEDULER** | Cron (Linux) & Windows scheduled tasks |
| 14 | **USER MANAGER** | Users & groups, lock/unlock accounts |
| 15 | **ENVIRONMENT MANAGER** | Env vars & PATH |
| 16 | **PORT SCANNER (local)** | Listening ports, connections, port checks |
| 17 | **GIT HELPER** | status, log, commit, pull, push, stash |
| 18 | **DEBLOATER & TELEMETRY STRIPPER** | Kill telemetry and junk services |
| 19 | **AUTOSTART & PERSISTENCE INSPECTOR** | Scan autostart locations |
| 20 | **RAM & CACHE PURGER** | Free memory and cache |
| 21 | **HTTP FILE SHARE & QR CODE** | Share files over HTTP with a QR code |
| 22 | **SSL/TLS & DOMAIN INSPECTOR** | SSL certificates & DNS records |

### Gold (full access)

| # | Module | What it does |
|---|--------|--------------|
| 23 | **DOCKER CENTER** | Containers, images, logs, start/stop/restart, prune |
| 24 | **BACKUP TOOL** | Create, verify and restore backups |
| 25 | **UPDATE CENTER** | Full system update |
| 26 | **BENCHMARK** | CPU / RAM / disk performance tests |
| 27 | **LIVE TUI RESOURCE MONITOR** | Live resource monitor |
| 28 | **DISK HEALTH & S.M.A.R.T. MONITOR** | Drive health monitoring |

### Extras

- **Web Panel** — `localhost:7070` for a browser-based management surface
- **Themes** — Cyberpunk Cyan, Matrix Green, Crimson Red, Deep Purple, Monochrome Minimal
- **Languages** — English & Polski (pick on first launch)

---

## License tiers

| Tier | Access |
|------|--------|
| **Bronze** | Core diagnostic modules |
| **Silver** | System & security modules |
| **Gold** | Full access incl. Docker, Backup, Benchmark |

License verification is online; once activated it also works offline with a
cache validity of up to 7 days.

---

## Installation

### Linux / macOS

```bash
git clone https://github.com/root-xx-dc/ToolKit.git
cd ToolKit
chmod +x install_unix.sh
./install_unix.sh
```

The script automatically:
- Checks for Python 3.10+
- Installs the package via pip
- Adds `rootx` to your PATH
- Creates a desktop shortcut

### Windows

1. Download the repository
2. Run `install_windows.bat` **as administrator** (right-click → Run as administrator)
3. The `RootX-Toolkit` shortcut appears on your desktop

---

## Usage

```bash
rootx          # after installation
```

or double-click the desktop shortcut. On first launch you pick your language
(PL/EN), then enter your license key.

---

## Requirements

- Python 3.10+
- pip
- `psutil >= 5.9.0`

---

## Project structure

```
rootx/
├── cli.py          # Main TUI & menu
├── _config.py      # Configuration (compiled via Cython)
├── license.py      # License system (compiled via Cython)
├── lang/           # Translations (pl.py / en.py)
├── webpanel/       # Web Panel server
└── modules.py      # Individual feature modules
```

`_config` and `license` ship as compiled extensions (`.so` / `.pyd`) to protect
the licensing logic from tampering.

Protected builds are produced with `build_protected.py` and automated via
GitHub Actions (`.github/workflows/build-protected.yml`).

---

## License

Get a license key through Discord — without a key, ROOT//X won't start.

---

*ROOT//X TOOLKIT © 2024 — 11wiks & Szefuncio_xx*
