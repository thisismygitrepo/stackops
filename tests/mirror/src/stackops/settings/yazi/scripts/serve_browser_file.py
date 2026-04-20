import functools
from http.server import ThreadingHTTPServer
from pathlib import Path
import threading
import urllib.request

import pytest

from stackops.settings.yazi.scripts import serve_browser_file


def test_make_file_url_uses_loopback_for_wildcard_bind(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("report with spaces.pdf")
    target_path.write_bytes(b"%PDF-1.7\n")

    url = serve_browser_file.make_file_url(host="0.0.0.0", port=8765, target_path=target_path, root=tmp_path)

    assert url == "http://127.0.0.1:8765/report%20with%20spaces.pdf"


def test_make_index_html_lists_browser_files_only(tmp_path: Path) -> None:
    html_path = tmp_path.joinpath("report.html")
    pdf_path = tmp_path.joinpath("report.pdf")
    image_path = tmp_path.joinpath("photo.webp")
    html_path.write_text("<!doctype html>", encoding="utf-8")
    pdf_path.write_bytes(b"%PDF-1.7\n")
    image_path.write_bytes(b"image")
    tmp_path.joinpath("notes.txt").write_text("notes", encoding="utf-8")

    body = serve_browser_file.make_index_html(root=tmp_path, target_path=pdf_path).decode("utf-8")

    assert "report.html" in body
    assert "report.pdf" in body
    assert "photo.webp" in body
    assert "notes.txt" not in body
    assert "(selected)" in body


def test_favicon_request_returns_no_content(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("report.pdf")
    target_path.write_bytes(b"%PDF-1.7\n")
    handler = functools.partial(serve_browser_file.BrowserFileDirectoryHandler, root=tmp_path, target_path=target_path)
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


def test_serve_browser_file_rejects_non_browser_file(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("notes.txt")
    target_path.write_text("notes", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected a browser-viewable file"):
        serve_browser_file.serve_browser_file(target_path=target_path, host="127.0.0.1", port=0, open_browser=False)
