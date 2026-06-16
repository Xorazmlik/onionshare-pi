import os
import subprocess
import time
class Meek(object):
    def __init__(self, common, get_tor_paths=None):
        self.common = common
        self.common.log("Meek", "__init__")
        if not get_tor_paths:
            get_tor_paths = self.common.get_tor_paths
        (
            self.tor_path,
            self.tor_geo_ip_file_path,
            self.tor_geo_ipv6_file_path,
            self.obfs4proxy_file_path,
            self.snowflake_file_path,
            self.meek_client_file_path,
        ) = get_tor_paths()
        self.meek_proxies = {}
        self.meek_url = "https://1723079976.rsc.cdn77.org/"
        self.meek_front = "www.phpmyadmin.net"
        self.meek_env = {
            "TOR_PT_MANAGED_TRANSPORT_VER": "1",
            "TOR_PT_CLIENT_TRANSPORTS": "meek",
        }
        self.meek_host = "127.0.0.1"
        self.meek_port = None
    def start(self):
        if self.meek_client_file_path is None or not os.path.exists(
            self.meek_client_file_path
        ):
            raise MeekNotFound(self.common)
        self.common.log("Meek", "start", "Meek mijoz ishga tushirilmoqda")
        if self.common.platform == "Windows":
            env = os.environ.copy()
            for key in self.meek_env:
                env[key] = self.meek_env[key]
            self.meek_proc = subprocess.Popen(
                [
                    self.meek_client_file_path,
                    "--url",
                    self.meek_url,
                    "--front",
                    self.meek_front,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                env=env,
                text=True,
            )
        else:
            self.meek_proc = subprocess.Popen(
                [
                    self.meek_client_file_path,
                    "--url",
                    self.meek_url,
                    "--front",
                    self.meek_front,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                env=self.meek_env,
                universal_newlines=True,
            )
        for line in iter(self.meek_proc.stdout.readline, ""):
            if "CMETHOD meek socks5" in line:
                self.meek_host = line.split(" ")[3].split(":")[0]
                self.meek_port = line.split(" ")[3].split(":")[1]
                self.common.log(
                    "Meek",
                    "start",
                    f"Meek quyidagi manzilda ishlayapti {self.meek_host}:{self.meek_port}",
                )
                break
            if "CMETHOD-ERROR" in line:
                self.cleanup()
                raise MeekNotRunning(self.common, line)
                break
        if self.meek_port:
            self.meek_proxies = {
                "http": f"socks5h://{self.meek_host}:{self.meek_port}",
                "https": f"socks5h://{self.meek_host}:{self.meek_port}",
            }
        else:
            self.cleanup()
            raise MeekNotRunning(self.common, "Meek portini olish mumkin bo'lmadi")
    def cleanup(self):
        self.common.log("Meek", "cleanup")
        if self.meek_proc:
            self.meek_proc.terminate()
            time.sleep(0.2)
            if self.meek_proc.poll() is None:
                self.common.log(
                    "Meek",
                    "cleanup",
                    "Meek mijoz jarayonini to'xtatishga urindik, lekin u hanuzgacha ishlamoqda",
                )
                try:
                    self.meek_proc.kill()
                    time.sleep(0.2)
                    if self.meek_proc.poll() is None:
                        self.common.log(
                            "Meek",
                            "cleanup",
                            "Meek mijoz jarayonini majburan o'ldirishga urindik, lekin u hanuzgacha ishlamoqda",
                        )
                except Exception:
                    self.common.log(
                        "Meek", "cleanup", "Meek mijoz jarayonini to'xtatishda xato yuz berdi"
                    )
            self.meek_proc = None
            self.meek_proxies = {}
            self.meek_port = None
class MeekNotRunning(Exception):
    def __init__(self, common, info=None):
        self.common = common
        msg = "Meek ishga tushishda xato yuz berdi"
        if info:
            msg = msg + f": {info}"
        self.common.log("MeekNotRunning", "__init__", msg)
class MeekNotFound(Exception):
    def __init__(self, common):
        self.common = common
        self.common.log("MeekNotFound", "__init__", "Meek ijrochisi topilmadi")