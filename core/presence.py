import time
import threading
from pypresence import Presence

DEFAULT_APP_ID = "1556241281733107733"

class DiscordRPC:
    def __init__(self, client_id=DEFAULT_APP_ID):
        self.client_id = client_id
        self.rpc = None
        self.start_time = int(time.time())
        self.running = False
        self.current_details = "Running ROOT//X Toolkit"
        self.current_state = "License: Active"

    def start(self, tier="Platinum", distro="Linux"):
        self.current_state = f"Tier: {tier} ({distro})"
        self.current_details = "Managing Server & Diagnostics"

        def _worker():
            self.running = True
            while self.running:
                try:
                    if self.rpc is None:
                        self.rpc = Presence(self.client_id)
                        self.rpc.connect()

                    self.rpc.update(
                        state=self.current_state,
                        details=self.current_details,
                        start=self.start_time,
                        large_image="rootx_logo",
                        large_text="ROOT//X Products Ecosystem",
                        small_image="verified_badge",
                        small_text=f"Verified License [{tier}]",
                        buttons=[
                            {"label": "Join Discord Server", "url": "https://discord.gg/rootx"},
                            {"label": "Get License", "url": "https://discord.com/channels/1531449593118724197"}
                        ]
                    )
                except Exception:
                    # Discord might not be running or restarted; wait and reconnect
                    self.rpc = None
                time.sleep(15)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def update_status(self, details=None, state=None):
        if details:
            self.current_details = details
        if state:
            self.current_state = state
        if self.rpc:
            try:
                self.rpc.update(
                    state=self.current_state,
                    details=self.current_details,
                    start=self.start_time,
                    large_image="rootx_logo",
                    large_text="ROOT//X Products Ecosystem",
                    small_image="verified_badge",
                    small_text="Verified License Holder",
                    buttons=[
                        {"label": "Join Discord Server", "url": "https://discord.gg/rootx"},
                        {"label": "Get License", "url": "https://discord.com/channels/1531449593118724197"}
                    ]
                )
            except Exception:
                pass

    def stop(self):
        self.running = False
        if self.rpc:
            try:
                self.rpc.close()
            except Exception:
                pass
            self.rpc = None
