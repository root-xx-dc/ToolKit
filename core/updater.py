"""
ROOT//X Toolkit Auto-Updater
Seamlessly checks for the latest GitHub commits and updates the application
for both Git clones and standalone directory/ZIP installations.
"""

import os
import sys
import time
import json
import zipfile
import tempfile
import subprocess
import urllib.request
from colorama import Fore, Style

GITHUB_REPO = "root-xx-dc/ToolKit"
GITHUB_COMMITS_API = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
GITHUB_ZIP_URL = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"
CURRENT_COMMIT_FALLBACK = "5ba9154"
HEADERS = {
    "User-Agent": "ROOTX-Toolkit-Updater/2.5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/vnd.github.v3+json"
}

def get_toolkit_dir() -> str:
    """Returns the base directory of the ToolKit installation."""
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return pkg_dir

def get_local_commit() -> str:
    """Gets the currently installed commit hash."""
    toolkit_dir = get_toolkit_dir()
    
    # 1. Try git rev-parse if .git exists
    git_dir = os.path.join(toolkit_dir, ".git")
    if os.path.exists(git_dir):
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=toolkit_dir,
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

    # 2. Try .commit_hash file
    hash_file = os.path.join(toolkit_dir, ".commit_hash")
    if os.path.exists(hash_file):
        try:
            with open(hash_file, "r", encoding="utf-8") as f:
                h = f.read().strip()
                if h:
                    return h
        except Exception:
            pass

    return CURRENT_COMMIT_FALLBACK

def check_for_remote_update() -> dict | None:
    """Checks GitHub for the latest commit on main branch."""
    try:
        req = urllib.request.Request(GITHUB_COMMITS_API, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                raw_data = response.read().decode("utf-8")
                data = json.loads(raw_data)
                remote_sha = data.get("sha", "")
                commit_info = data.get("commit", {})
                message = commit_info.get("message", "").split("\n")[0]
                author = commit_info.get("author", {}).get("name", "ROOT//X Dev")

                local_sha = get_local_commit()

                if remote_sha and not local_sha.startswith(remote_sha[:7]) and not remote_sha.startswith(local_sha[:7]):
                    return {
                        "remote_sha": remote_sha,
                        "short_sha": remote_sha[:7],
                        "message": message,
                        "author": author,
                        "local_sha": local_sha[:7]
                    }
    except Exception:
        pass
    return None

def perform_update(update_info: dict) -> bool:
    """Performs the actual update via Git pull or ZIP extraction."""
    toolkit_dir = get_toolkit_dir()
    git_dir = os.path.join(toolkit_dir, ".git")
    remote_sha = update_info.get("remote_sha", "")

    print(f"\n{Fore.CYAN}[*] Pobieranie i instalowanie aktualizacji z GitHuba...{Style.RESET_ALL}")

    # Method 1: Git Pull
    if os.path.exists(git_dir):
        try:
            res = subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=toolkit_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            if res.returncode == 0:
                # Save hash file as backup
                with open(os.path.join(toolkit_dir, ".commit_hash"), "w", encoding="utf-8") as f:
                    f.write(remote_sha)
                
                # Re-link entry point
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps"],
                    cwd=toolkit_dir,
                    capture_output=True,
                    timeout=15
                )
                return True
        except Exception:
            pass

    # Method 2: ZIP Download & Extract (Standalone Directory)
    try:
        req = urllib.request.Request(GITHUB_ZIP_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status != 200:
                print(f"{Fore.RED}[-] Nie udalo sie pobrac archiwum: HTTP {response.status}{Style.RESET_ALL}")
                return False

            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                tmp_path = tmp_file.name
                while True:
                    chunk = response.read(16384)
                    if not chunk:
                        break
                    tmp_file.write(chunk)

        # Extract files over toolkit_dir
        with zipfile.ZipFile(tmp_path, "r") as zf:
            namelist = zf.namelist()
            top_dir = namelist[0].split("/")[0] if namelist else "ToolKit-main"

            for member in namelist:
                if member.endswith("/"):
                    continue
                # Strip top level directory (e.g. ToolKit-main/)
                rel_path = member[len(top_dir) + 1:] if member.startswith(top_dir + "/") else member
                if not rel_path:
                    continue

                dest_path = os.path.join(toolkit_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                with zf.open(member) as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())

        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        # Write current commit hash
        with open(os.path.join(toolkit_dir, ".commit_hash"), "w", encoding="utf-8") as f:
            f.write(remote_sha)

        # Re-link editable package
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps"],
                cwd=toolkit_dir,
                capture_output=True,
                timeout=15
            )
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"{Fore.RED}[-] Blad podczas instalacji aktualizacji: {e}{Style.RESET_ALL}")
        return False

def check_and_prompt_update():
    """Entry point called on startup. Prompts user if an update is found."""
    update = check_for_remote_update()
    if not update:
        return

    banner = f"""
  {Fore.CYAN}==================================================
    {Fore.GREEN}DOSTEPNA AKTUALIZACJA / UPDATE AVAILABLE
  {Fore.CYAN}==================================================
    {Fore.WHITE}Dostepna jest nowa wersja / aktualizacja ROOT//X TOOLKIT na GitHubie!
    {Fore.WHITE}Commit: {Fore.YELLOW}[{update['short_sha']}]{Fore.WHITE} - {update['message']}
    {Fore.WHITE}Autor:  {Fore.CYAN}{update['author']}
  {Fore.CYAN}=================================================={Style.RESET_ALL}
"""
    print(banner)
    choice = input(f"  {Fore.WHITE}Czy chcesz pobrac i zainstalowac te aktualizacje teraz? [t/N]: {Style.RESET_ALL}").strip().lower()

    if choice in ["t", "tak", "y", "yes"]:
        success = perform_update(update)
        if success:
            print(f"  {Fore.GREEN}[+] Aktualizacja zainstalowana pomyslnie! Restartowanie ROOT//X TOOLKIT...{Style.RESET_ALL}\n")
            time.sleep(1.0)
            # Restart current process
            toolkit_dir = get_toolkit_dir()
            main_script = os.path.join(toolkit_dir, "main.py")
            if os.path.exists(main_script):
                os.execv(sys.executable, [sys.executable, main_script])
            else:
                os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print(f"  {Fore.RED}[!] Aktualizacja nie powiodla sie. Kontynuowanie uruchamiania...{Style.RESET_ALL}\n")
            time.sleep(1.5)
    else:
        print(f"  {Fore.YELLOW}[*] Pominieto aktualizacje.{Style.RESET_ALL}\n")
