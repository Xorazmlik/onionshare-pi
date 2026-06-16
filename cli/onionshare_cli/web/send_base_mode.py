import os
import sys
import tempfile
import mimetypes
import gzip
from flask import Response, request
from unidecode import unidecode
from urllib.parse import quote, unquote
class SendBaseModeWeb:
    def __init__(self, common, web):
        super(SendBaseModeWeb, self).__init__()
        self.common = common
        self.web = web
        self.is_zipped = False
        self.download_filename = None
        self.download_filesize = None
        self.zip_writer = None
        self.gzip_tmp_dir = tempfile.TemporaryDirectory(dir=self.common.build_tmp_dir())
        self.gzip_counter = 0
        self.download_in_progress = False
        self.cur_history_id = 0
        self.supports_file_requests = True
        self.define_routes()
        self.init()
    def fix_windows_paths(self, path):
        if self.common.platform == "Windows":
            return path.replace("\\", "/")
        return path
    def set_file_info(self, filenames, processed_size_callback=None):
        if len(filenames) == 1 and os.path.isdir(filenames[0]):
            filenames = [
                os.path.join(filenames[0], x) for x in os.listdir(filenames[0])
            ]
        self.files = {}
        self.root_files = (
            {}
        )
        self.cur_history_id = 0
        self.file_info = {"files": [], "dirs": []}
        self.gzip_individual_files = {}
        self.init()
        if self.common.platform == "Windows":
            slash = "\\"
        else:
            slash = "/"
        for filename in filenames:
            basename = os.path.basename(filename.rstrip(slash))
            if os.path.isfile(filename):
                self.files[self.fix_windows_paths(basename)] = filename
                self.root_files[self.fix_windows_paths(basename)] = filename
            elif os.path.isdir(filename):
                self.root_files[self.fix_windows_paths(basename)] = filename
                for root, _, nested_filenames in os.walk(filename):
                    normalized_root = os.path.join(
                        basename, root[len(filename) :].lstrip(slash)
                    ).rstrip(slash)
                    self.files[self.fix_windows_paths(normalized_root)] = root
                    for nested_filename in nested_filenames:
                        self.files[
                            self.fix_windows_paths(
                                os.path.join(normalized_root, nested_filename)
                            )
                        ] = os.path.join(root, nested_filename)
        self.set_file_info_custom(filenames, processed_size_callback)
    def directory_listing(self, filenames, path="", filesystem_path=None, add_trailing_slash=False):
        history_id = self.cur_history_id
        self.cur_history_id += 1
        self.web.add_request(
            self.web.REQUEST_INDIVIDUAL_FILE_STARTED,
            f"/{path}",
            {"id": history_id, "method": request.method, "status_code": 200},
        )
        breadcrumbs = [("☗", "/")]
        parts = path.split("/")
        if parts[-1] == "":
            parts = parts[:-1]
        for i in range(len(parts)):
            breadcrumbs.append((parts[i], f"/{'/'.join(parts[0 : i + 1])}"))
        breadcrumbs_leaf = breadcrumbs.pop()[0]
        files, dirs = self.build_directory_listing(path, filenames, filesystem_path, add_trailing_slash)
        self.web.done = True
        return self.directory_listing_template(
            path, files, dirs, breadcrumbs, breadcrumbs_leaf
        )
    def build_directory_listing(self, path, filenames, filesystem_path, add_trailing_slash=False):
        files = []
        dirs = []
        for filename in filenames:
            if filesystem_path:
                this_filesystem_path = os.path.join(filesystem_path, filename)
            else:
                this_filesystem_path = self.files[filename]
            is_dir = os.path.isdir(this_filesystem_path)
            if is_dir:
                if add_trailing_slash:
                    dirs.append(
                        {"link": os.path.join(f"/{path}", quote(filename), ""), "basename": filename}
                    )
                else:
                    dirs.append(
                        {"link": os.path.join(f"/{path}", quote(filename)), "basename": filename}
                    )
            else:
                size = os.path.getsize(this_filesystem_path)
                size_human = self.common.human_readable_filesize(size)
                files.append(
                    {
                        "link": os.path.join(f"/{path}", quote(filename)),
                        "basename": filename,
                        "size_human": size_human,
                    }
                )
        return files, dirs
    def stream_individual_file(self, filesystem_path):
        use_gzip = self.should_use_gzip()
        if use_gzip:
            if filesystem_path not in self.gzip_individual_files:
                gzip_filename = os.path.join(
                    self.gzip_tmp_dir.name, str(self.gzip_counter)
                )
                self.gzip_counter += 1
                self._gzip_compress(filesystem_path, gzip_filename, 6, None)
                self.gzip_individual_files[filesystem_path] = gzip_filename
            file_to_download = self.gzip_individual_files[filesystem_path]
            filesize = os.path.getsize(self.gzip_individual_files[filesystem_path])
        else:
            file_to_download = filesystem_path
            filesize = os.path.getsize(filesystem_path)
        path = request.path
        history_id = self.cur_history_id
        self.cur_history_id += 1
        self.web.add_request(
            self.web.REQUEST_INDIVIDUAL_FILE_STARTED,
            path,
            {"id": history_id, "filesize": filesize},
        )
        def generate():
            chunk_size = 102400
            fp = open(file_to_download, "rb")
            self.web.done = False
            while not self.web.done:
                chunk = fp.read(chunk_size)
                if chunk == b"":
                    self.web.done = True
                else:
                    try:
                        yield chunk
                        downloaded_bytes = fp.tell()
                        percent = (1.0 * downloaded_bytes / filesize) * 100
                        if (
                            not self.web.is_gui
                            or self.common.platform == "Linux"
                            or self.common.platform == "BSD"
                        ):
                            if self.web.settings.get(self.web.mode, "log_filenames"):
                                decoded_path = unquote(path)
                                decoded_path = decoded_path.replace("\r", "").replace("\n", "")
                                filename_str = f"{decoded_path} - "
                            else:
                                filename_str = ""
                            sys.stdout.write(
                                "\r{0}{1:s}, {2:.2f}%          ".format(
                                    filename_str,
                                    self.common.human_readable_filesize(
                                        downloaded_bytes
                                    ),
                                    percent,
                                )
                            )
                            sys.stdout.flush()
                        self.web.add_request(
                            self.web.REQUEST_INDIVIDUAL_FILE_PROGRESS,
                            path,
                            {
                                "id": history_id,
                                "bytes": downloaded_bytes,
                                "filesize": filesize,
                            },
                        )
                        self.web.done = False
                    except Exception:
                        self.web.done = True
                        self.web.add_request(
                            self.web.REQUEST_INDIVIDUAL_FILE_CANCELED,
                            path,
                            {"id": history_id},
                        )
            fp.close()
            sys.stdout.write("\n")
        basename = os.path.basename(filesystem_path)
        r = Response(generate())
        if use_gzip:
            r.headers.set("Content-Encoding", "gzip")
        r.headers.set("Content-Length", filesize)
        filename_dict = {
            "filename": unidecode(basename),
            "filename*": "UTF-8''%s" % quote(basename),
        }
        r.headers.set("Content-Disposition", "inline", **filename_dict)
        (content_type, _) = mimetypes.guess_type(basename, strict=False)
        if content_type is not None:
            r.headers.set("Content-Type", content_type)
        return r
    def should_use_gzip(self):
        return (not self.is_zipped) and (
            "gzip" in request.headers.get("Accept-Encoding", "").lower()
        )
    def _gzip_compress(
        self, input_filename, output_filename, level, processed_size_callback=None
    ):
        bytes_processed = 0
        blocksize = 1 << 16
        with open(input_filename, "rb") as input_file:
            output_file = gzip.open(output_filename, "wb", level)
            while True:
                if processed_size_callback is not None:
                    processed_size_callback(bytes_processed)
                block = input_file.read(blocksize)
                if len(block) == 0:
                    break
                output_file.write(block)
                bytes_processed += blocksize
            output_file.close()
    def init(self):
        pass
    def define_routes(self):
        pass
    def directory_listing_template(self):
        pass
    def set_file_info_custom(self, filenames, processed_size_callback):
        pass
    def render_logic(self, path=""):
        pass
