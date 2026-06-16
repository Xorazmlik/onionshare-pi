import unicodedata
from flask import request, render_template, make_response, jsonify, session
from flask_socketio import emit, ConnectionRefusedError
class ChatModeWeb:
    def __init__(self, common, web):
        self.common = common
        self.common.log("ChatModeWeb", "__init__")
        self.web = web
        self.connected_users = []
        self.cur_history_id = 0
        self.supports_file_requests = False
        self.define_routes()
    def remove_unallowed_characters(self, text):
        def allowed_character(ch):
            allowed_unicode_categories = [
                'L',
                'N',
            ]
            allowed_special_characters = [
                '-',
                '_',
                ' ',
            ]
            return (
                unicodedata.category(ch)[0] in allowed_unicode_categories and ord(ch) < 128
             ) or ch in allowed_special_characters
        return "".join(
            ch for ch in text if allowed_character(ch)
        )
    def validate_username(self, username):
        try:
            username = self.remove_unallowed_characters(username.strip())
            return (
                username
                and username not in self.connected_users
                and len(username) < 128
            )
        except Exception as e:
            self.common.log("ChatModeWeb", "validate_username", e)
            return False
    def define_routes(self):
        @self.web.app.route("/", methods=["GET"], provide_automatic_options=False)
        def index():
            history_id = self.cur_history_id
            self.cur_history_id += 1
            session["name"] = (
                session.get("name")
                if session.get("name")
                else self.common.build_username()
            )
            self.web.add_request(
                request.path,
                {"id": history_id, "status_code": 200},
            )
            self.web.add_request(self.web.REQUEST_LOAD, request.path)
            return render_template(
                "chat.html",
                static_url_path=self.web.static_url_path,
                username=session.get("name"),
                title=self.web.settings.get("general", "title"),
            )
        @self.web.app.route(
            "/update-session-username",
            methods=["POST"],
            provide_automatic_options=False,
        )
        def update_session_username():
            history_id = self.cur_history_id
            data = request.get_json()
            username = data.get("username", session.get("name")).strip()
            if self.validate_username(username):
                session["name"] = username
                self.web.add_request(
                    request.path,
                    {"id": history_id, "status_code": 200},
                )
                self.web.add_request(self.web.REQUEST_LOAD, request.path)
                r = make_response(
                    jsonify(
                        username=session.get("name"),
                        success=True,
                    )
                )
            else:
                self.web.add_request(
                    request.path,
                    {"id": history_id, "status_code": 403},
                )
                r = make_response(
                    jsonify(
                        username=session.get("name"),
                        success=False,
                    )
                )
            return r
        @self.web.socketio.on("connect", namespace="/chat")
        def server_connect():
            if self.validate_username(session.get("name")):
                self.connected_users.append(session.get("name"))
                session["socketio_session_id"] = request.sid
                emit(
                    "status",
                    {
                        "username": session.get("name"),
                        "msg": "{} has joined.".format(session.get("name")),
                        "connected_users": self.connected_users,
                        "user": session.get("name"),
                    },
                    broadcast=True,
                )
            else:
                raise ConnectionRefusedError('Invalid session')
        @self.web.socketio.on("text", namespace="/chat")
        def text(message):
            emit(
                "chat_message",
                {"username": session.get("name"), "msg": message["msg"]},
                broadcast=True,
            )
        @self.web.socketio.on("update_username", namespace="/chat")
        def update_username(message):
            current_name = session.get("name")
            new_name = message.get("username", "").strip()
            if self.validate_username(new_name):
                session["name"] = new_name
                self.connected_users[self.connected_users.index(current_name)] = (
                    session.get("name")
                )
                emit(
                    "status",
                    {
                        "msg": "{} has updated their username to: {}".format(
                            current_name, session.get("name")
                        ),
                        "connected_users": self.connected_users,
                        "old_name": current_name,
                        "new_name": session.get("name"),
                    },
                    broadcast=True,
                )
            else:
                emit(
                    "status",
                    {"msg": "Failed to update username."},
                )
        @self.web.socketio.on("disconnect", namespace="/chat")
        def disconnect():
            user_already_disconnected = False
            if session.get("name") in self.connected_users:
                self.connected_users.remove(session.get("name"))
            else:
                user_already_disconnected = True
            self.web.socketio.server.disconnect(
                sid=session.get("socketio_session_id"), namespace="/chat"
            )
            if not user_already_disconnected:
                emit(
                    "status",
                    {
                        "msg": "{} has left the room.".format(session.get("name")),
                        "connected_users": self.connected_users,
                    },
                    broadcast=True,
                )
