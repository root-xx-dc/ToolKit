import os
import sys
import psutil
import time
from colorama import Fore, Style

def draw_resource_bar(percent: float, width: int = 20) -> str:
    filled = max(0, min(width, int(width * (percent / 100.0))))
    bar = "=" * filled + "." * (width - filled)
    if percent < 60:
        col = Fore.GREEN
    elif percent < 85:
        col = Fore.YELLOW
    else:
        col = Fore.RED
    return f"{col}[{bar}] {percent:>5.1f}%{Style.RESET_ALL}"

def show_system_resources():
    print(f"\n{Fore.CYAN}=== Real-Time System Resource Breakdown ==={Style.RESET_ALL}")
    cpu_pct = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    root_path = os.path.splitdrive(os.getcwd())[0] + os.sep if os.name == 'nt' else '/'
    
    gb = 1024 ** 3
    print(f"  CPU Total Load:  {draw_resource_bar(cpu_pct, width=25)}")
    print(f"  RAM Utilization: {draw_resource_bar(ram.percent, width=25)} ({ram.used / gb:.2f} GB / {ram.total / gb:.2f} GB)")
    
    try:
        disk = psutil.disk_usage(root_path)
        print(f"  Disk ({root_path}):     {draw_resource_bar(disk.percent, width=25)} ({disk.used / gb:.2f} GB / {disk.total / gb:.2f} GB)")
    except Exception:
        pass

    net = psutil.net_io_counters()
    print(f"  Network I/O:     Sent: {Fore.GREEN}{net.bytes_sent / (1024**2):.2f} MB{Style.RESET_ALL} | Recv: {Fore.CYAN}{net.bytes_recv / (1024**2):.2f} MB{Style.RESET_ALL}")

def show_top_processes():
    print(f"\n{Fore.CYAN}=== Top 10 Resource Consuming Processes ==={Style.RESET_ALL}")
    print(f"  {'PID':<8} {'User':<16} {'CPU %':<8} {'RAM %':<8} {'Name'}")
    print("  " + "-" * 65)
    
    procs = []
    for p in psutil.process_iter(['pid', 'username', 'cpu_percent', 'memory_percent', 'name']):
        try:
            procs.append(p.info)
        except Exception:
            pass
            
    procs = sorted(procs, key=lambda x: (x.get('cpu_percent') or 0, x.get('memory_percent') or 0), reverse=True)[:10]
    for p in procs:
        cpu = p.get('cpu_percent') or 0.0
        mem = p.get('memory_percent') or 0.0
        user = str(p.get('username') or 'N/A')[:15]
        name = str(p.get('name') or 'N/A')
        print(f"  {p['pid']:<8} {user:<16} {cpu:<8.1f} {mem:<8.1f} {name}")

def show_network_interfaces():
    print(f"\n{Fore.CYAN}=== Network Interface Statistics & Counters ==={Style.RESET_ALL}")
    net_if = psutil.net_io_counters(pernic=True)
    addrs = psutil.net_if_addrs()

    for iface, stats in net_if.items():
        if iface.startswith("lo") or iface.startswith("Loopback"):
            continue
        ip_str = "N/A"
        if iface in addrs:
            for snic in addrs[iface]:
                if snic.family.name == "AF_INET":
                    ip_str = snic.address
                    break

        print(f"  [+] Interface: {Fore.GREEN}{iface:<16}{Style.RESET_ALL} (IP: {Fore.YELLOW}{ip_str}{Style.RESET_ALL})")
        print(f"      Sent: {stats.bytes_sent / (1024**2):>8.2f} MB ({stats.packets_sent} pkts) | Errors: {stats.errout}")
        print(f"      Recv: {stats.bytes_recv / (1024**2):>8.2f} MB ({stats.packets_recv} pkts) | Drop:   {stats.dropin}")

def terminate_process():
    pid_str = input(f"\n{Fore.WHITE}Enter PID to terminate: {Style.RESET_ALL}").strip()
    if pid_str.isdigit():
        try:
            p = psutil.Process(int(pid_str))
            p_name = p.name()
            p.terminate()
            print(f"{Fore.GREEN}[+] Process '{p_name}' (PID {pid_str}) terminated successfully.{Style.RESET_ALL}")
        except psutil.NoSuchProcess:
            print(f"{Fore.RED}[-] Process with PID {pid_str} not found.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[-] Termination failed: {e}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}[!] Invalid PID entered.{Style.RESET_ALL}")

def run_server_manager():
    while True:
        print(f"\n{Fore.CYAN}=== ROOT//X Server & Process Manager ==={Style.RESET_ALL}")
        print(f"{Fore.WHITE}[1] System Resource Usage & Health Overview")
        print(f"{Fore.WHITE}[2] List Top CPU / Memory Processes")
        print(f"{Fore.WHITE}[3] Network Interface Statistics")
        print(f"{Fore.WHITE}[4] Terminate Process by PID")
        print(f"{Fore.WHITE}[0] Back to Main Menu\n")

        c = input(f"{Fore.WHITE}Select Option [0-4]: {Style.RESET_ALL}").strip()
        if c == "1":
            show_system_resources()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif c == "2":
            show_top_processes()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif c == "3":
            show_network_interfaces()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif c == "4":
            terminate_process()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif c == "0":
            break
