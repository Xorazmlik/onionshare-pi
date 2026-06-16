import os
from flask import render_template, make_response
from .send_base_mode import SendBaseModeWeb
class WebsiteModeWeb(SendBaseModeWeb):
    def init(self):
        pass
    def define_routes(self):
        @self.web.app.route("/", defaults={"path": ""}, methods=["GET"], provide_automatic_options=False)
        @self.web.app.route("/<path:path>", methods=["GET"], provide_automatic_options=False)
        def path_public(path):
            return path_logic(path)
        def path_logic(path=""):
            return self.render_logic(path)
    def directory_listing_template(
        self, path, files, dirs, breadcrumbs, breadcrumbs_leaf
    ):
        return make_response(
            render_template(
                "listing.html",
                path=path,
                files=files,
                dirs=dirs,
                breadcrumbs=breadcrumbs,
                breadcrumbs_leaf=breadcrumbs_leaf,
                static_url_path=self.web.static_url_path,
                title=self.web.settings.get("general", "title"),
            )
        )
    def set_file_info_custom(self, filenames, processed_size_callback):
        self.common.log("WebsiteModeWeb", "set_file_info_custom")
        self.web.cancel_compression = True
    def render_logic(self, path=""):
        path = path.rstrip("/")
        if path in self.files:
            filesystem_path = self.files[path]
            if os.path.isdir(filesystem_path):
                index_path = os.path.join(path, "index.html")
                if index_path in self.files:
                    return self.stream_individual_file(self.files[index_path])
                else:
                    filenames = []
                    for filename in os.listdir(filesystem_path):
                        filenames.append(filename)
                    filenames.sort()
                    return self.directory_listing(filenames, path, filesystem_path, True)
            elif os.path.isfile(filesystem_path):
                return self.stream_individual_file(filesystem_path)
            else:
                history_id = self.cur_history_id
                self.cur_history_id += 1
                return self.web.error404(history_id)
        else:
            if path == "":
                index_path = "index.html"
                if index_path in self.files:
                    return self.stream_individual_file(self.files[index_path])
                else:
                    filenames = list(self.root_files)
                    filenames.sort()
                    return self.directory_listing(filenames, path, None, True)
            else:
                history_id = self.cur_history_id
                self.cur_history_id += 1
                return self.web.error404(history_id)
