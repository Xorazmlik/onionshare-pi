import os
import json
import platform
class ModeSettings:
    def __init__(self, common, filename=None, id=None):
        self.common = common
        self.default_settings = {
            "onion": {
                "private_key": None,
                "client_auth_priv_key": None,
                "client_auth_pub_key": None,
            },
            "persistent": {
                "mode": None,
                "enabled": False,
                "autostart_on_launch": False,
            },
            "general": {
                "title": None,
                "public": False,
                "autostart_timer": False,
                "autostop_timer": False,
                "service_id": None,
                "qr": False,
            },
            "share": {
                "autostop_sharing": True,
                "filenames": [],
                "log_filenames": False,
            },
            "receive": {
                "data_dir": self.build_default_receive_data_dir(),
                "webhook_url": None,
                "disable_text": False,
                "disable_files": False,
            },
            "website": {
                "disable_csp": False,
                "custom_csp": None,
                "log_filenames": False,
                "filenames": [],
            },
            "chat": {},
        }
        self._settings = {}
        self.just_created = False
        if id:
            self.id = id
        else:
            self.id = self.common.build_password(3)
        self.load(filename)
    def fill_in_defaults(self):
        for key in self.default_settings:
            if key in self._settings:
                for inner_key in self.default_settings[key]:
                    if inner_key not in self._settings[key]:
                        self._settings[key][inner_key] = self.default_settings[key][
                            inner_key
                        ]
            else:
                self._settings[key] = self.default_settings[key]
    def get(self, group, key):
        return self._settings[group][key]
    def set(self, group, key, val):
        self._settings[group][key] = val
        self.common.log(
            "ModeSettings",
            "set",
            f"yangilanmoqda {self.id}: {group}.{key} = {val}",
        )
        self.save()
    def build_default_receive_data_dir(self):
        if self.common.platform == "Darwin":
            import pwd
            real_homedir = pwd.getpwuid(os.getuid()).pw_dir
            return os.path.join(real_homedir, "OnionShare")
        elif self.common.platform == "Windows":
            return os.path.expanduser("~\\OnionShare")
        else:
            return os.path.expanduser("~/OnionShare")
    def load(self, filename=None):
        if filename:
            self.filename = filename
        else:
            self.filename = os.path.join(
                self.common.build_persistent_dir(), f"{self.id}.json"
            )
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    self._settings = json.load(f)
                    self.fill_in_defaults()
                    self.common.log("ModeSettings", "load", f"yuklandi {self.filename}")
                    return
            except Exception:
                pass
        self.common.log("ModeSettings", "load", f"yaratilmoqda {self.filename}")
        self.fill_in_defaults()
        self.just_created = True
    def save(self):
        if not self.get("persistent", "enabled"):
            return
        if self.filename:
            with open(self.filename, "w") as file:
                file.write(json.dumps(self._settings, indent=2))
    def delete(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)