"""
rootx.tickets
=============
Ticket submission module.
Submits diagnostic support tickets to the GitHub Intake Gist (rootx-tickets-intake.json).
The Discord Bot reads this Gist, matches token_hash -> Discord User, and creates a Support Ticket!
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import urllib.error
import urllib.request
from typing import Any, Tuple

from rootx._config import (
    GIST_HMAC_SECRET,
    GIST_TIMEOUT,
    INTAKE_GITHUB_TOKEN,
    INTAKE_GIST_API_URL,
    INTAKE_GIST_FILENAME,
    INTAKE_GIST_RAW_URL,
    PRODUCT_NAME,
    VERSION,
)


def _sign_ticket(ticket_data: dict) -> str:
    """Sign ticket data with HMAC secret for integrity verification."""
    stable = json.dumps(ticket_data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    secret_bytes = GIST_HMAC_SECRET.encode("utf-8") if isinstance(GIST_HMAC_SECRET, str) else GIST_HMAC_SECRET
    return hmac.new(secret_bytes, stable, hashlib.sha256).hexdigest()


def fetch_intake_tickets() -> list:
    """Fetch existing pending tickets from the Intake Gist."""
    try:
        req = urllib.request.Request(
            INTAKE_GIST_RAW_URL,
            headers={
                "User-Agent": f"{PRODUCT_NAME}/{VERSION}",
                "Cache-Control": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=GIST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and "tickets" in data:
                return data.get("tickets", [])
            return []
    except Exception:
        return []


def submit_doctor_ticket(user_description: str, report: Any, token_hash: str) -> Tuple[bool, str]:
    """
    Submit a new diagnostic report ticket to the Intake Gist.
    User is prompted in CLI before this function is called.
    """
    ticket_payload = {
        "token_hash": token_hash,
        "user_description": user_description.strip(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "system_info": {
            "os": f"{report.system_info.distro_name} {report.system_info.distro_version}",
            "kernel": report.system_info.kernel,
            "arch": report.system_info.architecture,
            "hostname": report.system_info.hostname,
            "uptime": report.system_info.uptime,
        },
        "problems": [
            *[{"level": "CRITICAL", "message": c.message} for c in report.criticals],
            *[{"level": "WARNING", "message": w.message} for w in report.warnings],
        ],
        "failed_services": [svc.name for svc in report.failed_services],
        "network_ok": report.network_result.internet_ok,
    }

    ticket_payload["_sig"] = _sign_ticket(ticket_payload)

    # Load existing tickets
    existing_tickets = fetch_intake_tickets()
    existing_tickets.append(ticket_payload)

    intake_data = {
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tickets": existing_tickets,
    }

    # Prepare PATCH payload for GitHub API
    content_str = json.dumps(intake_data, indent=2)
    api_payload = {
        "files": {
            INTAKE_GIST_FILENAME: {
                "content": content_str
            }
        }
    }

    try:
        data_bytes = json.dumps(api_payload).encode("utf-8")
        headers = {
            "User-Agent": f"{PRODUCT_NAME}/{VERSION}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        }
        if INTAKE_GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {INTAKE_GITHUB_TOKEN}"

        req = urllib.request.Request(
            INTAKE_GIST_API_URL,
            data=data_bytes,
            headers=headers,
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=GIST_TIMEOUT) as resp:
            if resp.status in (200, 201):
                return True, "Ticket submitted successfully!"
            return False, f"HTTP {resp.status} updating ticket intake Gist."
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return False, "Gist write error (401 Unauthorized): INTAKE_GITHUB_TOKEN required for ticket submission."
        return False, f"HTTP {exc.code} error submitting ticket: {exc.reason}"
    except Exception as exc:
        return False, f"Failed to submit ticket: {exc}"
