import functools
from http.server import ThreadingHTTPServer
from pathlib import Path
import threading
import urllib.request

import pytest

from stackops.settings.yazi.scripts import serve_browser_file


def test_make_target_url_uses_loopback_for_wildcard_bind(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("report with spaces.pdf")
    target_path.write_bytes(b"%PDF-1.7\n")

    url = serve_browser_file.make_target_url(host="0.0.0.0", port=8765, target_path=target_path, root=tmp_path)

    assert url == "http://127.0.0.1:8765/report%20with%20spaces.pdf"


def test_make_target_url_uses_root_for_directory(tmp_path: Path) -> None:
    url = serve_browser_file.make_target_url(host="127.0.0.1", port=8765, target_path=tmp_path, root=tmp_path)

    assert url == "http://127.0.0.1:8765/"


def test_make_directory_index_html_lists_directories_and_files(tmp_path: Path) -> None:
    html_path = tmp_path.joinpath("report.html")
    pdf_path = tmp_path.joinpath("report.pdf")
    image_path = tmp_path.joinpath("photo.webp")
    child_dir = tmp_path.joinpath("nested")
    html_path.write_text("<!doctype html>", encoding="utf-8")
    pdf_path.write_bytes(b"%PDF-1.7\n")
    image_path.write_bytes(b"image")
    child_dir.mkdir()
    tmp_path.joinpath("notes.txt").write_text("notes", encoding="utf-8")

    body = serve_browser_file.make_directory_index_html(root=tmp_path, target_path=pdf_path, directory_path=tmp_path).decode(
        "utf-8"
    )

    assert "report.html" in body
    assert "report.pdf" in body
    assert "photo.webp" in body
    assert "nested/" in body
    assert "notes.txt" in body
    assert "(selected)" in body


def test_favicon_request_returns_no_content(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("report.pdf")
    target_path.write_bytes(b"%PDF-1.7\n")
    handler = functools.partial(serve_browser_file.BrowserPathHandler, root=tmp_path, target_path=target_path)
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


def test_directory_request_returns_clickable_index(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("gallery")
    target_path.mkdir()
    target_path.joinpath("image.png").write_bytes(b"image")
    handler = functools.partial(serve_browser_file.BrowserPathHandler, root=target_path, target_path=target_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
        body = response.read().decode("utf-8")
        assert response.status == 200
        assert 'href="/image.png"' in body
        assert "image.png" in body
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


def test_index_html_file_request_serves_file(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("index.html")
    target_path.write_text("<!doctype html><title>Actual Index</title>", encoding="utf-8")
    handler = functools.partial(serve_browser_file.BrowserPathHandler, root=tmp_path, target_path=target_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=2)
        body = response.read().decode("utf-8")
        assert response.status == 200
        assert "Actual Index" in body
        assert "(selected)" not in body
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


def test_serve_browser_target_rejects_non_browser_file(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("notes.txt")
    target_path.write_text("notes", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected a browser-viewable file"):
        serve_browser_file.serve_browser_target(target_path=target_path, host="127.0.0.1", port=0, open_browser=False)
