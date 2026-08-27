"""
rootx.live_monitor
==================
Live TUI Resource Monitor.
Refreshes every 1 second. CPU per-core bars, RAM bar, Network speed.
Press Ctrl+C to exit.
"""
from __future__ import annotations

import os
import sys
import time
from typing import List, Optional


def _bar(value: float, width: int = 20, char_fill: str = "#", char_empty: str = ".") -> str:
    """Return ASCII progress bar like [####....] 45.3%"""
    filled = int(round(value / 100 * width))
    filled = max(0, min(width, filled))
    bar = char_fill * filled + char_empty * (width - filled)
    return f"[{bar}] {value:5.1f}%"


def _color(value: float, low: str = "\033[92m", mid: str = "\033[93m", high: str = "\033[91m") -> str:
    if value < 60:
        return low
    elif value < 85:
        return mid
    return high


def _fmt_speed(bps: float) -> str:
    if bps < 1024:
        return f"{bps:.0f} B/s"
    elif bps < 1024 ** 2:
        return f"{bps / 1024:.1f} KB/s"
    elif bps < 1024 ** 3:
        return f"{bps / 1024 ** 2:.1f} MB/s"
    return f"{bps / 1024 ** 3:.1f} GB/s"


def _get_cpu_per_core(psutil) -> List[float]:
    return psutil.cpu_percent(percpu=True, interval=None) or []


def _get_ram(psutil) -> dict:
    vm = psutil.virtual_memory()
    return {
        "total": vm.total,
        "used": vm.used,
        "available": vm.available,
        "percent": vm.percent,
    }


def _get_net_speed(psutil, prev_counters, interval: float):
    curr = psutil.net_io_counters()
    if prev_counters is None:
        return 0.0, 0.0, curr
    rx = max(0.0, (curr.bytes_recv - prev_counters.bytes_recv) / interval)
    tx = max(0.0, (curr.bytes_sent - prev_counters.bytes_sent) / interval)
    return rx, tx, curr


def _render_frame(
    cpu_cores: List[float],
    ram: dict,
    rx_speed: float,
    tx_speed: float,
    term_width: int,
    elapsed: int,
) -> str:
    RESET = "\033[0m"
    CYAN  = "\033[96m"
    DIM   = "\033[2m"
    BOLD  = "\033[1m"
    YELLOW = "\033[93m"
    WHITE  = "\033[97m"
    SEP = f"  {DIM}{'─' * min(term_width - 4, 60)}{RESET}"

    lines = ["\033[2J\033[H"]  # clear screen, move cursor to top
    lines.append(f"  {BOLD}{CYAN}ROOT//X  LIVE MONITOR{RESET}  {DIM}[Ctrl+C to exit | {elapsed}s]{RESET}")
    lines.append(SEP)

    # CPU per-core
    lines.append(f"  {BOLD}CPU{RESET}")
    per_row = 4
    for i in range(0, len(cpu_cores), per_row):
        row_cores = cpu_cores[i:i + per_row]
        row_str = ""
        for j, pct in enumerate(row_cores):
            core_num = i + j
            col = _color(pct)
            row_str += f"  {DIM}Core{core_num:02d}{RESET} {col}{_bar(pct, 12)}{RESET}"
        lines.append(row_str)

    # Overall CPU
    avg_cpu = sum(cpu_cores) / len(cpu_cores) if cpu_cores else 0
    col = _color(avg_cpu)
    lines.append(f"\n  {DIM}Total {RESET} {col}{_bar(avg_cpu, 40)}{RESET}")
    lines.append(SEP)

    # RAM
    ram_pct = ram["percent"]
    ram_used_gb = ram["used"] / (1024 ** 3)
    ram_total_gb = ram["total"] / (1024 ** 3)
    col = _color(ram_pct)
    lines.append(f"  {BOLD}RAM{RESET}")
    lines.append(f"  {col}{_bar(ram_pct, 40)}{RESET}  {DIM}{ram_used_gb:.2f} / {ram_total_gb:.2f} GB{RESET}")
    lines.append(SEP)

    # Network
    lines.append(f"  {BOLD}NETWORK{RESET}")
    lines.append(f"  {CYAN}RX{RESET}  {_fmt_speed(rx_speed):<14}  {CYAN}TX{RESET}  {_fmt_speed(tx_speed)}")
    lines.append(SEP)
    lines.append(f"  {DIM}Press Ctrl+C to return to menu.{RESET}")

    return "\n".join(lines)


def run_live_monitor() -> None:
    """Start the live TUI monitor. Blocks until Ctrl+C."""
    try:
        import psutil
    except ImportError:
        print("  [ERROR] psutil is required for live monitoring.")
        print("  Install with: pip install psutil")
        return

    # Initial poll to seed CPU counters
    psutil.cpu_percent(percpu=True, interval=None)
    prev_net = psutil.net_io_counters()
    start = time.time()

    try:
        while True:
            t0 = time.time()
            time.sleep(1.0)
            interval = time.time() - t0

            cpu_cores = _get_cpu_per_core(psutil)
            ram = _get_ram(psutil)
            rx, tx, prev_net = _get_net_speed(psutil, prev_net, interval)
            elapsed = int(time.time() - start)

            try:
                term_width = os.get_terminal_size().columns
            except Exception:
                term_width = 80

            frame = _render_frame(cpu_cores, ram, rx, tx, term_width, elapsed)
            sys.stdout.write(frame)
            sys.stdout.flush()

    except KeyboardInterrupt:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
