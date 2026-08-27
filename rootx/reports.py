"""
rootx.reports
=============
Generates a plain-text diagnostic report (rootx-report.txt) summarizing
system, hardware, network, disk, memory, package manager, service and the
most relevant Doctor findings. Works the same way on Windows, macOS and
Linux since it only formats data already collected by the read-only
system/network/storage/services modules.

The report generator never writes passwords, tokens, private keys or other
secrets: it only ever includes data already collected elsewhere, none of
which touches credential stores.
"""

from __future__ import annotations

import os
from typing import Optional

from . import doctor as doctor_module
from . import utils

REPORT_FILENAME = "rootx-report.txt"


def build_report_text(report: "doctor_module.DoctorReport") -> str:
    lines = []
    lines.append("ROOT//X TOOLKIT - DIAGNOSTIC REPORT")
    lines.append(f"Generated: {utils.timestamp()}")
    lines.append(f"OS:        {utils.os_name()}")
    lines.append("=" * 60)

    s = report.system_info
    lines.append("\n[SYSTEM]")
    lines.append(f"OS / Distro:   {s.distro_name} {s.distro_version}")
    lines.append(f"Kernel:        {s.kernel}")
    lines.append(f"Architecture:  {s.architecture}")
    lines.append(f"Hostname:      {s.hostname}")
    lines.append(f"Uptime:        {s.uptime}")

    lines.append("\n[HARDWARE]")
    lines.append(f"CPU:           {s.cpu_model} ({s.cpu_cores} cores)")
    lines.append(f"Load average:  {s.load_average}")
    lines.append(f"RAM total:     {s.ram_total}")
    lines.append(f"RAM available: {s.ram_available}")
    lines.append(f"Swap total:    {s.swap_total}")
    lines.append(f"Swap used:     {s.swap_used}")
    lines.append(f"GPU:           {s.gpu}")
    lines.append(f"Motherboard:   {s.motherboard}")
    lines.append(f"Temperature:   {s.temperature}")

    lines.append("\n[DISK]")
    for mount in report.storage_result["mounts"]:
        lines.append(
            f"  {mount.mount_point:<20} {mount.used:>8}/{mount.size:<8} ({mount.percent}%) [{mount.level}]"
        )

    lines.append("\n[NETWORK]")
    net = report.network_result
    lines.append(f"Interface:     {net.interface_name}")
    lines.append(f"Local IP:      {net.local_ip}")
    lines.append(f"Gateway:       {net.gateway_ip}")
    lines.append(f"Gateway OK:    {net.gateway_ok}")
    lines.append(f"DNS OK:        {net.dns_ok}")
    lines.append(f"Internet OK:   {net.internet_ok}")

    lines.append("\n[PACKAGE MANAGER]")
    lines.append(f"Detected:      {report.package_manager or 'None detected'}")

    lines.append("\n[FAILED / STOPPED SERVICES]")
    if report.failed_services:
        for svc in report.failed_services:
            lines.append(f"  - {svc.name} ({svc.active}/{svc.sub})")
    else:
        lines.append("  None")

    lines.append("\n[FINDINGS]")
    lines.append(f"Problems detected: {report.problem_count}")
    for finding in report.criticals:
        lines.append(f"  [CRITICAL] {finding.category}: {finding.message}")
    for finding in report.warnings:
        lines.append(f"  [WARNING]  {finding.category}: {finding.message}")
    if report.problem_count == 0:
        lines.append("  No problems detected.")

    lines.append("\n" + "=" * 60)
    lines.append("Note: this report contains system diagnostic information only.")
    lines.append("No passwords, tokens, keys, or other secrets are ever included.")

    return "\n".join(lines)


def write_report(report: "doctor_module.DoctorReport", directory: Optional[str] = None) -> str:
    """Write the report to disk and return the absolute path."""
    directory = directory or os.getcwd()
    path = os.path.join(directory, REPORT_FILENAME)
    text = build_report_text(report)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return os.path.abspath(path)
