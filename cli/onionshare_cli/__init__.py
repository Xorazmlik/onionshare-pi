import os
import sys
import time
import argparse
import threading
from datetime import datetime
from datetime import timedelta
from .common import Common, CannotFindTor
from .web import Web
from .onion import TorErrorProtocolError, TorTooOldEphemeral, TorTooOldStealth, Onion
from .onionshare import OnionShare
from .mode_settings import ModeSettings
from qrcode import QRCode
def main(cwd=None):
    common = Common()
    common.display_banner()
    if common.platform == "Darwin":
        if cwd:
            os.chdir(cwd)
    parser = argparse.ArgumentParser(
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=28)
    )
    parser.add_argument("--receive", action="store_true", dest="receive", help="Fayl qabul qilish")
    parser.add_argument("--website", action="store_true", dest="website", help="Veb-sayt nashr etish")
    parser.add_argument("--chat", action="store_true", dest="chat", help="Chat serverini ishga tushirish")
    parser.add_argument("--local-only", action="store_true", dest="local_only", default=False, help="Tor ishlatilmaydi (faqat ishlab chiqish uchun)")
    parser.add_argument("--connect-timeout", metavar="SONIYA", dest="connect_timeout", default=120, help="Torga ulanishdan voz kechish vaqti soniyalarda (standart: 120)")
    parser.add_argument("--config", metavar="FAYL", default=None, help="Maxsus global sozlamalar fayli nomi")
    parser.add_argument("--persistent", metavar="FAYL", default=None, help="Doimiy sessiya fayli nomi")
    parser.add_argument("--title", metavar="SARLAVHA", default=None, help="Sarlavha belgilash")
    parser.add_argument("--public", action="store_true", dest="public", default=False, help="Shaxsiy kalit ishlatilmaydi")
    parser.add_argument("--auto-start-timer", metavar="SONIYA", dest="autostart_timer", default=0, help="Onion xizmatini belgilangan vaqtda ishga tushirish (hozirdan N soniya)")
    parser.add_argument("--auto-stop-timer", metavar="SONIYA", dest="autostop_timer", default=0, help="Onion xizmatini belgilangan vaqtda to'xtatish (hozirdan N soniya)")
    parser.add_argument("--no-autostop-sharing", action="store_true", dest="no_autostop_sharing", default=False, help="Faylni yuborib bo'lgandan keyin ham ulashishni davom ettirish")
    parser.add_argument("--log-filenames", action="store_true", dest="log_filenames", default=False, help="Fayl yuklab olish faoliyatini stdout ga chiqarish")
    parser.add_argument("--qr", action="store_true", dest="qr", default=False, help="Ulashish havolasi uchun QR kodni terminalda ko'rsatish")
    parser.add_argument("--data-dir", metavar="papka", default=None, help="Qabul qilish: fayllarni ushbu papkaga saqlash")
    parser.add_argument("--webhook-url", metavar="url", default=None, help="Qabul qilish: webhook bildirishnomalar uchun URL")
    parser.add_argument("--disable-text", action="store_true", dest="disable_text", help="Qabul qilish: matn xabarlarini qabul qilishni o'chirish")
    parser.add_argument("--disable-files", action="store_true", dest="disable_files", help="Qabul qilish: fayllarni qabul qilishni o'chirish")
    parser.add_argument("--disable_csp", action="store_true", dest="disable_csp", default=False, help="Veb-sayt: standart Content Security Policy sarlavhasini o'chirish")
    parser.add_argument("--custom_csp", metavar="csp", default=None, help="Veb-sayt: maxsus Content Security Policy sarlavhasini belgilash")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="OnionShare xatolarini stdout ga, veb xatolarini diskka chiqarish")
    parser.add_argument("filename", metavar="fayl", nargs="*", help="Ulashiladigan fayllar yoki papkalar ro'yxati")
    args = parser.parse_args()
    filenames = args.filename
    for i in range(len(filenames)):
        filenames[i] = os.path.abspath(filenames[i])
    receive = bool(args.receive)
    website = bool(args.website)
    chat = bool(args.chat)
    local_only = bool(args.local_only)
    connect_timeout = int(args.connect_timeout)
    config_filename = args.config
    persistent_filename = args.persistent
    title = args.title
    public = bool(args.public)
    autostart_timer = int(args.autostart_timer)
    autostop_timer = int(args.autostop_timer)
    autostop_sharing = not bool(args.no_autostop_sharing)
    print_qr = bool(args.qr)
    data_dir = args.data_dir
    webhook_url = args.webhook_url
    disable_text = args.disable_text
    disable_files = args.disable_files
    disable_csp = bool(args.disable_csp)
    custom_csp = args.custom_csp
    log_filenames = bool(args.log_filenames)
    verbose = bool(args.verbose)
    common.verbose = verbose
    if config_filename:
        common.load_settings(config_filename)
    else:
        common.load_settings()
    if persistent_filename:
        mode_settings = ModeSettings(common, persistent_filename)
        mode_settings.set("persistent", "enabled", True)
    else:
        mode_settings = ModeSettings(common)
    if receive:
        mode = "receive"
    elif website:
        mode = "website"
    elif chat:
        mode = "chat"
    else:
        mode = "share"
    if mode_settings.just_created:
        mode_settings.set("general", "title", title)
        mode_settings.set("general", "public", public)
        mode_settings.set("general", "autostart_timer", autostart_timer)
        mode_settings.set("general", "autostop_timer", autostop_timer)
        mode_settings.set("general", "qr", print_qr)
        if persistent_filename:
            mode_settings.set("persistent", "mode", mode)
        if mode == "share":
            mode_settings.set("share", "autostop_sharing", autostop_sharing)
            mode_settings.set("share", "log_filenames", log_filenames)
        if mode == "receive":
            if data_dir:
                mode_settings.set("receive", "data_dir", data_dir)
            if webhook_url:
                mode_settings.set("receive", "webhook_url", webhook_url)
            mode_settings.set("receive", "disable_text", disable_text)
            mode_settings.set("receive", "disable_files", disable_files)
        if mode == "website":
            if disable_csp and custom_csp:
                print("--disable-csp va --custom-csp bir vaqtda ishlatib bo'lmaydi.")
                sys.exit()
            if disable_csp:
                mode_settings.set("website", "disable_csp", True)
                mode_settings.set("website", "custom_csp", None)
            if custom_csp:
                mode_settings.set("website", "custom_csp", custom_csp)
                mode_settings.set("website", "disable_csp", False)
            mode_settings.set("website", "log_filenames", log_filenames)
    else:
        mode = mode_settings.get("persistent", "mode")
    if mode == "share" or mode == "website":
        if persistent_filename and not mode_settings.just_created:
            filenames = mode_settings.get(mode, "filenames")
        else:
            if len(filenames) == 0:
                if persistent_filename:
                    mode_settings.delete()
                print("Fayllar ko'rsatilmagan")
                parser.print_help()
                sys.exit()
            valid = True
            for filename in filenames:
                if not os.path.isfile(filename) and not os.path.isdir(filename):
                    print(f"{filename} mavjud fayl emas.")
                    valid = False
                if not os.access(filename, os.R_OK):
                    print(f"{filename} o'qib bo'lmaydigan fayl.")
                    valid = False
            if not valid:
                sys.exit()
        if persistent_filename:
            mode_settings.set(mode, "filenames", filenames)
    if mode == "receive" and disable_text and disable_files:
        print("Matn va fayllarni bir vaqtda o'chirib bo'lmaydi")
        sys.exit()
    web = Web(common, False, mode_settings, mode)
    try:
        onion = Onion(common, use_tmp_dir=True)
    except CannotFindTor:
        print("OnionShare-dan foydalanish uchun tor o'rnatilishi kerak")
        if common.platform == "Darwin":
            print("macOS da buni Homebrew (https://brew.sh) orqali qilish mumkin:")
            print("  brew install tor")
        sys.exit()
    try:
        onion.connect(
            custom_settings=False,
            config=config_filename,
            connect_timeout=connect_timeout,
            local_only=local_only,
        )
    except KeyboardInterrupt:
        print("")
        sys.exit()
    except Exception:
        sys.exit()
    try:
        common.settings.load()
        if mode == "receive":
            if local_only:
                web.proxies = None
            else:
                (socks_address, socks_port) = onion.get_tor_socks_port()
                web.proxies = {
                    "http": f"socks5h://{socks_address}:{socks_port}",
                    "https": f"socks5h://{socks_address}:{socks_port}",
                }
        app = OnionShare(common, onion, local_only, autostop_timer)
        app.choose_port()
        if autostart_timer > 0:
            if autostop_timer > 0 and autostop_timer < autostart_timer:
                print("Avtomatik to'xtatish vaqti avtomatik boshlash vaqtidan oldin bo'lishi mumkin emas.")
                sys.exit()
            app.start_onion_service(mode, mode_settings, False)
            url = f"http://{app.onion_host}"
            schedule = datetime.now() + timedelta(seconds=autostart_timer)
            if mode == "receive":
                print(f"Yuborilgan fayllar ushbu papkada paydo bo'ladi: {mode_settings.get('receive', 'data_dir')}")
                print("")
                print("Ogohlantirish: Qabul qilish rejimi odamlarga kompyuteringizga fayl yuklash imkonini beradi. Ba'zi fayllar ishonchsiz bo'lishi mumkin.")
                print("")
                if not mode_settings.get("general", "public"):
                    print(f"Ushbu manzil va shaxsiy kalitni jo'natuvchiga bering, va unga quyidagi vaqtgacha ulanib bo'lmasligini ayting: {schedule.strftime('%I:%M:%S%p, %b %d, %y')}")
                    print(f"Shaxsiy kalit: {app.auth_string}")
                else:
                    print(f"Ushbu manzilni jo'natuvchiga bering, va unga quyidagi vaqtgacha ulanib bo'lmasligini ayting: {schedule.strftime('%I:%M:%S%p, %b %d, %y')}")
            else:
                if not mode_settings.get("general", "public"):
                    print(f"Ushbu manzil va shaxsiy kalitni qabul qiluvchiga bering, va unga quyidagi vaqtgacha ulanib bo'lmasligini ayting: {schedule.strftime('%I:%M:%S%p, %b %d, %y')}")
                    print(f"Shaxsiy kalit: {app.auth_string}")
                else:
                    print(f"Ushbu manzilni qabul qiluvchiga bering, va unga quyidagi vaqtgacha ulanib bo'lmasligini ayting: {schedule.strftime('%I:%M:%S%p, %b %d, %y')}")
            print(url)
            if mode_settings.get("general", "qr"):
                qr = QRCode()
                qr.add_data(url)
                print("Onion manzil QR kod sifatida:")
                qr.print_ascii()
                if not mode_settings.get("general", "public"):
                    qr.clear()
                    qr.add_data(app.auth_string)
                    print("Shaxsiy kalit QR kod sifatida:")
                    qr.print_ascii()
            print("")
            print("Rejalashtirilgan vaqtni kutish boshlandi...")
            app.onion.cleanup(False)
            time.sleep(autostart_timer)
            app.start_onion_service(mode, mode_settings)
        else:
            app.start_onion_service(mode, mode_settings)
    except KeyboardInterrupt:
        print("")
        sys.exit()
    except (TorTooOldEphemeral, TorTooOldStealth, TorErrorProtocolError) as e:
        print("")
        sys.exit()
    if mode == "website":
        try:
            web.website_mode.set_file_info(filenames)
        except OSError as e:
            print(e.strerror)
            sys.exit(1)
    if mode == "share":
        print("Fayllar siqilmoqda.")
        try:
            web.share_mode.set_file_info(filenames)
        except OSError as e:
            print(e.strerror)
            sys.exit(1)
        if web.share_mode.download_filesize >= 157_286_400:
            print("")
            print("Ogohlantirish: Katta faylni ulashish bir necha soat vaqt olishi mumkin")
            print("")
    t = threading.Thread(target=web.start, args=(app.port,))
    t.daemon = True
    t.start()
    try:
        time.sleep(0.2)
        if app.autostop_timer > 0:
            app.autostop_timer_thread.start()
        url = f"http://{app.onion_host}"
        print("")
        if autostart_timer > 0:
            print("Server ishga tushdi")
        else:
            if mode == "receive":
                print(f"Yuborilgan fayllar ushbu papkada paydo bo'ladi: {mode_settings.get('receive', 'data_dir')}")
                print("")
                print("Ogohlantirish: Qabul qilish rejimi odamlarga kompyuteringizga fayl yuklash imkonini beradi. Ba'zi fayllar ishonchsiz bo'lishi mumkin.")
                print("")
                if mode_settings.get("general", "public"):
                    print("Jo'natuvchiga ushbu manzilni bering:")
                    print(url)
                else:
                    print("Jo'natuvchiga ushbu manzil va shaxsiy kalitni bering:")
                    print(url)
                    print(f"Shaxsiy kalit: {app.auth_string}")
            else:
                if mode_settings.get("general", "public"):
                    print("Qabul qiluvchiga ushbu manzilni bering:")
                    print(url)
                else:
                    print("Qabul qiluvchiga ushbu manzil va shaxsiy kalitni bering:")
                    print(url)
                    print(f"Shaxsiy kalit: {app.auth_string}")
            if mode_settings.get("general", "qr"):
                qr = QRCode()
                qr.add_data(url)
                print("Onion manzil QR kod sifatida:")
                qr.print_ascii()
                if not mode_settings.get("general", "public"):
                    qr.clear()
                    qr.add_data(app.auth_string)
                    print("Shaxsiy kalit QR kod sifatida:")
                    qr.print_ascii()
        print("")
        print("To'xtatish uchun Ctrl+C bosing")
        while t.is_alive():
            if app.autostop_timer > 0:
                if not app.autostop_timer_thread.is_alive():
                    if mode == "share":
                        if (
                            not web.share_mode.download_in_progress
                            or web.share_mode.cur_history_id == 0
                            or web.done
                        ):
                            print("Avtomatik to'xtatish taymer tugaganligi sababli to'xtatildi")
                            web.stop(app.port)
                            break
                    elif mode == "receive":
                        if (
                            web.receive_mode.cur_history_id == 0
                            or not web.receive_mode.uploads_in_progress
                        ):
                            print("Avtomatik to'xtatish taymer tugaganligi sababli to'xtatildi")
                            web.stop(app.port)
                            break
                        web.receive_mode.can_upload = False
                    else:
                        print("Avtomatik to'xtatish taymer tugaganligi sababli to'xtatildi")
                        web.stop(app.port)
                        break
            time.sleep(0.2)
    except KeyboardInterrupt:
        web.stop(app.port)
    finally:
        web.cleanup()
        t.join()
        onion.cleanup()
if __name__ == "__main__":
    main()
