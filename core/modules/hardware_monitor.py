import os
import sys
import time
import platform
import subprocess
import psutil
from colorama import Fore, Style

def draw_ascii_bar(percent: float, width: int = 20) -> str:
    filled_len = int(width * (percent / 100.0))
    filled_len = max(0, min(width, filled_len))
    empty_len = width - filled_len
    bar = "=" * filled_len + "." * empty_len
    if percent < 60:
        col = Fore.GREEN
    elif percent < 85:
        col = Fore.YELLOW
    else:
        col = Fore.RED
    return f"{col}[{bar}] {percent:>5.1f}%{Style.RESET_ALL}"

def get_gpu_info() -> list:
    gpus = []
    # 1. Try nvidia-smi
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append({
                        "name": parts[0],
                        "total_mem": f"{parts[1]} MB",
                        "used_mem": f"{parts[2]} MB",
                        "temp": f"{parts[3]} C",
                        "util": f"{parts[4]}%"
                    })
            return gpus
    except Exception:
        pass

    # 2. Try Windows WMI
    if os.name == "nt":
        try:
            res = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip() and l.strip() != "Name"]
                for l in lines:
                    gpus.append({"name": l, "total_mem": "System Managed", "used_mem": "N/A", "temp": "N/A", "util": "N/A"})
                return gpus
        except Exception:
            pass

    # 3. Try Linux lspci
    elif platform.system() == "Linux":
        try:
            res = subprocess.run(["lspci"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.split("\n"):
                    if "VGA" in line or "3D" in line or "Display" in line:
                        gpu_name = line.split(":")[-1].strip()
                        gpus.append({"name": gpu_name, "total_mem": "System Managed", "used_mem": "N/A", "temp": "N/A", "util": "N/A"})
                return gpus
        except Exception:
            pass

    if not gpus:
        gpus.append({"name": "Integrated / Standard Display Adapter", "total_mem": "Shared", "used_mem": "N/A", "temp": "N/A", "util": "N/A"})
    return gpus

def show_cpu_cores_meter():
    print(f"\n{Fore.CYAN}=== Real-Time CPU Core Monitor (Press Ctrl+C to Stop) ==={Style.RESET_ALL}")
    try:
        while True:
            per_cpu = psutil.cpu_percent(interval=1.0, percpu=True)
            freq = psutil.cpu_freq()
            
            # Clear lines using ANSI
            print(f"\033[H\033[J", end="") if os.name != "nt" else os.system("cls")
            print(f"{Fore.CYAN}=== ROOT//X CPU Core & Hardware Monitor ==={Style.RESET_ALL}")
            if freq:
                print(f"Current Frequency: {Fore.YELLOW}{freq.current:.1f} MHz{Style.RESET_ALL} (Min: {freq.min:.0f} MHz | Max: {freq.max:.0f} MHz)")
            print(f"Logical Threads:   {Fore.WHITE}{len(per_cpu)}{Style.RESET_ALL}\n")
            
            for idx, pct in enumerate(per_cpu):
                bar = draw_ascii_bar(pct, width=24)
                print(f"  Core #{idx:<2} {bar}")

            print(f"\n{Fore.WHITE}Overall Load: {draw_ascii_bar(psutil.cpu_percent(), width=30)}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}[*] Updating every 1s... Press Ctrl+C to return to menu.{Style.RESET_ALL}")
    except KeyboardInterrupt:
        pass

def show_memory_diagnostics():
    print(f"\n{Fore.CYAN}=== Memory & RAM Architecture Diagnostics ==={Style.RESET_ALL}")
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    gb = 1024 ** 3
    print(f"Physical Memory (RAM):")
    print(f"  Total RAM:      {Fore.WHITE}{vm.total / gb:.2f} GB{Style.RESET_ALL}")
    print(f"  In Use:         {Fore.YELLOW}{vm.used / gb:.2f} GB{Style.RESET_ALL}")
    print(f"  Available:      {Fore.GREEN}{vm.available / gb:.2f} GB{Style.RESET_ALL}")
    print(f"  Memory Load:    {draw_ascii_bar(vm.percent, width=25)}")
    
    if hasattr(vm, 'cached') and vm.cached:
        print(f"  Cached Memory:  {Fore.CYAN}{vm.cached / gb:.2f} GB{Style.RESET_ALL}")
    if hasattr(vm, 'buffers') and vm.buffers:
        print(f"  Buffer Cache:   {Fore.CYAN}{vm.buffers / gb:.2f} GB{Style.RESET_ALL}")

    print(f"\nSwap / Pagefile:")
    print(f"  Total Swap:     {Fore.WHITE}{swap.total / gb:.2f} GB{Style.RESET_ALL}")
    print(f"  Used Swap:      {Fore.YELLOW}{swap.used / gb:.2f} GB{Style.RESET_ALL}")
    print(f"  Swap Load:      {draw_ascii_bar(swap.percent, width=25)}")

def show_gpu_and_power():
    print(f"\n{Fore.CYAN}=== GPU & Power Sensors ==={Style.RESET_ALL}")
    gpus = get_gpu_info()
    print(f"Detected Graphics Adapters ({len(gpus)}):")
    for idx, gpu in enumerate(gpus):
        print(f"  [{idx + 1}] {Fore.GREEN}{gpu['name']}{Style.RESET_ALL}")
        print(f"      VRAM: {Fore.WHITE}{gpu['used_mem']} / {gpu['total_mem']}{Style.RESET_ALL} | Temp: {Fore.YELLOW}{gpu['temp']}{Style.RESET_ALL} | Util: {Fore.CYAN}{gpu['util']}{Style.RESET_ALL}")

    print(f"\nPower & Battery Status:")
    if hasattr(psutil, "sensors_battery"):
        battery = psutil.sensors_battery()
        if battery:
            plugged = "AC Power Connected" if battery.power_plugged else "Running on Battery"
            plug_col = Fore.GREEN if battery.power_plugged else Fore.YELLOW
            print(f"  Power Source: {plug_col}{plugged}{Style.RESET_ALL}")
            print(f"  Charge Level: {draw_ascii_bar(battery.percent, width=20)}")
            if not battery.power_plugged and battery.secsleft > 0:
                mins = battery.secsleft // 60
                print(f"  Remaining:    {Fore.WHITE}{mins // 60}h {mins % 60}m{Style.RESET_ALL}")
        else:
            print(f"  {Fore.WHITE}Desktop / No Battery Detected (Direct AC Power){Style.RESET_ALL}")
    else:
        print(f"  {Fore.WHITE}Power metrics not supported on this platform.{Style.RESET_ALL}")

def run_hardware_monitor():
    while True:
        print(f"\n{Fore.CYAN}=== ROOT//X Hardware & Sensor Diagnostics ==={Style.RESET_ALL}")
        print(f"{Fore.WHITE}[1] Real-Time CPU Multi-Core Usage Meter")
        print(f"{Fore.WHITE}[2] Detailed RAM & Memory Diagnostics")
        print(f"{Fore.WHITE}[3] GPU & Power / Battery Sensors")
        print(f"{Fore.WHITE}[0] Back to Main Menu\n")

        choice = input(f"{Fore.WHITE}Select Option [0-3]: {Style.RESET_ALL}").strip()
        if choice == "1":
            show_cpu_cores_meter()
        elif choice == "2":
            show_memory_diagnostics()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif choice == "3":
            show_gpu_and_power()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif choice == "0":
            break
