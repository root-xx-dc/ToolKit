import os
import sys
import socket
import requests
import time
import subprocess
import platform
import psutil
from colorama import Fore, Style

DNS_PROVIDERS = [
    {"name": "Cloudflare DNS (Ultra-Fast & Private)", "primary": "1.1.1.1", "secondary": "1.0.0.1"},
    {"name": "Google Public DNS (Global & Reliable)", "primary": "8.8.8.8", "secondary": "8.8.4.4"},
    {"name": "Quad9 Security (Malware Blocking)", "primary": "9.9.9.9", "secondary": "149.112.112.112"},
    {"name": "OpenDNS Home", "primary": "208.67.222.222", "secondary": "208.67.220.220"}
]

def benchmark_dns_servers():
    print(f"\n{Fore.YELLOW}[*] Benchmarking DNS response times...{Style.RESET_ALL}")
    results = []
    for provider in DNS_PROVIDERS:
        latencies = []
        for _ in range(3):
            try:
                start = time.time()
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(1.5)
                s.connect((provider["primary"], 53))
                latencies.append((time.time() - start) * 1000)
                s.close()
            except Exception:
                pass
        
        avg_lat = round(sum(latencies) / len(latencies), 1) if latencies else 999.0
        results.append((provider, avg_lat))
        
        status_color = Fore.GREEN if avg_lat < 30 else (Fore.YELLOW if avg_lat < 70 else Fore.RED)
        print(f"  {Fore.WHITE}{provider['name']:<42} {Fore.CYAN}{provider['primary']:<15} {status_color}{avg_lat:>6} ms{Style.RESET_ALL}")

    results.sort(key=lambda x: x[1])
    fastest = results[0][0]
    print(f"\n{Fore.GREEN}[+] Fastest DNS: {fastest['name']} ({fastest['primary']}){Style.RESET_ALL}")
    return fastest

def flush_dns_cache():
    print(f"\n{Fore.YELLOW}[*] Flushing DNS Resolver Cache...{Style.RESET_ALL}")
    try:
        if os.name == "nt":
            subprocess.run(["ipconfig", "/flushdns"], check=True, capture_output=True)
            print(f"{Fore.GREEN}[+] Windows DNS Cache flushed successfully.{Style.RESET_ALL}")
        elif platform.system() == "Darwin":
            subprocess.run(["dscacheutil", "-flushcache"], check=True)
            subprocess.run(["killall", "-HUP", "mDNSResponder"], check=False)
            print(f"{Fore.GREEN}[+] macOS DNS Cache flushed successfully.{Style.RESET_ALL}")
        else:
            subprocess.run(["systemd-resolve", "--flush-caches"], check=False)
            print(f"{Fore.GREEN}[+] Linux DNS Cache flush signal sent.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[-] Could not flush DNS cache: {e}{Style.RESET_ALL}")

def clean_system_memory():
    print(f"\n{Fore.CYAN}[*] Analyzing system memory & process cache...{Style.RESET_ALL}")
    mem_before = psutil.virtual_memory()
    print(f"  Memory in use: {Fore.YELLOW}{mem_before.percent}% ({mem_before.used // (1024*1024)} MB / {mem_before.total // (1024*1024)} MB){Style.RESET_ALL}")
    
    if os.name == "nt":
        flush_dns_cache()
    
    time.sleep(0.5)
    mem_after = psutil.virtual_memory()
    print(f"{Fore.GREEN}[+] Optimization complete. Active available RAM: {Fore.CYAN}{mem_after.available // (1024*1024)} MB{Style.RESET_ALL}")

def run_network_tools():
    while True:
        print(f"\n{Fore.CYAN}=== ROOT//X Network & Diagnostics Suite ===")
        print(f"{Fore.WHITE}[1] TCP Port Scanner")
        print(f"{Fore.WHITE}[2] Domain DNS Resolver")
        print(f"{Fore.WHITE}[3] HTTP/HTTPS Endpoint Status Checker")
        print(f"{Fore.WHITE}[4] Public IP & Geo Information")
        print(f"{Fore.WHITE}[5] ⚡ DNS Benchmark & 1-Click Cache Cleaner")
        print(f"{Fore.WHITE}[6] 🧹 System Memory & Network Cache Cleaner")
        print(f"{Fore.WHITE}[0] Back to Main Menu\n")

        c = input(f"{Fore.WHITE}Select Option: {Style.RESET_ALL}").strip()
        if c == "1":
            target = input("Target Host/IP: ").strip()
            ports_input = input("Ports to scan (e.g. 22,80,443,3306,8080): ").strip()
            ports = [int(p.strip()) for p in ports_input.split(",") if p.strip().isdigit()]
            if not ports:
                ports = [21, 22, 80, 443, 3306, 8080, 5432, 27017]
            print(f"\n{Fore.YELLOW}[*] Scanning {target} on {len(ports)} ports...")
            for port in ports:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.0)
                result = s.connect_ex((target, port))
                if result == 0:
                    print(f"{Fore.GREEN}[+] Port {port:<6} OPEN")
                else:
                    print(f"{Fore.RED}[-] Port {port:<6} CLOSED")
                s.close()
        elif c == "2":
            domain = input("Domain name (e.g. rootx.com): ").strip()
            try:
                ip = socket.gethostbyname(domain)
                print(f"{Fore.GREEN}[+] Resolved {domain} -> {ip}")
            except Exception as e:
                print(f"{Fore.RED}[-] Resolution failed: {e}")
        elif c == "3":
            url = input("URL to check (e.g. https://google.com): ").strip()
            if not url.startswith("http"):
                url = "https://" + url
            try:
                start = time.time()
                res = requests.get(url, timeout=5)
                latency = round((time.time() - start) * 1000, 1)
                print(f"{Fore.GREEN}[+] Status Code: {res.status_code} | Latency: {latency} ms | Server: {res.headers.get('Server', 'Unknown')}")
            except Exception as e:
                print(f"{Fore.RED}[-] Request failed: {e}")
        elif c == "4":
            try:
                res = requests.get("https://ipapi.co/json/", timeout=5).json()
                print(f"\n{Fore.GREEN}Public IP:{Fore.WHITE} {res.get('ip')}")
                print(f"{Fore.GREEN}City / Region:{Fore.WHITE} {res.get('city')}, {res.get('region')}")
                print(f"{Fore.GREEN}Country:{Fore.WHITE} {res.get('country_name')}")
                print(f"{Fore.GREEN}ISP / Org:{Fore.WHITE} {res.get('org')}")
            except Exception as e:
                print(f"{Fore.RED}[-] Could not fetch geo info: {e}")
        elif c == "5":
            benchmark_dns_servers()
            flush_choice = input(f"\n{Fore.WHITE}Flush system DNS cache now? [Y/n]: ").strip().lower()
            if flush_choice in ["", "y", "yes", "t", "tak"]:
                flush_dns_cache()
        elif c == "6":
            clean_system_memory()
        elif c == "0":
            break

