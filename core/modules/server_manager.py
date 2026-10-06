import os
import psutil
import time
from colorama import Fore, Style

def run_server_manager():
    while True:
        print(f"\n{Fore.CYAN}=== ROOT//X Server & Process Manager ===")
        print(f"{Fore.WHITE}[1] System Resource Usage (CPU, RAM, Disk)")
        print(f"{Fore.WHITE}[2] List Top CPU Consuming Processes")
        print(f"{Fore.WHITE}[3] Network Interface Statistics")
        print(f"{Fore.WHITE}[4] Kill Process by PID")
        print(f"{Fore.WHITE}[0] Back to Main Menu\n")

        c = input(f"{Fore.WHITE}Select Option: ").strip()
        if c == "1":
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            root_path = os.path.splitdrive(os.getcwd())[0] + os.sep if os.name == 'nt' else '/'
            try:
                disk = psutil.disk_usage(root_path)
                disk_str = f"{disk.percent}% ({round(disk.used/(1024**3),2)} GB / {round(disk.total/(1024**3),2)} GB)"
            except Exception:
                disk_str = "N/A"
            print(f"\n{Fore.GREEN}CPU Usage:{Fore.WHITE} {cpu}%")
            print(f"{Fore.GREEN}RAM Usage:{Fore.WHITE} {ram.percent}% ({round(ram.used/(1024**3),2)} GB / {round(ram.total/(1024**3),2)} GB)")
            print(f"{Fore.GREEN}Disk Usage ({root_path}):{Fore.WHITE} {disk_str}")
        elif c == "2":
            print(f"\n{Fore.GREEN}{'PID':<8} {'User':<15} {'CPU %':<8} {'RAM %':<8} {'Name'}")
            print("-" * 60)
            procs = []
            for p in psutil.process_iter(['pid', 'username', 'cpu_percent', 'memory_percent', 'name']):
                try:
                    procs.append(p.info)
                except Exception:
                    pass
            procs = sorted(procs, key=lambda x: x.get('cpu_percent') or 0, reverse=True)[:10]
            for p in procs:
                print(f"{p['pid']:<8} {str(p['username'])[:14]:<15} {str(p['cpu_percent']):<8} {str(round(p['memory_percent'] or 0, 1)):<8} {p['name']}")
        elif c == "3":
            net = psutil.net_io_counters()
            print(f"\n{Fore.GREEN}Bytes Sent:{Fore.WHITE} {round(net.bytes_sent/(1024**2), 2)} MB")
            print(f"{Fore.GREEN}Bytes Recv:{Fore.WHITE} {round(net.bytes_recv/(1024**2), 2)} MB")
        elif c == "4":
            pid_str = input("Enter PID to terminate: ").strip()
            if pid_str.isdigit():
                try:
                    p = psutil.Process(int(pid_str))
                    p.terminate()
                    print(f"{Fore.GREEN}[+] Process {pid_str} terminated successfully.")
                except Exception as e:
                    print(f"{Fore.RED}[-] Failed: {e}")
        elif c == "0":
            break
