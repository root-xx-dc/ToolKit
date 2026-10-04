# ROOT//X Advanced Toolkit

Official, cross-platform system, network, and diagnostics toolkit for the **ROOT//X Ecosystem**.

## Features
- **Discord Rich Presence (RPC):** Displays real-time license status, tier, and live activity on Discord (App ID `1556241281733107733`).
- **Cryptographic License Guard:** Real-time HWID fingerprinting and Gist license authentication.
- **Server & Process Management:** CPU/RAM/Disk metrics, top resource consumers, process control.
- **Network Suite:** TCP port scanner, DNS resolution, latency & HTTP header inspection.
- **Security & Port Auditor:** Local listening port scanner, password entropy validator.
- **Discord Developer Tools:** Webhook dispatching, snowflake decoder, bot token health checking.

---

## Installation & Running

### Linux (Arch, Ubuntu, Mint, Debian, Gentoo, Fedora)
```bash
# Clone the repository
git clone https://github.com/root-xx-dc/ToolKit.git
cd ToolKit

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch Toolkit
python3 main.py
```

### Windows (PowerShell / Command Prompt)
```powershell
git clone https://github.com/root-xx-dc/ToolKit.git
cd ToolKit

python -m venv venv
.\venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

---

## Building Standalone Native Binaries (Closed-Source Distribution)

### Linux ELF Binary
```bash
chmod +x build_scripts/build_linux.sh
./build_scripts/build_linux.sh
```

### Windows Executable (.exe)
```cmd
build_scripts\build_windows.bat
```

---

## License & Authorization
A valid license key is required to access the toolkit modules. Keys are issued automatically upon purchase or via Discord slash commands.
