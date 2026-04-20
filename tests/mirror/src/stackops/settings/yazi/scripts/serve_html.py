import functools
from http.server import ThreadingHTTPServer
from pathlib import Path
import threading
import urllib.request

import pytest

from stackops.settings.yazi.scripts import serve_html


def test_make_file_url_uses_loopback_for_wildcard_bind(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("report with spaces.html")
    target_path.write_text("<!doctype html>", encoding="utf-8")

    url = serve_html.make_file_url(host="0.0.0.0", port=8765, target_path=target_path, root=tmp_path)

    assert url == "http://127.0.0.1:8765/report%20with%20spaces.html"


def test_make_index_html_lists_html_files_only(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("report.html")
    target_path.write_text("<!doctype html>", encoding="utf-8")
    tmp_path.joinpath("notes.txt").write_text("notes", encoding="utf-8")

    body = serve_html.make_index_html(root=tmp_path, target_path=target_path).decode("utf-8")

    assert "report.html" in body
    assert "notes.txt" not in body
    assert "(selected)" in body


def test_favicon_request_returns_no_content(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("report.html")
    target_path.write_text("<!doctype html>", encoding="utf-8")
    handler = functools.partial(serve_html.HtmlDirectoryHandler, root=tmp_path, target_path=target_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{port}/favicon.ico", timeout=2)
        assert response.status == 204
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


def test_serve_html_rejects_non_html_file(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("notes.txt")
    target_path.write_text("notes", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected an HTML file"):
        serve_html.serve_html(target_path=target_path, host="127.0.0.1", port=0, open_browser=False)
