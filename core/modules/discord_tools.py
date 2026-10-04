import requests
from colorama import Fore

def run_discord_tools():
    while True:
        print(f"\n{Fore.CYAN}=== ROOT//X Discord Developer Tools ===")
        print(f"{Fore.WHITE}[1] Send Webhook Message / Embed")
        print(f"{Fore.WHITE}[2] Discord Snowflake Timestamp Decoder")
        print(f"{Fore.WHITE}[3] Bot Token Info / Health Check")
        print(f"{Fore.WHITE}[0] Back to Main Menu\n")

        c = input(f"{Fore.WHITE}Select Option: ").strip()
        if c == "1":
            wh_url = input("Webhook URL: ").strip()
            content = input("Message Content: ").strip()
            try:
                r = requests.post(wh_url, json={"content": content, "username": "ROOT//X Toolkit"}, timeout=5)
                if r.status_code in [200, 204]:
                    print(f"{Fore.GREEN}[+] Webhook message dispatched successfully.")
                else:
                    print(f"{Fore.RED}[-] Discord API error {r.status_code}: {r.text}")
            except Exception as e:
                print(f"{Fore.RED}[-] Webhook dispatch failed: {e}")
        elif c == "2":
            sf_str = input("Enter Discord ID (Snowflake): ").strip()
            if sf_str.isdigit():
                sf = int(sf_str)
                ts = ((sf >> 22) + 1420070400000) / 1000
                import datetime
                dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
                print(f"{Fore.GREEN}[+] Creation Date (UTC): {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        elif c == "3":
            tok = input("Bot Token: ").strip()
            try:
                r = requests.get("https://discord.com/api/v10/users/@me", headers={"Authorization": f"Bot {tok}"}, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    print(f"{Fore.GREEN}[+] Valid Bot Token! Bot: {data.get('username')}#{data.get('discriminator')} (ID: {data.get('id')})")
                else:
                    print(f"{Fore.RED}[-] Invalid Token (HTTP {r.status_code})")
            except Exception as e:
                print(f"{Fore.RED}[-] Verification error: {e}")
        elif c == "0":
            break
