from .censorship import CensorshipCircumvention
from .meek import Meek
from stem.control import Controller
from stem import ProtocolError, SocketClosed
from stem.connection import MissingPassword, UnreadableCookieFile, AuthenticationFailure
import base64
import nacl.public
import os
import psutil
import re
import shlex
import subprocess
import tempfile
import time
import traceback
from packaging.version import Version
class TorErrorAutomatic(Exception):
    pass
class TorErrorInvalidSetting(Exception):
    pass
class TorErrorSocketPort(Exception):
    pass
class TorErrorSocketFile(Exception):
    pass
class TorErrorMissingPassword(Exception):
    pass
class TorErrorUnreadableCookieFile(Exception):
    pass
class TorErrorAuthError(Exception):
    pass
class TorErrorProtocolError(Exception):
    pass
class TorTooOldEphemeral(Exception):
    pass
class TorTooOldStealth(Exception):
    pass
class BundledTorTimeout(Exception):
    pass
class BundledTorCanceled(Exception):
    pass
class BundledTorBroken(Exception):
    pass
class PortNotAvailable(Exception):
    pass
class Onion(object):
    def __init__(self, common, use_tmp_dir=False, get_tor_paths=None):
        self.common = common
        self.common.log("Onion", "__init__")
        self.use_tmp_dir = use_tmp_dir
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
        self.tor_proc = None
        self.c = None
        self.connected_to_tor = False
        self.auth_string = None
        self.graceful_close_onions = []
    def key_str(self, key):
        key_bytes = bytes(key)
        key_b32 = base64.b32encode(key_bytes)
        assert key_b32[-4:] == b"===="
        key_b32 = key_b32[:-4]
        s = key_b32.decode("utf-8")
        return s
    def connect(
        self,
        custom_settings=None,
        config=None,
        tor_status_update_func=None,
        connect_timeout=120,
        local_only=False,
    ):
        if local_only:
            self.common.log("Onion", "connect", "--local-only, Tor o'tkazib yuborilmoqda")
            return
        if custom_settings:
            self.settings = custom_settings
        elif config:
            self.common.load_settings(config)
            self.settings = self.common.settings
        else:
            self.common.load_settings()
            self.settings = self.common.settings
        self.common.log("Onion", "connect", f"connection_type={self.settings.get('connection_type')}")
        self.c = None
        if self.settings.get("connection_type") == "bundled":
            if self.use_tmp_dir:
                self.tor_data_directory = tempfile.TemporaryDirectory(dir=self.common.build_tmp_dir())
                self.tor_data_directory_name = self.tor_data_directory.name
            else:
                self.tor_data_directory_name = self.common.build_tor_dir()
            self.common.log("Onion", "connect", f"tor_data_directory_name={self.tor_data_directory_name}")
            with open(self.common.get_resource_path("torrc_template")) as f:
                torrc_template = f.read()
            self.tor_cookie_auth_file = os.path.join(self.tor_data_directory_name, "cookie")
            try:
                self.tor_socks_port = self.common.get_available_port(1000, 65535)
            except Exception:
                print("OnionShare uchun port mavjud emas")
                raise PortNotAvailable()
            self.tor_torrc = os.path.join(self.tor_data_directory_name, "torrc")
            for proc in psutil.process_iter(["pid", "name", "username"]):
                try:
                    cmdline = proc.cmdline()
                    if (
                        cmdline[0] == self.tor_path
                        and cmdline[1] == "-f"
                        and cmdline[2] == self.tor_torrc
                    ):
                        self.common.log("Onion", "connect", "eskirgan tor jarayoni topildi, o'chirilmoqda")
                        proc.terminate()
                        proc.wait()
                        break
                except Exception:
                    pass
            if self.common.platform == "Windows" or self.common.platform == "Darwin":
                torrc_template += "ControlPort {{control_port}}\n"
                try:
                    self.tor_control_port = self.common.get_available_port(1000, 65535)
                except Exception:
                    print("OnionShare uchun port mavjud emas")
                    raise PortNotAvailable()
                self.tor_control_socket = None
            else:
                torrc_template += "ControlSocket {{control_socket}}\n"
                self.tor_control_port = None
                self.tor_control_socket = os.path.join(self.tor_data_directory_name, "control_socket")
            torrc_template = torrc_template.replace("{{data_directory}}", self.tor_data_directory_name)
            torrc_template = torrc_template.replace("{{control_port}}", str(self.tor_control_port))
            torrc_template = torrc_template.replace("{{control_socket}}", str(self.tor_control_socket))
            torrc_template = torrc_template.replace("{{cookie_auth_file}}", self.tor_cookie_auth_file)
            torrc_template = torrc_template.replace("{{geo_ip_file}}", self.tor_geo_ip_file_path)
            torrc_template = torrc_template.replace("{{geo_ipv6_file}}", self.tor_geo_ipv6_file_path)
            torrc_template = torrc_template.replace("{{socks_port}}", str(self.tor_socks_port))
            torrc_template = torrc_template.replace("{{obfs4proxy_path}}", str(self.obfs4proxy_file_path))
            torrc_template = torrc_template.replace("{{snowflake_path}}", str(self.snowflake_file_path))
            with open(self.tor_torrc, "w") as f:
                self.common.log("Onion", "connect", "torrc shablon fayli yozilmoqda")
                f.write(torrc_template)
                if self.settings.get("bridges_enabled"):
                    f.write("\nUseBridges 1\n")
                    if self.settings.get("bridges_type") == "built-in":
                        use_torrc_bridge_templates = False
                        builtin_bridge_type = self.settings.get("bridges_builtin_pt")
                        if self.settings.get("bridges_builtin"):
                            try:
                                for line in self.settings.get("bridges_builtin")[builtin_bridge_type]:
                                    if line.strip() != "":
                                        f.write(f"Bridge {line}\n")
                                self.common.log("Onion", "connect", "O'rnatilgan ko'priklar sozlamalardan yozildi")
                            except KeyError:
                                use_torrc_bridge_templates = True
                        else:
                            use_torrc_bridge_templates = True
                        if use_torrc_bridge_templates:
                            if builtin_bridge_type == "obfs4":
                                with open(self.common.get_resource_path("torrc_template-obfs4")) as o:
                                    f.write(o.read())
                            elif builtin_bridge_type == "meek-azure":
                                with open(self.common.get_resource_path("torrc_template-meek_lite_azure")) as o:
                                    f.write(o.read())
                            elif builtin_bridge_type == "snowflake":
                                with open(self.common.get_resource_path("torrc_template-snowflake")) as o:
                                    f.write(o.read())
                            self.common.log("Onion", "connect", "O'rnatilgan ko'priklar torrc shablonlaridan yozildi")
                    elif self.settings.get("bridges_type") == "moat":
                        for line in self.settings.get("bridges_moat").split("\n"):
                            if line.strip() != "":
                                f.write(f"Bridge {line}\n")
                    elif self.settings.get("bridges_type") == "custom":
                        for line in self.settings.get("bridges_custom").split("\n"):
                            if line.strip() != "":
                                f.write(f"Bridge {line}\n")
            self.common.log("Onion", "connect", f"{self.tor_path} jarayoni ishga tushirilmoqda")
            start_ts = time.time()
            if self.common.platform == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                self.tor_proc = subprocess.Popen(
                    [self.tor_path, "-f", self.tor_torrc],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                )
            else:
                if self.common.is_snapcraft():
                    env = None
                else:
                    env = {"LD_LIBRARY_PATH": os.path.dirname(self.tor_path)}
                self.tor_proc = subprocess.Popen(
                    [self.tor_path, "-f", self.tor_torrc],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                )
            self.common.log("Onion", "connect", f"tor pid: {self.tor_proc.pid}")
            time.sleep(2)
            return_code = self.tor_proc.poll()
            if return_code != None:
                self.common.log("Onion", "connect", f"tor jarayoni erta tugadi: {return_code}")
            self.common.log("Onion", "connect", "tor nazoratchisiga autentifikatsiya qilinmoqda")
            try:
                if self.common.platform == "Windows" or self.common.platform == "Darwin":
                    self.c = Controller.from_port(port=self.tor_control_port)
                    self.c.authenticate()
                else:
                    self.c = Controller.from_socket_file(path=self.tor_control_socket)
                    self.c.authenticate()
            except Exception as e:
                print("OnionShare Torga ulana olmadi:\n{}".format(e.args[0]))
                print(traceback.format_exc())
                raise BundledTorBroken(e.args[0])
            while True:
                try:
                    res = self.c.get_info("status/bootstrap-phase")
                except SocketClosed:
                    raise BundledTorCanceled()
                res_parts = shlex.split(res)
                progress = res_parts[2].split("=")[1]
                summary = res_parts[4].split("=")[1]
                print(f"\rTor tarmog'iga ulanish: {progress}% - {summary}\033[K", end="")
                if callable(tor_status_update_func):
                    if not tor_status_update_func(progress, summary):
                        self.common.log("Onion", "connect", "tor_status_update_func False qaytardi, Torga ulanish bekor qilindi")
                        print()
                        return False
                if summary == "Done":
                    print("")
                    break
                time.sleep(0.2)
                if self.settings.get("bridges_enabled"):
                    if connect_timeout == 120:
                        connect_timeout = 150
                if time.time() - start_ts > connect_timeout:
                    print("")
                    try:
                        self.tor_proc.terminate()
                        print("Torga ulanish juda uzoq davom etmoqda. Ehtimol internetga ulanmagansiz yoki tizim soatingiz noto'g'ri?")
                        raise BundledTorTimeout()
                    except FileNotFoundError:
                        pass
        elif self.settings.get("connection_type") == "automatic":
            automatic_error = "Tor nazoratchisiga ulanib bo'lmadi. Tor Browser (torproject.org saytida) orqa fonda ishga tushirilganmi?"
            found_tor = False
            env_port = os.environ.get("TOR_CONTROL_PORT")
            if env_port:
                try:
                    self.c = Controller.from_port(port=int(env_port))
                    found_tor = True
                except Exception:
                    pass
            else:
                try:
                    ports = [9151, 9153, 9051]
                    for port in ports:
                        self.c = Controller.from_port(port=port)
                        found_tor = True
                except Exception:
                    pass
                socket_file_path = ""
                if not found_tor:
                    try:
                        if self.common.platform == "Darwin":
                            socket_file_path = os.path.expanduser("~/Library/Application Support/TorBrowser-Data/Tor/control.socket")
                        self.c = Controller.from_socket_file(path=socket_file_path)
                        found_tor = True
                    except Exception:
                        pass
            if not found_tor:
                try:
                    if self.common.platform == "Linux" or self.common.platform == "BSD":
                        socket_file_path = f"/run/user/{os.geteuid()}/Tor/control.socket"
                    elif self.common.platform == "Darwin":
                        socket_file_path = f"/run/user/{os.geteuid()}/Tor/control.socket"
                    elif self.common.platform == "Windows":
                        print(automatic_error)
                        raise TorErrorAutomatic()
                    self.c = Controller.from_socket_file(path=socket_file_path)
                except Exception:
                    print(automatic_error)
                    raise TorErrorAutomatic()
            try:
                self.c.authenticate()
            except Exception:
                print(automatic_error)
                raise TorErrorAutomatic()
        else:
            invalid_settings_error = "Sozlamalaringiz mantiqsizligi sababli Tor nazoratchisiga ulanib bo'lmadi."
            try:
                if self.settings.get("connection_type") == "control_port":
                    self.c = Controller.from_port(
                        address=self.settings.get("control_port_address"),
                        port=self.settings.get("control_port_port"),
                    )
                elif self.settings.get("connection_type") == "socket_file":
                    self.c = Controller.from_socket_file(path=self.settings.get("socket_file_path"))
                else:
                    print(invalid_settings_error)
                    raise TorErrorInvalidSetting()
            except Exception:
                if self.settings.get("connection_type") == "control_port":
                    print("Tor nazoratchisiga {}:{} manzilda ulanib bo'lmadi.".format(
                        self.settings.get("control_port_address"),
                        self.settings.get("control_port_port"),
                    ))
                    raise TorErrorSocketPort(
                        self.settings.get("control_port_address"),
                        self.settings.get("control_port_port"),
                    )
                print("Socket fayli {} orqali Tor nazoratchisiga ulanib bo'lmadi.".format(
                    self.settings.get("socket_file_path")
                ))
                raise TorErrorSocketFile(self.settings.get("socket_file_path"))
            try:
                if self.settings.get("auth_type") == "no_auth":
                    self.c.authenticate()
                elif self.settings.get("auth_type") == "password":
                    self.c.authenticate(self.settings.get("auth_password"))
                else:
                    print(invalid_settings_error)
                    raise TorErrorInvalidSetting()
            except MissingPassword:
                print("Tor nazoratchisiga ulandi, lekin autentifikatsiya uchun parol talab etiladi.")
                raise TorErrorMissingPassword()
            except UnreadableCookieFile:
                print("Tor nazoratchisiga ulandi, lekin parol noto'g'ri bo'lishi yoki foydalanuvchingiz cookie faylini o'qiy olmasligi mumkin.")
                raise TorErrorUnreadableCookieFile()
            except AuthenticationFailure:
                print("{}:{} ga ulandi, lekin autentifikatsiyadan o'tolmadi. Balki bu Tor nazoratchisi emas?".format(
                    self.settings.get("control_port_address"),
                    self.settings.get("control_port_port"),
                ))
                raise TorErrorAuthError(
                    self.settings.get("control_port_address"),
                    self.settings.get("control_port_port"),
                )
        self.connected_to_tor = True
        self.tor_version = self.c.get_version().version_str
        self.common.log("Onion", "connect", f"Tor {self.tor_version} ga ulandi")
        list_ephemeral_hidden_services = getattr(self.c, "list_ephemeral_hidden_services", None)
        self.supports_ephemeral = (
            callable(list_ephemeral_hidden_services) and self.tor_version >= "0.2.7.1"
        )
        try:
            res = self.c.create_ephemeral_hidden_service(
                {1: 1},
                basic_auth=None,
                await_publication=False,
                key_type="NEW",
                key_content="ED25519-V3",
                client_auth_v3="E2GOT5LTUTP3OAMRCRXO4GSH6VKJEUOXZQUC336SRKAHTTT5OVSA",
            )
            tmp_service_id = res.service_id
            self.c.remove_ephemeral_hidden_service(tmp_service_id)
            self.supports_stealth = True
        except Exception:
            self.supports_stealth = False
        cleaned_tor_version = re.sub(r"\s*\(.*\)", "", self.tor_version)
        self.supports_v3_onions = Version(cleaned_tor_version) >= Version("0.3.5.7")
        if (
            self.settings.get("bridges_enabled")
            and self.settings.get("bridges_type") == "built-in"
        ):
            self.update_builtin_bridges()
    def is_authenticated(self):
        if self.c is not None:
            return self.c.is_authenticated()
        else:
            return False
    def start_onion_service(self, mode, mode_settings, port, await_publication):
        self.common.log("Onion", "start_onion_service", f"port={port}")
        if not self.supports_ephemeral:
            print("Sizning Tor versiyangiz juda eski — vaqtinchalik (ephemeral) onion xizmatlari qo'llab-quvvatlanmaydi")
            raise TorTooOldEphemeral()
        if mode_settings.get("onion", "private_key"):
            key_content = mode_settings.get("onion", "private_key")
            key_type = "ED25519-V3"
        else:
            key_content = "ED25519-V3"
            key_type = "NEW"
        debug_message = f"key_type={key_type}"
        if key_type == "NEW":
            debug_message += f", key_content={key_content}"
        self.common.log("Onion", "start_onion_service", debug_message)
        if mode_settings.get("general", "public"):
            client_auth_priv_key = None
            client_auth_pub_key = None
        else:
            if not self.supports_stealth:
                print("Sizning Tor versiyangiz juda eski — stealth (maxfiy) onion xizmatlari qo'llab-quvvatlanmaydi")
                raise TorTooOldStealth()
            else:
                if key_type == "NEW" or not mode_settings.get("onion", "client_auth_priv_key"):
                    client_auth_priv_key_raw = nacl.public.PrivateKey.generate()
                    client_auth_priv_key = self.key_str(client_auth_priv_key_raw)
                    client_auth_pub_key = self.key_str(client_auth_priv_key_raw.public_key)
                else:
                    client_auth_priv_key = mode_settings.get("onion", "client_auth_priv_key")
                    client_auth_pub_key = mode_settings.get("onion", "client_auth_pub_key")
        try:
            if not self.supports_stealth:
                res = self.c.create_ephemeral_hidden_service(
                    {80: port},
                    await_publication=await_publication,
                    basic_auth=None,
                    key_type=key_type,
                    key_content=key_content,
                )
            else:
                res = self.c.create_ephemeral_hidden_service(
                    {80: port},
                    await_publication=await_publication,
                    basic_auth=None,
                    key_type=key_type,
                    key_content=key_content,
                    client_auth_v3=client_auth_pub_key,
                )
        except ProtocolError as e:
            print("Tor xatosi: {}".format(e.args[0]))
            raise TorErrorProtocolError(e.args[0])
        onion_host = res.service_id + ".onion"
        if mode == "share":
            self.graceful_close_onions.append(res.service_id)
        mode_settings.set("general", "service_id", res.service_id)
        if not mode_settings.get("onion", "private_key"):
            mode_settings.set("onion", "private_key", res.private_key)
        if not mode_settings.get("general", "public"):
            mode_settings.set("onion", "client_auth_priv_key", client_auth_priv_key)
            mode_settings.set("onion", "client_auth_pub_key", client_auth_pub_key)
            self.auth_string = client_auth_priv_key
        return onion_host
    def stop_onion_service(self, mode_settings):
        onion_host = mode_settings.get("general", "service_id")
        if onion_host:
            self.common.log("Onion", "stop_onion_service", f"onion host: {onion_host}")
            try:
                self.c.remove_ephemeral_hidden_service(mode_settings.get("general", "service_id"))
            except Exception:
                self.common.log("Onion", "stop_onion_service", f"{onion_host} ni o'chirib bo'lmadi")
    def cleanup(self, stop_tor=True, wait=True):
        self.common.log("Onion", "cleanup")
        try:
            onions = self.c.list_ephemeral_hidden_services()
            for service_id in onions:
                onion_host = f"{service_id}.onion"
                try:
                    self.common.log("Onion", "cleanup", f"onion o'chirilmoqda: {onion_host}")
                    self.c.remove_ephemeral_hidden_service(service_id)
                except Exception:
                    self.common.log("Onion", "cleanup", f"{onion_host} ni o'chirib bo'lmadi")
                    pass
        except Exception:
            pass
        if stop_tor:
            if self.tor_proc:
                if wait:
                    try:
                        rendezvous_circuit_ids = []
                        for c in self.c.get_circuits():
                            if (
                                c.purpose == "HS_SERVICE_REND"
                                and c.rend_query in self.graceful_close_onions
                            ):
                                rendezvous_circuit_ids.append(c.id)
                        symbols = list("\\|/-")
                        symbols_i = 0
                        while True:
                            num_rend_circuits = 0
                            for c in self.c.get_circuits():
                                if c.id in rendezvous_circuit_ids:
                                    num_rend_circuits += 1
                            if num_rend_circuits == 0:
                                print("\rTor rendezvous zanjirlari yopildi" + " " * 20)
                                break
                            if num_rend_circuits == 1:
                                circuits = "zanjir"
                            else:
                                circuits = "zanjirlar"
                            print(
                                f"\r{num_rend_circuits} ta Tor rendezvous {circuits} yopilishini kutilyapti {symbols[symbols_i]} ",
                                end="",
                            )
                            symbols_i = (symbols_i + 1) % len(symbols)
                            time.sleep(1)
                    except Exception:
                        pass
                self.tor_proc.terminate()
                time.sleep(0.2)
                if self.tor_proc.poll() is None:
                    self.common.log("Onion", "cleanup", "Tor jarayonini to'xtatishga urinildi, lekin u hali ham ishlayapti")
                    try:
                        self.tor_proc.kill()
                        time.sleep(0.2)
                        if self.tor_proc.poll() is None:
                            self.common.log("Onion", "cleanup", "Tor jarayonini o'ldirish urinildi, lekin u hali ham ishlayapti")
                    except Exception:
                        self.common.log("Onion", "cleanup", "Tor jarayonini o'ldirishda xatolik")
                self.tor_proc = None
            self.connected_to_tor = False
            try:
                if self.use_tmp_dir:
                    self.tor_data_directory.cleanup()
            except Exception:
                pass
    def get_tor_socks_port(self):
        self.common.log("Onion", "get_tor_socks_port")
        if self.settings.get("connection_type") == "bundled":
            return ("127.0.0.1", self.tor_socks_port)
        elif self.settings.get("connection_type") == "automatic":
            return ("127.0.0.1", 9150)
        else:
            return (self.settings.get("socks_address"), self.settings.get("socks_port"))
    def update_builtin_bridges(self):
        builtin_bridges = False
        meek = None
        if self.is_authenticated:
            self.common.log("Onion", "update_builtin_bridges", "O'rnatilgan ko'priklar yangilanmoqda. Avval Tor orqali urinilmoqda")
            self.censorship_circumvention = CensorshipCircumvention(self.common, None, self)
            builtin_bridges = self.censorship_circumvention.request_builtin_bridges()
        if not builtin_bridges:
            self.common.log("Onion", "update_builtin_bridges", "O'rnatilgan ko'priklar yangilanmoqda. Meek orqali urinilmoqda (Torsiz)")
            meek = Meek(self.common)
            meek.start()
            self.censorship_circumvention = CensorshipCircumvention(self.common, meek, None)
            builtin_bridges = self.censorship_circumvention.request_builtin_bridges()
            meek.cleanup()
        if builtin_bridges:
            self.common.log("Onion", "update_builtin_bridges", f"Ko'priklar olindi: {builtin_bridges}")
            self.settings.set("bridges_builtin", builtin_bridges)
            self.settings.save()
        else:
            self.common.log("Onion", "update_builtin_bridges", "O'rnatilgan ko'priklarni olishda xatolik")
            return False
