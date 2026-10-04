import socket
import requests
import time
from colorama import Fore

def run_network_tools():
    while True:
        print(f"\n{Fore.CYAN}=== ROOT//X Network & Diagnostics Suite ===")
        print(f"{Fore.WHITE}[1] TCP Port Scanner")
        print(f"{Fore.WHITE}[2] Domain DNS Resolver")
        print(f"{Fore.WHITE}[3] HTTP/HTTPS Endpoint Status Checker")
        print(f"{Fore.WHITE}[4] Public IP & Geo Information")
        print(f"{Fore.WHITE}[0] Back to Main Menu\n")

        c = input(f"{Fore.WHITE}Select Option: ").strip()
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
        elif c == "0":
            break
