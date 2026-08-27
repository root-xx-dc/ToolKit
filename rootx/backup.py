"""
rootx.backup
============
Backup tool. Pure stdlib: tarfile + hashlib.
Checksum saved as <archive>.sha256.
Never overwrites existing backups.
"""

from __future__ import annotations

import hashlib
import os
import tarfile
import time
from dataclasses import dataclass
from typing import List, Tuple

from . import utils


@dataclass
class BackupInfo:
    path: str
    size: str
    date: str
    checksum_file: str
    verified: bool = False


def estimate_size(source: str) -> int:
    """Estimate total size of source in bytes using os.walk."""
    total = 0
    try:
        source = os.path.expanduser(source)
        if os.path.isfile(source):
            return os.path.getsize(source)
        for root, _, files in os.walk(source):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
    except Exception:
        pass
    return total


def _unique_path(dest_dir: str, name: str) -> str:
    """Generate a unique path, appending counter if needed."""
    base = os.path.join(dest_dir, name)
    if not os.path.exists(base):
        return base
    stem = name[:-7] if name.endswith(".tar.gz") else name
    counter = 1
    while True:
        candidate = os.path.join(dest_dir, f"{stem}_{counter}.tar.gz")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


def create_backup(source: str, dest: str) -> Tuple[bool, str]:
    """Create a .tar.gz backup of source in dest dir. Returns (ok, path_or_error)."""
    source = os.path.expanduser(source)
    dest = os.path.expanduser(dest)
    if not os.path.exists(source):
        return False, f"Source does not exist: {source}"
    try:
        os.makedirs(dest, exist_ok=True)
    except Exception as e:
        return False, f"Could not create destination: {e}"
    ts = time.strftime("%Y-%m-%d_%H-%M")
    basename = os.path.basename(source.rstrip("/\\")) or "root"
    archive_name = f"backup_{basename}_{ts}.tar.gz"
    archive_path = _unique_path(dest, archive_name)
    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(source, arcname=basename)
    except Exception as e:
        return False, f"Backup failed: {e}"

    sha256 = _sha256_file(archive_path)
    checksum_path = archive_path + ".sha256"
    try:
        with open(checksum_path, "w", encoding="utf-8") as f:
            f.write(f"{sha256}  {os.path.basename(archive_path)}\n")
    except Exception:
        pass
    return True, archive_path


def verify_backup(path: str) -> Tuple[bool, str]:
    """Verify backup checksum. Returns (ok, message)."""
    checksum_path = path + ".sha256"
    if not os.path.exists(checksum_path):
        return False, "No checksum file found."
    try:
        with open(checksum_path, "r", encoding="utf-8") as f:
            expected_line = f.read().strip()
        expected_hash = expected_line.split()[0]
    except Exception as e:
        return False, f"Could not read checksum: {e}"
    actual_hash = _sha256_file(path)
    if actual_hash == expected_hash:
        return True, f"Checksum OK: {actual_hash[:16]}..."
    return False, f"CHECKSUM MISMATCH! Expected: {expected_hash[:16]}... Got: {actual_hash[:16]}..."


def list_backups(dest: str) -> List[BackupInfo]:
    """List backup archives in dest directory."""
    dest = os.path.expanduser(dest)
    backups: List[BackupInfo] = []
    if not os.path.isdir(dest):
        return backups
    for fname in sorted(os.listdir(dest)):
        if fname.endswith(".tar.gz"):
            full = os.path.join(dest, fname)
            try:
                size = utils.human_bytes(os.path.getsize(full))
                mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(full)))
                checksum_file = full + ".sha256"
                backups.append(
                    BackupInfo(
                        path=full,
                        size=size,
                        date=mtime,
                        checksum_file=checksum_file if os.path.exists(checksum_file) else "",
                    )
                )
            except Exception:
                pass
    return backups


def restore_backup(archive: str, dest: str) -> Tuple[bool, str]:
    """Extract archive to dest. Returns (ok, message)."""
    archive = os.path.expanduser(archive)
    dest = os.path.expanduser(dest)
    if not os.path.exists(archive):
        return False, f"Archive not found: {archive}"
    try:
        os.makedirs(dest, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(path=dest)
        return True, f"Restored to: {dest}"
    except Exception as e:
        return False, f"Restore failed: {e}"
