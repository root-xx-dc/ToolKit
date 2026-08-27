"""
rootx.hash_tool
===============
Hash Calculator & Password / API Key Generator.
Uses stdlib only: hashlib, secrets, string.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import os
import secrets
import string
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class HashResult:
    algorithm: str
    value: str
    match: Optional[bool] = None  # None = no comparison, True/False = result


@dataclass
class PasswordResult:
    password: str
    length: int
    entropy_bits: float
    charset: str
    charset_size: int


_ALGORITHMS = ["md5", "sha1", "sha256", "sha512"]
_CHUNK_SIZE = 65536  # 64 KB


def _hash_bytes(data: bytes, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    h.update(data)
    return h.hexdigest()


def _hash_file_stream(path: str, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


# ─── Hash ─────────────────────────────────────────────────────────────────────

def hash_file(
    path: str,
    algorithms: Optional[List[str]] = None,
    compare_with: Optional[str] = None,
) -> Dict[str, HashResult]:
    """
    Compute hash(es) for a file.
    compare_with: if given, compares against the SHA-256 result (or the first algorithm).
    """
    if algorithms is None:
        algorithms = _ALGORITHMS

    results = {}
    for algo in algorithms:
        try:
            value = _hash_file_stream(path, algo)
            match = None
            if compare_with and algo == algorithms[0]:
                match = hmac.compare_digest(
                    value.lower().strip(),
                    compare_with.lower().strip(),
                )
            results[algo] = HashResult(algorithm=algo, value=value, match=match)
        except (ValueError, FileNotFoundError, PermissionError) as e:
            results[algo] = HashResult(algorithm=algo, value=f"ERROR: {e}")
    return results


def hash_string(
    data: str,
    algorithms: Optional[List[str]] = None,
    compare_with: Optional[str] = None,
) -> Dict[str, HashResult]:
    """Compute hash(es) for a string."""
    if algorithms is None:
        algorithms = _ALGORITHMS

    encoded = data.encode("utf-8")
    results = {}
    for algo in algorithms:
        try:
            value = _hash_bytes(encoded, algo)
            match = None
            if compare_with and algo == algorithms[0]:
                match = hmac.compare_digest(
                    value.lower().strip(),
                    compare_with.lower().strip(),
                )
            results[algo] = HashResult(algorithm=algo, value=value, match=match)
        except ValueError as e:
            results[algo] = HashResult(algorithm=algo, value=f"ERROR: {e}")
    return results


def compare_hash(computed: str, expected: str) -> bool:
    """Constant-time hash comparison."""
    return hmac.compare_digest(computed.lower().strip(), expected.lower().strip())


# ─── Password Generator ───────────────────────────────────────────────────────

def generate_password(
    length: int = 32,
    use_upper: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> PasswordResult:
    """
    Generate a cryptographically secure random password.
    Always includes lowercase letters as base.
    """
    charset = string.ascii_lowercase
    charset_name = "lowercase"

    if use_upper:
        charset += string.ascii_uppercase
        charset_name += "+uppercase"
    if use_digits:
        charset += string.digits
        charset_name += "+digits"
    if use_symbols:
        charset += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        charset_name += "+symbols"

    charset_size = len(charset)
    entropy = length * math.log2(charset_size)

    # Ensure at least one of each required class
    password_chars = []
    if use_upper:
        password_chars.append(secrets.choice(string.ascii_uppercase))
    if use_digits:
        password_chars.append(secrets.choice(string.digits))
    if use_symbols:
        password_chars.append(secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))
    password_chars.append(secrets.choice(string.ascii_lowercase))

    # Fill rest
    remaining = length - len(password_chars)
    password_chars.extend(secrets.choice(charset) for _ in range(remaining))

    # Shuffle
    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

    return PasswordResult(
        password="".join(password_chars),
        length=length,
        entropy_bits=round(entropy, 1),
        charset=charset_name,
        charset_size=charset_size,
    )


def generate_api_key(length: int = 64) -> str:
    """Generate a cryptographically secure API key (hex string)."""
    return secrets.token_hex(length // 2)


def generate_uuid() -> str:
    """Generate a random UUID v4."""
    return str(uuid.uuid4())


def generate_urlsafe_token(length: int = 32) -> str:
    """Generate a URL-safe random token."""
    return secrets.token_urlsafe(length)
