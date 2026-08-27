"""
rootx.self_updater
==================
Auto-update system for ROOT//X TOOLKIT.
Checks GitHub repository (root-xx-dc/ToolKit) for updates on startup,
prompts the user, and automatically pulls/applies updates with automatic restart.
"""

from __future__ import annotations

import io
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import utils

GITHUB_API_COMMITS = "https://api.github.com/repos/root-xx-dc/ToolKit/commits/main"
GITHUB_ZIP_URL = "https://github.com/root-xx-dc/ToolKit/archive/refs/heads/main.zip"
UPDATE_TIMEOUT = 3.5


def _get_project_root() -> Path:
    """Returns the root directory of the Toolkit project (containing setup.py)."""
    return Path(__file__).resolve().parent.parent


def get_local_commit() -> Optional[str]:
    """Returns local git commit hash (short) or None if not a git repository."""
    try:
        root = _get_project_root()
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return None


def fetch_remote_info() -> Optional[Dict[str, Any]]:
    """Fetches latest commit metadata from GitHub repository API."""
    try:
        req = urllib.request.Request(
            GITHUB_API_COMMITS,
            headers={
                "User-Agent": "ROOTX-TOOLKIT-UPDATER",
                "Accept": "application/vnd.github.v3+json",
                "Cache-Control": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=UPDATE_TIMEOUT) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                sha = data.get("sha", "")
                commit_msg = data.get("commit", {}).get("message", "").splitlines()[0]
                return {
                    "sha": sha,
                    "short_sha": sha[:7] if sha else "",
                    "message": commit_msg,
                    "author": data.get("commit", {}).get("author", {}).get("name", ""),
                    "date": data.get("commit", {}).get("author", {}).get("date", ""),
                }
    except Exception:
        pass
    return None


def check_for_updates() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Checks if a newer commit/version is available on GitHub.
    Returns: (is_update_available, remote_info_dict)
    """
    remote_info = fetch_remote_info()
    if not remote_info:
        return False, None

    local_commit = get_local_commit()
    if local_commit:
        # If in a git repo, compare commit SHAs
        remote_short = remote_info.get("short_sha", "")
        if remote_short and local_commit != remote_short:
            return True, remote_info
        return False, remote_info

    # If not a git clone, check saved commit timestamp/hash
    state_file = _get_project_root() / ".last_commit"
    last_saved = ""
    if state_file.exists():
        try:
            last_saved = state_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    remote_sha = remote_info.get("sha", "")
    if remote_sha and last_saved and last_saved != remote_sha:
        return True, remote_info

    return False, remote_info


def apply_update() -> Tuple[bool, str]:
    """
    Pulls and applies the update from GitHub.
    Returns (success, message).
    """
    root = _get_project_root()
    is_git = (root / ".git").exists()

    if is_git:
        # 1. Update via Git
        try:
            fetch_res = subprocess.run(
                ["git", "pull", "--ff-only", "origin", "main"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if fetch_res.returncode != 0:
                # If fast-forward fails, try reset
                reset_res = subprocess.run(
                    ["git", "fetch", "origin", "main"],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if reset_res.returncode == 0:
                    subprocess.run(
                        ["git", "reset", "--hard", "origin/main"],
                        cwd=str(root),
                        capture_output=True,
                        timeout=15,
                    )
                else:
                    return False, f"Git pull failed: {fetch_res.stderr.strip() or fetch_res.stdout.strip()}"
        except Exception as exc:
            return False, f"Git error: {exc}"
    else:
        # 2. Update via ZIP download
        try:
            req = urllib.request.Request(
                GITHUB_ZIP_URL,
                headers={"User-Agent": "ROOTX-TOOLKIT-UPDATER"},
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                zip_bytes = resp.read()

            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                # Top folder in zip is usually 'ToolKit-main'
                names = zf.namelist()
                top_dir = names[0].split("/")[0] if names else ""

                for member in zf.infolist():
                    if member.filename.endswith("/"):
                        continue
                    # Strip top directory name
                    rel_path = member.filename
                    if top_dir and rel_path.startswith(top_dir + "/"):
                        rel_path = rel_path[len(top_dir) + 1 :]
                    if not rel_path:
                        continue

                    dest_path = root / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(dest_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        except Exception as exc:
            return False, f"Download error: {exc}"

    # 3. Save commit hash if available
    remote = fetch_remote_info()
    if remote and remote.get("sha"):
        try:
            (root / ".last_commit").write_text(remote["sha"], encoding="utf-8")
        except Exception:
            pass

    # 4. Rebuild protected modules if build_protected.py is present
    build_script = root / "build_protected.py"
    if build_script.exists():
        try:
            subprocess.run(
                [sys.executable, str(build_script)],
                cwd=str(root),
                capture_output=True,
                timeout=30,
            )
        except Exception:
            pass

    # 5. Reinstall editable package
    try:
        install_cmd = [sys.executable, "-m", "pip", "install", "-e", str(root), "--quiet"]
        if platform.system() != "Windows":
            # Add --break-system-packages for modern Linux
            test_res = subprocess.run(install_cmd, capture_output=True, timeout=30)
            if test_res.returncode != 0:
                subprocess.run(install_cmd + ["--break-system-packages"], capture_output=True, timeout=30)
        else:
            subprocess.run(install_cmd, capture_output=True, timeout=30)
    except Exception:
        pass

    return True, "Update applied successfully."


def restart_toolkit() -> None:
    """Restarts the running Toolkit process."""
    root = _get_project_root()
    if platform.system() == "Windows":
        # Launch new process and exit current
        subprocess.Popen([sys.executable, "-m", "rootx"], cwd=str(root))
        sys.exit(0)
    else:
        # Replace process on Linux/macOS
        os.execv(sys.executable, [sys.executable, "-m", "rootx"])


def check_and_prompt_update(C: Any, T: Dict[str, str]) -> bool:
    """
    Startup hook: Checks for updates and prompts user if available.
    Returns True if update was performed (and process is restarting), False otherwise.
    """
    has_update, info = check_for_updates()
    if not has_update or not info:
        return False

    short_sha = info.get("short_sha", "latest")
    msg = info.get("message", "")
    author = info.get("author", "")

    print(f"\n  {C.YELLOW}{'═' * 50}{C.RESET}")
    print(f"  {C.BOLD}{C.YELLOW}  {T.get('update_available_title', 'UPDATE AVAILABLE')}{C.RESET}")
    print(f"  {C.YELLOW}{'═' * 50}{C.RESET}")
    print(f"  {C.WHITE}  {T.get('update_available_msg', 'A new update is available on GitHub!')}{C.RESET}")
    print(f"  {C.CYAN}  Commit: {C.BOLD}[{short_sha}]{C.RESET} - {msg}")
    if author:
        print(f"  {C.DIM}  Author: {author}{C.RESET}")
    print(f"  {C.YELLOW}{'═' * 50}{C.RESET}\n")

    prompt_txt = T.get("update_prompt", "Do you want to update now? [y/N]")
    try:
        choice = input(f"  {C.BOLD}{prompt_txt}:{C.RESET} ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return False

    if choice in ("y", "yes", "t", "tak"):
        print(f"\n  {C.CYAN}[*] {T.get('update_downloading', 'Downloading and applying update from GitHub...')}{C.RESET}")
        ok, error_msg = apply_update()
        if ok:
            print(f"  {C.GREEN}✓ {T.get('update_success', 'Update installed successfully! Restarting...')}{C.RESET}\n")
            time.sleep(1.2)
            restart_toolkit()
            return True
        else:
            print(f"  {C.RED}✗ {T.get('update_failed', 'Update failed.')} ({error_msg}){C.RESET}")
            input(f"  {C.DIM}Press Enter to continue...{C.RESET}")
            return False

    return False
