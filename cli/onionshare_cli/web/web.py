import importlib.metadata
import logging
import mimetypes
import os
import queue
import requests
import shutil
from packaging.version import Version
from waitress.server import create_server
import flask
from flask import (
    Flask,
    request,
    render_template,
    abort,
    make_response,
    send_file,
)
from flask_compress import Compress
from flask_socketio import SocketIO
from .share_mode import ShareModeWeb
from .receive_mode import ReceiveModeWeb, ReceiveModeWSGIMiddleware, ReceiveModeRequest
from .website_mode import WebsiteModeWeb
from .chat_mode import ChatModeWeb
def stubbed_show_server_banner(env, debug, app_import_path=None, eager_loading=None):
    pass
try:
    flask.cli.show_server_banner = stubbed_show_server_banner
except Exception:
    pass
class WaitressException(Exception):
    pass
class Web:
    REQUEST_LOAD = 0
    REQUEST_STARTED = 1
    REQUEST_PROGRESS = 2
    REQUEST_CANCELED = 3
    REQUEST_UPLOAD_INCLUDES_MESSAGE = 4
    REQUEST_UPLOAD_FILE_RENAMED = 5
    REQUEST_UPLOAD_SET_DIR = 6
    REQUEST_UPLOAD_FINISHED = 7
    REQUEST_UPLOAD_CANCELED = 8
    REQUEST_INDIVIDUAL_FILE_STARTED = 9
    REQUEST_INDIVIDUAL_FILE_PROGRESS = 10
    REQUEST_INDIVIDUAL_FILE_CANCELED = 11
    REQUEST_ERROR_DATA_DIR_CANNOT_CREATE = 12
    REQUEST_OTHER = 13
    def __init__(self, common, is_gui, mode_settings, mode="share"):
        self.common = common
        self.common.log("Web", "__init__", f"is_gui={is_gui}, mode={mode}")
        self.settings = mode_settings
        mimetypes.add_type("text/javascript", ".js")
        self.waitress = None
        self.app = Flask(
            __name__,
            static_folder=self.common.get_resource_path("static"),
            static_url_path=f"/static_{self.common.random_string(16)}",
            template_folder=self.common.get_resource_path("templates"),
        )
        self.compress = Compress()
        self.compress.init_app(self.app)
        self.app.secret_key = self.common.random_string(8)
        self.generate_static_url_path()
        if self.common.verbose:
            self.verbose_mode()
        self.is_gui = is_gui
        self.stop_q = queue.Queue()
        self.mode = mode
        if self.mode == "receive":
            self.app.wsgi_app = ReceiveModeWSGIMiddleware(self.app.wsgi_app, self)
            self.app.request_class = ReceiveModeRequest
        flask_version = importlib.metadata.version("flask")
        if Version(flask_version) < Version("0.11"):
            Flask.select_jinja_autoescape = self._safe_select_jinja_autoescape
        self.security_headers = [
            ("X-Frame-Options", "DENY"),
            ("X-Xss-Protection", "1; mode=block"),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
            ("Server", "OnionShare"),
        ]
        self.q = queue.Queue()
        self.done = False
        self.shutdown_password = self.common.random_string(16)
        self.running = False
        self.define_common_routes()
        self.share_mode = None
        self.receive_mode = None
        self.website_mode = None
        self.chat_mode = None
        if self.mode == "share":
            self.share_mode = ShareModeWeb(self.common, self)
        elif self.mode == "receive":
            self.receive_mode = ReceiveModeWeb(self.common, self)
        elif self.mode == "website":
            self.website_mode = WebsiteModeWeb(self.common, self)
        elif self.mode == "chat":
            if self.common.verbose:
                try:
                    self.socketio = SocketIO(async_mode="gevent", logger=True, engineio_logger=True)
                except ValueError:
                    self.socketio = SocketIO(logger=True, engineio_logger=True)
            else:
                try:
                    self.socketio = SocketIO(async_mode="gevent")
                except ValueError:
                    self.socketio = SocketIO()
            self.socketio.init_app(self.app)
            self.chat_mode = ChatModeWeb(self.common, self)
        self.cleanup_tempdirs = []
    def get_mode(self):
        if self.mode == "share":
            return self.share_mode
        elif self.mode == "receive":
            return self.receive_mode
        elif self.mode == "website":
            return self.website_mode
        elif self.mode == "chat":
            return self.chat_mode
        else:
            return None
    def generate_static_url_path(self):
        self.static_url_path = f"/static_{self.common.random_string(16)}"
        self.common.log("Web", "generate_static_url_path", f"yangi static_url_path: {self.static_url_path}")
        self.app.static_url_path = self.static_url_path
        self.app.add_url_rule(
            self.static_url_path + "/<path:filename>",
            view_func=self.app.send_static_file,
        )
    def define_common_routes(self):
        @self.app.after_request
        def add_security_headers(r):
            for header, value in self.security_headers:
                r.headers.set(header, value)
            default_csp = "default-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'; img-src 'self' data:;"
            if self.mode != "website" or (
                not self.settings.get("website", "disable_csp")
                and not self.settings.get("website", "custom_csp")
            ):
                r.headers.set("Content-Security-Policy", default_csp)
            else:
                if self.settings.get("website", "custom_csp"):
                    r.headers.set("Content-Security-Policy", self.settings.get("website", "custom_csp"))
            return r
        @self.app.errorhandler(404)
        def not_found(e):
            mode = self.get_mode()
            history_id = mode.cur_history_id
            mode.cur_history_id += 1
            return self.error404(history_id)
        @self.app.errorhandler(405)
        def method_not_allowed(e):
            mode = self.get_mode()
            history_id = mode.cur_history_id
            mode.cur_history_id += 1
            return self.error405(history_id)
        @self.app.errorhandler(500)
        def internal_error(e):
            mode = self.get_mode()
            history_id = mode.cur_history_id
            mode.cur_history_id += 1
            return self.error500(history_id)
        if self.mode != "website":
            @self.app.route("/favicon.ico")
            def favicon():
                return send_file(f"{self.common.get_resource_path('static')}/img/favicon.ico")
    def error403(self):
        self.add_request(Web.REQUEST_OTHER, request.path)
        return render_template("403.html", static_url_path=self.static_url_path), 403
    def error404(self, history_id):
        mode = self.get_mode()
        if mode.supports_file_requests:
            self.add_request(self.REQUEST_INDIVIDUAL_FILE_STARTED, request.path, {"id": history_id, "status_code": 404})
        self.add_request(Web.REQUEST_OTHER, request.path)
        return render_template("404.html", static_url_path=self.static_url_path), 404
    def error405(self, history_id):
        mode = self.get_mode()
        if mode.supports_file_requests:
            self.add_request(self.REQUEST_INDIVIDUAL_FILE_STARTED, request.path, {"id": history_id, "status_code": 405})
        self.add_request(Web.REQUEST_OTHER, request.path)
        return render_template("405.html", static_url_path=self.static_url_path), 405
    def error500(self, history_id):
        mode = self.get_mode()
        if mode.supports_file_requests:
            self.add_request(self.REQUEST_INDIVIDUAL_FILE_STARTED, request.path, {"id": history_id, "status_code": 500})
        self.add_request(Web.REQUEST_OTHER, request.path)
        return render_template("500.html", static_url_path=self.static_url_path), 500
    def _safe_select_jinja_autoescape(self, filename):
        if filename is None:
            return True
        return filename.endswith((".html", ".htm", ".xml", ".xhtml"))
    def add_request(self, request_type, path=None, data=None):
        self.q.put({"type": request_type, "path": path, "data": data})
    def verbose_mode(self):
        flask_log_filename = os.path.join(self.common.build_data_dir(), "flask.log")
        log_handler = logging.FileHandler(flask_log_filename)
        log_handler.setLevel(logging.WARNING)
        self.app.logger.addHandler(log_handler)
    def start(self, port):
        self.common.log("Web", "start", f"port={port}")
        while not self.stop_q.empty():
            try:
                self.stop_q.get(block=False)
            except queue.Empty:
                pass
        if os.path.exists("/usr/share/anon-ws-base-files/workstation"):
            host = "0.0.0.0"
        else:
            host = "127.0.0.1"
        self.running = True
        if self.mode == "chat":
            self.socketio.run(self.app, host=host, port=port)
        else:
            try:
                self.waitress = create_server(
                    self.app,
                    host=host,
                    port=port,
                    clear_untrusted_proxy_headers=True,
                    ident="OnionShare",
                )
                self.waitress.run()
            except Exception as e:
                if not self.waitress.shutdown:
                    raise WaitressException(f"Waitress ishga tushirishda xatolik: {e}")
    def stop(self, port):
        self.common.log("Web", "stop", "server to'xtatilmoqda")
        self.stop_q.put(True)
        if self.mode == "chat":
            self.socketio.stop()
        if self.waitress:
            self.waitress_custom_shutdown()
    def cleanup(self):
        self.common.log("Web", "cleanup")
        for dir in self.cleanup_tempdirs:
            dir.cleanup()
        self.cleanup_tempdirs = []
    def waitress_custom_shutdown(self):
        self.waitress.shutdown = True
        while self.waitress._map:
            triggers = list(self.waitress._map.values())
            for trigger in triggers:
                trigger.handle_close()
        self.waitress.maintenance(0)
        self.waitress.task_dispatcher.shutdown()
        return True
