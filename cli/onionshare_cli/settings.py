import json
import os
import locale
class Settings(object):
    def __init__(self, common, config=False):
        self.common = common
        self.common.log("Settings", "__init__")
        if config:
            if os.path.isfile(config):
                self.filename = config
            else:
                self.common.log(
                    "Settings",
                    "__init__",
                    "Berilgan sozlamalar fayli mavjud emas yoki o‘qib bo‘lmaydi. Standart joyga qaytiladi",
                )
                self.filename = self.build_filename()
        else:
            self.filename = self.build_filename()
        self.available_locales = {
            "af": "Afrikaans",
            "sq": "Shqip",
            "ar": "العربية",
            "be": "Беларуская",
            "bn": "বাংলা",
            "bg": "Български",
            "ca": "Català",
            "zh_Hant": "正體中文 (繁體)",
            "zh_Hans": "中文 (简体)",
            "hr": "Hrvatski",
            "cs": "čeština",
            "da": "Dansk",
            "en": "English",
            "fi": "Suomi",
            "fr": "Français",
            "gl": "Galego",
            "de": "Deutsch",
            "el": "Ελληνικά",
            "is": "Íslenska",
            "ga": "Gaeilge",
            "it": "Italiano",
            "ja": "日本語",
            "km": "ខ្មែរ",
            "lt": "Lietuvių Kalba",
            "nb_NO": "Norsk Bokmål",
            "fa": "فارسی",
            "pl": "Polski",
            "pt_BR": "Português (Brasil)",
            "pt_PT": "Português (Portugal)",
            "ru": "Русский",
            "sn": "chiShona",
            "sk": "Slovenčina",
            "es": "Español",
            "sw": "Kiswahili",
            "sv": "Svenska",
            "ta": "Tamil",
            "tr": "Türkçe",
            "uk": "Українська",
            "vi": "Tiếng Việt",
        }
        self.default_settings = {
            "version": self.common.version,
            "connection_type": "bundled",
            "control_port_address": "127.0.0.1",
            "control_port_port": 9051,
            "socks_address": "127.0.0.1",
            "socks_port": 9050,
            "socket_file_path": "/var/run/tor/control",
            "auth_type": "no_auth",
            "auth_password": "",
            "auto_connect": False,
            "use_autoupdate": True,
            "autoupdate_timestamp": None,
            "bridges_enabled": False,
            "bridges_type": "built-in",
            "bridges_builtin_pt": "obfs4",
            "bridges_moat": "",
            "bridges_custom": "",
            "bridges_builtin": {},
            "persistent_tabs": [],
            "locale": None,
            "theme": 0,
        }
        self._settings = {}
        self.fill_in_defaults()
    def fill_in_defaults(self):
        for key in self.default_settings:
            if key not in self._settings:
                self._settings[key] = self.default_settings[key]
        if self._settings["locale"] is None:
            language_code, encoding = locale.getlocale()
            if not language_code:
                language_code = "en_US"
            if language_code == "pt_PT" and language_code == "pt_BR":
                default_locale = language_code
            else:
                default_locale = language_code[:2]
            if default_locale not in self.available_locales:
                default_locale = "en"
            self._settings["locale"] = default_locale
    def build_filename(self):
        return os.path.join(self.common.build_data_dir(), "onionshare.json")
    def load(self):
        self.common.log("Settings", "load")
        if os.path.exists(self.filename):
            try:
                self.common.log("Settings", "load", f"{self.filename} ni yuklashga harakat qilinyapti")
                with open(self.filename, "r") as f:
                    self._settings = json.load(f)
                    self.fill_in_defaults()
            except Exception:
                pass
        try:
            os.makedirs(self.get("data_dir"), exist_ok=True)
        except Exception:
            pass
    def save(self):
        self.common.log("Settings", "save")
        open(self.filename, "w").write(json.dumps(self._settings, indent=2))
        self.common.log("Settings", "save", f"Sozlamalar {self.filename} ga saqlandi")
    def get(self, key):
        return self._settings[key]
    def set(self, key, val):
        if key == "control_port_port" or key == "socks_port":
            try:
                val = int(val)
            except Exception:
                if key == "control_port_port":
                    val = self.default_settings["control_port_port"]
                elif key == "socks_port":
                    val = self.default_settings["socks_port"]
        self._settings[key] = val