import os
from .common import AutoStopTimer
class OnionShare(object):
    def __init__(self, common, onion, local_only=False, autostop_timer=0):
        self.common = common
        self.common.log("OnionShare", "__init__")
        self.onion = onion
        self.hidserv_dir = None
        self.onion_host = None
        self.port = None
        self.local_only = local_only
        self.autostop_timer = autostop_timer
        self.autostop_timer_thread = None
    def choose_port(self):
        try:
            self.port = self.common.get_available_port(17600, 17650)
        except Exception:
            raise OSError("OnionShare uchun mavjud port topilmadi")
    def start_onion_service(self, mode, mode_settings, await_publication=True):
        self.common.log("OnionShare", "start_onion_service")
        if not self.port:
            self.choose_port()
        if self.autostop_timer > 0:
            self.autostop_timer_thread = AutoStopTimer(self.common, self.autostop_timer)
        if self.local_only:
            self.onion_host = f"127.0.0.1:{self.port}"
            if not mode_settings.get("general", "public"):
                self.auth_string = (
                    "E2GOT5LTUTP3OAMRCRXO4GSH6VKJEUOXZQUC336SRKAHTTT5OVSA"
                )
            return
        self.onion_host = self.onion.start_onion_service(
            mode, mode_settings, self.port, await_publication
        )
        if not mode_settings.get("general", "public"):
            self.auth_string = self.onion.auth_string
    def stop_onion_service(self, mode_settings):
        self.onion.stop_onion_service(mode_settings)