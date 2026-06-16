import requests
class CensorshipCircumventionError(Exception):
    pass
class CensorshipCircumvention(object):
    def __init__(self, common, meek=None, onion=None):
        self.common = common
        self.common.log("CensorshipCircumvention", "__init__")
        self.api_proxies = {}
        if meek:
            self.meek = meek
            self.common.log(
                "CensorshipCircumvention",
                "__init__",
                "Meek CensorshipCircumvention API bilan ishlatilmoqda",
            )
            self.api_proxies = self.meek.meek_proxies
        if onion:
            self.onion = onion
            if not self.onion.is_authenticated:
                return False
            else:
                self.common.log(
                    "CensorshipCircumvention",
                    "__init__",
                    "Tor CensorshipCircumvention API bilan ishlatilmoqda",
                )
                (socks_address, socks_port) = self.onion.get_tor_socks_port()
                self.api_proxies = {
                    "http": f"socks5h://{socks_address}:{socks_port}",
                    "https": f"socks5h://{socks_address}:{socks_port}",
                }
    def request_map(self, country=False):
        self.common.log("CensorshipCircumvention", "request_map", f"country={country}")
        if not self.api_proxies:
            return False
        endpoint = "https://bridges.torproject.org/moat/circumvention/map"
        data = {}
        if country:
            data = {"country": country}
        try:
            r = requests.post(
                endpoint,
                json=data,
                headers={"Content-Type": "application/vnd.api+json"},
                proxies=self.api_proxies,
            )
            if r.status_code != 200:
                self.common.log(
                    "CensorshipCircumvention",
                    "request_map",
                    f"status_code={r.status_code}",
                )
                return False
            result = r.json()
            if "errors" in result:
                self.common.log(
                    "CensorshipCircumvention",
                    "request_map",
                    f"errors={result['errors']}",
                )
                return False
            return result
        except requests.exceptions.RequestException as e:
            raise CensorshipCircumventionError(e)
    def request_settings(self, country=False, transports=False):
        self.common.log(
            "CensorshipCircumvention",
            "request_settings",
            f"country={country}, transports={transports}",
        )
        if not self.api_proxies:
            return False
        endpoint = "https://bridges.torproject.org/moat/circumvention/settings"
        data = {}
        if country:
            self.common.log(
                "CensorshipCircumvention",
                "request_settings",
                f"Mamlakat uchun ko'priklar olinmoqda: {country}",
            )
            data = {"country": country}
        if transports:
            data.append({"transports": transports})
        try:
            r = requests.post(
                endpoint,
                json=data,
                headers={"Content-Type": "application/vnd.api+json"},
                proxies=self.api_proxies,
            )
            if r.status_code != 200:
                self.common.log(
                    "CensorshipCircumvention",
                    "request_settings",
                    f"status_code={r.status_code}",
                )
                return False
            result = r.json()
            self.common.log(
                "CensorshipCircumvention",
                "request_settings",
                f"result={result}",
            )
            if "errors" in result:
                self.common.log(
                    "CensorshipCircumvention",
                    "request_settings",
                    f"errors={result['errors']}",
                )
                return False
            if not "settings" in result or result["settings"] is None:
                self.common.log(
                    "CensorshipCircumvention",
                    "request_settings",
                    "No settings found for this country",
                )
                return False
            return result
        except requests.exceptions.RequestException as e:
            raise CensorshipCircumventionError(e)
    def request_builtin_bridges(self):
        if not self.api_proxies:
            return False
        endpoint = "https://bridges.torproject.org/moat/circumvention/builtin"
        try:
            r = requests.post(
                endpoint,
                headers={"Content-Type": "application/vnd.api+json"},
                proxies=self.api_proxies,
            )
            if r.status_code != 200:
                self.common.log(
                    "CensorshipCircumvention",
                    "request_builtin_bridges",
                    f"status_code={r.status_code}",
                )
                return False
            result = r.json()
            if "errors" in result:
                self.common.log(
                    "CensorshipCircumvention",
                    "request_builtin_bridges",
                    f"errors={result['errors']}",
                )
                return False
            return result
        except requests.exceptions.RequestException as e:
            raise CensorshipCircumventionError(e)
    def save_settings(self, settings, bridge_settings):
        self.common.log(
            "CensorshipCircumvention",
            "save_settings",
            f"ko'prik_sozlamalari: {bridge_settings}",
        )
        bridges_ok = False
        self.settings = settings
        if bridge_settings.get("settings", False):
            for returned_bridge_settings in bridge_settings["settings"]:
                if returned_bridge_settings.get("bridges", False):
                    bridges = returned_bridge_settings["bridges"]
                    bridge_strings = bridges["bridge_strings"]
                    self.settings.set("bridges_type", "custom")
                    bridges_checked = self.common.check_bridges_valid(bridge_strings)
                    if bridges_checked:
                        self.settings.set("bridges_custom", "\n".join(bridges_checked))
                        bridges_ok = True
                        break
        if bridges_ok:
            self.common.log(
                "CensorshipCircumvention",
                "save_settings",
                "Avtomatik olingan ko'priklar bilan sozlamalar saqlanmoqda",
            )
            self.settings.set("bridges_enabled", True)
            self.settings.save()
            return True
        else:
            self.common.log(
                "CensorshipCircumvention",
                "save_settings",
                "Olingan ko'priklardan hech birini ishlatib bo'lmadi.",
            )
            return False
    def request_default_bridges(self):
        if not self.api_proxies:
            return False
        endpoint = "https://bridges.torproject.org/moat/circumvention/defaults"
        try:
            r = requests.get(
                endpoint,
                headers={"Content-Type": "application/vnd.api+json"},
                proxies=self.api_proxies,
            )
            if r.status_code != 200:
                self.common.log(
                    "CensorshipCircumvention",
                    "request_default_bridges",
                    f"status_code={r.status_code}",
                )
                return False
            result = r.json()
            if "errors" in result:
                self.common.log(
                    "CensorshipCircumvention",
                    "request_default_bridges",
                    f"errors={result['errors']}",
                )
                return False
            return result
        except requests.exceptions.RequestException as e:
            raise CensorshipCircumventionError(e)