import os
import sys
import time
import tempfile
import psutil
from colorama import Fore, Style

def draw_storage_bar(percent: float, width: int = 20) -> str:
    filled = max(0, min(width, int(width * (percent / 100.0))))
    bar = "=" * filled + "." * (width - filled)
    if percent < 70:
        col = Fore.GREEN
    elif percent < 90:
        col = Fore.YELLOW
    else:
        col = Fore.RED
    return f"{col}[{bar}] {percent:>5.1f}%{Style.RESET_ALL}"

def show_disk_partitions():
    print(f"\n{Fore.CYAN}=== Storage Partitions & Drive Allocation ==={Style.RESET_ALL}")
    partitions = psutil.disk_partitions(all=False)
    
    if not partitions:
        print(f"  {Fore.YELLOW}[!] No physical storage partitions detected.{Style.RESET_ALL}")
        return

    gb = 1024 ** 3
    print(f"  {'Device':<16} {'Mount / Drive':<18} {'FSType':<10} {'Total':<10} {'Used':<10} {'Free':<10} {'Usage Bar'}")
    print("  " + "-" * 85)

    for p in partitions:
        try:
            usage = psutil.disk_usage(p.mountpoint)
            total_gb = f"{usage.total / gb:.1f} GB"
            used_gb = f"{usage.used / gb:.1f} GB"
            free_gb = f"{usage.free / gb:.1f} GB"
            bar = draw_storage_bar(usage.percent, width=15)
            print(f"  {p.device[:15]:<16} {p.mountpoint[:17]:<18} {p.fstype[:9]:<10} {total_gb:<10} {used_gb:<10} {free_gb:<10} {bar}")
        except PermissionError:
            print(f"  {p.device[:15]:<16} {p.mountpoint[:17]:<18} {p.fstype[:9]:<10} [Access Denied]")
        except Exception:
            pass

def run_speed_benchmark():
    print(f"\n{Fore.CYAN}=== Sequential Drive Read / Write Speed Benchmark ==={Style.RESET_ALL}")
    print(f"{Fore.WHITE}[*] Preparing temporary benchmark test block (50 MB)...{Style.RESET_ALL}")
    
    target_dir = tempfile.gettempdir()
    test_file_path = os.path.join(target_dir, f"rootx_io_bench_{int(time.time())}.tmp")
    block_size = 1024 * 1024  # 1 MB
    blocks_count = 50         # 50 MB
    payload = b"\xaa" * block_size

    try:
        # Write Test
        print(f"  [+] Testing Sequential Write Speed to: {Fore.YELLOW}{target_dir}{Style.RESET_ALL}")
        start_write = time.perf_counter()
        with open(test_file_path, "wb") as f:
            for _ in range(blocks_count):
                f.write(payload)
            f.flush()
            if hasattr(os, "fdatasync"):
                os.fdatasync(f.fileno())
            elif hasattr(os, "fsync"):
                os.fsync(f.fileno())
        write_time = time.perf_counter() - start_write
        write_speed = (blocks_count / write_time) if write_time > 0 else 0.0

        print(f"      {Fore.GREEN}[OK] Write Speed: {Fore.CYAN}{write_speed:.2f} MB/s{Style.RESET_ALL} (Time: {write_time:.2f}s)")

        # Read Test
        print(f"  [+] Testing Sequential Read Speed...")
        start_read = time.perf_counter()
        bytes_read = 0
        with open(test_file_path, "rb") as f:
            while True:
                buf = f.read(block_size)
                if not buf:
                    break
                bytes_read += len(buf)
        read_time = time.perf_counter() - start_read
        read_speed = ((bytes_read / (1024 * 1024)) / read_time) if read_time > 0 else 0.0

        print(f"      {Fore.GREEN}[OK] Read Speed:  {Fore.CYAN}{read_speed:.2f} MB/s{Style.RESET_ALL} (Time: {read_time:.2f}s)")

        # Rating
        avg_speed = (write_speed + read_speed) / 2
        if avg_speed > 500:
            rating = f"{Fore.GREEN}[NVMe SSD - ULTRA SPEED]{Style.RESET_ALL}"
        elif avg_speed > 200:
            rating = f"{Fore.CYAN}[SATA SSD - HIGH SPEED]{Style.RESET_ALL}"
        elif avg_speed > 80:
            rating = f"{Fore.YELLOW}[HDD / USB 3.0 - STANDARD SPEED]{Style.RESET_ALL}"
        else:
            rating = f"{Fore.RED}[SLOW STORAGE / BUS CONGESTION]{Style.RESET_ALL}"

        print(f"\n  [#] Storage Performance Tier: {rating}")

    except Exception as e:
        print(f"  {Fore.RED}[-] Benchmark error: {e}{Style.RESET_ALL}")
    finally:
        if os.path.exists(test_file_path):
            try:
                os.remove(test_file_path)
            except Exception:
                pass

def monitor_disk_io():
    print(f"\n{Fore.CYAN}=== Real-Time Disk I/O Activity Monitor (Press Ctrl+C to Stop) ==={Style.RESET_ALL}")
    try:
        last_io = psutil.disk_io_counters()
        last_time = time.time()
        time.sleep(1.0)

        while True:
            curr_io = psutil.disk_io_counters()
            curr_time = time.time()
            elapsed = curr_time - last_time

            read_bytes_sec = (curr_io.read_bytes - last_io.read_bytes) / elapsed
            write_bytes_sec = (curr_io.write_bytes - last_io.write_bytes) / elapsed
            read_mb_s = read_bytes_sec / (1024 * 1024)
            write_mb_s = write_bytes_sec / (1024 * 1024)

            print(f"\033[H\033[J", end="") if os.name != "nt" else os.system("cls")
            print(f"{Fore.CYAN}=== ROOT//X Storage I/O Real-Time Monitor ==={Style.RESET_ALL}")
            print(f"  Read Throughput:   {Fore.GREEN}{read_mb_s:>7.2f} MB/s{Style.RESET_ALL} (Total Read:  {curr_io.read_bytes // (1024**2)} MB)")
            print(f"  Write Throughput:  {Fore.YELLOW}{write_mb_s:>7.2f} MB/s{Style.RESET_ALL} (Total Write: {curr_io.write_bytes // (1024**2)} MB)")
            print(f"  Read Operations:   {Fore.WHITE}{curr_io.read_count}{Style.RESET_ALL} ops")
            print(f"  Write Operations:  {Fore.WHITE}{curr_io.write_count}{Style.RESET_ALL} ops")
            
            print(f"\n{Fore.YELLOW}[*] Sampling rate: 1.0s. Press Ctrl+C to exit.{Style.RESET_ALL}")

            last_io = curr_io
            last_time = curr_time
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"{Fore.RED}[-] I/O monitoring unavailable: {e}{Style.RESET_ALL}")

def run_storage_benchmark():
    while True:
        print(f"\n{Fore.CYAN}=== ROOT//X Storage & Drive Diagnostics Suite ==={Style.RESET_ALL}")
        print(f"{Fore.WHITE}[1] Disk Partitions & Storage Allocation Explorer")
        print(f"{Fore.WHITE}[2] Sequential Drive Read / Write Speed Benchmark")
        print(f"{Fore.WHITE}[3] Real-Time Disk I/O Activity Monitor")
        print(f"{Fore.WHITE}[0] Back to Main Menu\n")

        choice = input(f"{Fore.WHITE}Select Option [0-3]: {Style.RESET_ALL}").strip()
        if choice == "1":
            show_disk_partitions()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif choice == "2":
            run_speed_benchmark()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif choice == "3":
            monitor_disk_io()
        elif choice == "0":
            break
