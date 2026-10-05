import os
import sys

# Ensure root directory is in sys.path
pkg_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(pkg_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

try:
    import main as rootx_main
    def main():
        rootx_main.main()
except ImportError:
    # If called as rootx package
    from core.license_guard import check_license_interactive
    from core.presence import DiscordRPC
    from core.system_info import get_system_summary
    from core.modules.server_manager import run_server_manager
    from core.modules.network_tools import run_network_tools
    from core.modules.security_audit import run_security_audit
    from core.modules.discord_tools import run_discord_tools

    import main as rootx_main
    def main():
        rootx_main.main()

if __name__ == "__main__":
    main()
