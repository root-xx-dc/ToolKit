"""
rootx.ssl_inspector
===================
SSL/TLS Certificate & DNS Inspector.
No external dependencies — uses ssl + socket stdlib.
"""
from __future__ import annotations

import datetime
import socket
import ssl
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SSLInfo:
    domain: str
    valid: bool
    expires_at: Optional[datetime.datetime]
    days_remaining: Optional[int]
    issuer: str
    subject: str
    san: List[str] = field(default_factory=list)
    protocol: str = ""
    error: str = ""


@dataclass
class DNSInfo:
    domain: str
    a_records: List[str] = field(default_factory=list)
    aaaa_records: List[str] = field(default_factory=list)
    mx_records: List[str] = field(default_factory=list)
    ns_records: List[str] = field(default_factory=list)
    txt_records: List[str] = field(default_factory=list)
    error: str = ""


# ─── SSL ──────────────────────────────────────────────────────────────────────

def _parse_cert_dict(cert: dict) -> Tuple[str, str, List[str], Optional[datetime.datetime]]:
    """Parse subject, issuer, SANs, expiry from ssl cert dict."""
    def _rdn_to_str(rdn) -> str:
        return ", ".join(f"{k}={v}" for k, v in rdn)

    subject = _rdn_to_str(cert.get("subject", ((),))[0]) if cert.get("subject") else ""
    issuer = _rdn_to_str(cert.get("issuer", ((),))[0]) if cert.get("issuer") else ""

    san = []
    for entry in cert.get("subjectAltName", []):
        if entry[0].lower() == "dns":
            san.append(entry[1])

    expires_at = None
    not_after = cert.get("notAfter", "")
    if not_after:
        try:
            expires_at = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            pass

    return subject, issuer, san, expires_at


def check_ssl(domain: str, port: int = 443, timeout: int = 10) -> SSLInfo:
    domain = domain.strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0]
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                protocol = ssock.version() or ""

        subject, issuer, san, expires_at = _parse_cert_dict(cert)

        days_remaining = None
        if expires_at:
            now = datetime.datetime.now(datetime.timezone.utc)
            days_remaining = (expires_at - now).days

        return SSLInfo(
            domain=domain,
            valid=True,
            expires_at=expires_at,
            days_remaining=days_remaining,
            issuer=issuer,
            subject=subject,
            san=san,
            protocol=protocol,
        )
    except ssl.SSLCertVerificationError as e:
        return SSLInfo(domain=domain, valid=False, expires_at=None, days_remaining=None,
                       issuer="", subject="", error=f"Certificate verification failed: {e}")
    except ssl.SSLError as e:
        return SSLInfo(domain=domain, valid=False, expires_at=None, days_remaining=None,
                       issuer="", subject="", error=f"SSL error: {e}")
    except (socket.timeout, TimeoutError):
        return SSLInfo(domain=domain, valid=False, expires_at=None, days_remaining=None,
                       issuer="", subject="", error="Connection timed out.")
    except Exception as e:
        return SSLInfo(domain=domain, valid=False, expires_at=None, days_remaining=None,
                       issuer="", subject="", error=str(e))


# ─── DNS ──────────────────────────────────────────────────────────────────────

def _nslookup(domain: str, rtype: str) -> List[str]:
    """Run nslookup for a given record type and parse output."""
    try:
        result = subprocess.run(
            ["nslookup", f"-type={rtype}", domain],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout
        records = []
        for line in output.splitlines():
            line = line.strip()
            # Skip server/address lines
            if line.startswith("Server:") or line.startswith("Address:") and "#53" in line:
                continue
            if rtype.upper() == "A" and "Address:" in line and "#" not in line:
                addr = line.split(":", 1)[-1].strip()
                if addr and "." in addr:
                    records.append(addr)
            elif rtype.upper() == "AAAA" and "has AAAA address" in line:
                records.append(line.split("address")[-1].strip())
            elif rtype.upper() == "MX" and "mail exchanger" in line.lower():
                records.append(line.strip())
            elif rtype.upper() == "NS" and "nameserver" in line.lower():
                records.append(line.strip())
            elif rtype.upper() == "TXT" and "text =" in line.lower():
                records.append(line.split("=", 1)[-1].strip().strip('"'))
        return records
    except Exception:
        return []


def check_dns(domain: str) -> DNSInfo:
    domain = domain.strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0]
    info = DNSInfo(domain=domain)
    try:
        # A records
        try:
            results = socket.getaddrinfo(domain, None, socket.AF_INET)
            info.a_records = list({r[4][0] for r in results})
        except Exception:
            pass

        # AAAA records
        try:
            results = socket.getaddrinfo(domain, None, socket.AF_INET6)
            info.aaaa_records = list({r[4][0] for r in results})
        except Exception:
            pass

        # MX, NS, TXT via nslookup
        info.mx_records = _nslookup(domain, "MX")
        info.ns_records = _nslookup(domain, "NS")
        info.txt_records = _nslookup(domain, "TXT")

    except Exception as e:
        info.error = str(e)

    return info


# ─── Combined ─────────────────────────────────────────────────────────────────

def check_domain(domain: str) -> Tuple[SSLInfo, DNSInfo]:
    """Run both SSL and DNS checks for a domain."""
    ssl_info = check_ssl(domain)
    dns_info = check_dns(domain)
    return ssl_info, dns_info
