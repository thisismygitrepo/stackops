import argparse
import functools
import html
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import platform
import socket
from socketserver import BaseServer
import sys
import threading
from typing import Callable, Final, cast
from urllib.parse import quote
import webbrowser

DEFAULT_HOST: Final[str] = "0.0.0.0"
DEFAULT_PORT: Final[int] = 0
BROWSER_DOCUMENT_SUFFIXES: Final[frozenset[str]] = frozenset({".html", ".htm", ".pdf"})
BROWSER_IMAGE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".apng", ".avif", ".bmp", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
)
BROWSER_FILE_SUFFIXES: Final[frozenset[str]] = BROWSER_DOCUMENT_SUFFIXES | BROWSER_IMAGE_SUFFIXES
SUPPORTED_FILE_DESCRIPTION: Final[str] = ", ".join(sorted(BROWSER_FILE_SUFFIXES))


def is_browser_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in BROWSER_FILE_SUFFIXES


def is_browser_target(path: Path) -> bool:
    return path.is_dir() or is_browser_file(path=path)


def find_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def get_lan_addresses() -> list[str]:
    addresses: set[str] = set()
    hostname = socket.gethostname()
    try:
        for result in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM):
            address = cast(str, result[4][0])
            if not address.startswith("127."):
                addresses.add(address)
    except socket.gaierror:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            address = sock.getsockname()[0]
            if not address.startswith("127."):
                addresses.add(address)
    except OSError:
        pass

    return sorted(addresses)


def make_url_path(path: Path, root: Path) -> str:
    relative_parts = path.relative_to(root).parts
    if not relative_parts:
        return "/"
    quoted_path = "/".join(quote(part) for part in relative_parts)
    if path.is_dir():
        return f"/{quoted_path}/"
    return f"/{quoted_path}"


def make_target_url(host: str, port: int, target_path: Path, root: Path) -> str:
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{display_host}:{port}{make_url_path(path=target_path, root=root)}"


def make_directory_index_html(root: Path, target_path: Path, directory_path: Path) -> bytes:
    entries = sorted(directory_path.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower()))
    items: list[str] = []
    if directory_path != root:
        href = make_url_path(path=directory_path.parent, root=root)
        items.append(f'<li><a href="{html.escape(href)}">../</a></li>')

    for path in entries:
        href = make_url_path(path=path, root=root)
        display_name = f"{path.name}/" if path.is_dir() else path.name
        label = html.escape(display_name)
        marker = " (selected)" if path.resolve() == target_path.resolve() else ""
        items.append(f'<li><a href="{html.escape(href)}">{label}</a>{html.escape(marker)}</li>')

    list_markup = "\n".join(items) or "<li>Directory is empty.</li>"
    relative_title = "/" if directory_path == root else "/".join(directory_path.relative_to(root).parts)
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(relative_title)}</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{
      max-width: 76ch;
      margin: 2rem auto;
      padding: 0 1rem;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    a {{ color: LinkText; }}
    code {{ word-break: break-all; }}
    ul {{ list-style: none; padding-left: 0; }}
    li {{ padding: 0.15rem 0; }}
  </style>
</head>
<body>
  <h1>{html.escape(relative_title)}</h1>
  <p><code>{html.escape(str(directory_path))}</code></p>
  <ul>
    {list_markup}
  </ul>
</body>
</html>
"""
    return body.encode("utf-8")


class BrowserPathHandler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        request: socket.socket | tuple[bytes, socket.socket],
        client_address: tuple[str, int],
        server: BaseServer,
        *,
        root: Path,
        target_path: Path,
    ) -> None:
        self._root = root
        self._target_path = target_path
        super().__init__(request, client_address, server, directory=str(root))

    def send_directory_index(self, directory_path: Path, send_body: bool) -> None:
        body = make_directory_index_html(root=self._root, target_path=self._target_path, directory_path=directory_path)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        translated_path = Path(self.translate_path(self.path))
        if translated_path.is_dir():
            self.send_directory_index(directory_path=translated_path, send_body=True)
            return

        super().do_GET()

    def do_HEAD(self) -> None:
        translated_path = Path(self.translate_path(self.path))
        if translated_path.is_dir():
            self.send_directory_index(directory_path=translated_path, send_body=False)
            return

        super().do_HEAD()

    def log_message(self, format: str, *args: object) -> None:
        del format, args
        return


def read_exit_key() -> str:
    if platform.system().lower() == "windows":
        import msvcrt

        getch = cast(Callable[[], bytes], getattr(msvcrt, "getch"))
        pressed_key = getch()
        if pressed_key in {b"\x00", b"\xe0"}:
            _ = getch()
        return pressed_key.decode("latin-1")

    import termios
    import tty

    stdin_file_descriptor = sys.stdin.fileno()
    previous_terminal_state = termios.tcgetattr(stdin_file_descriptor)
    try:
        tty.setraw(stdin_file_descriptor)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(stdin_file_descriptor, termios.TCSADRAIN, previous_terminal_state)


def wait_for_return_to_yazi() -> None:
    if not sys.stdin.isatty():
        return

    print("Press q, Esc, or Enter to stop serving and return to Yazi.")
    while True:
        pressed_key = read_exit_key()
        if pressed_key.lower() == "q" or pressed_key in {"\x1b", "\r", "\n"}:
            return


def serve_browser_target(target_path: Path, host: str, port: int, open_browser: bool) -> None:
    target_path = target_path.resolve()
    if not is_browser_target(path=target_path):
        raise ValueError(f"Expected a browser-viewable file ({SUPPORTED_FILE_DESCRIPTION}) or directory, got: {target_path}")

    root = target_path if target_path.is_dir() else target_path.parent
    selected_port = port or find_free_port(host)
    handler = functools.partial(BrowserPathHandler, root=root, target_path=target_path)
    server = ThreadingHTTPServer((host, selected_port), handler)
    local_url = make_target_url(host=host, port=selected_port, target_path=target_path, root=root)

    print(f"Serving {target_path}")
    print(f"Local URL: {local_url}")
    for address in get_lan_addresses():
        network_url = make_target_url(host=address, port=selected_port, target_path=target_path, root=root)
        print(f"Network URL: {network_url}")

    if open_browser:
        webbrowser.open(local_url)

    server_thread = threading.Thread(target=server.serve_forever, name="stackops-yazi-browser-server", daemon=True)
    server_thread.start()
    try:
        wait_for_return_to_yazi()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


def parse_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a local browser-viewable file or directory.")
    parser.add_argument("target", type=Path, help="Browser-viewable file or directory to serve")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address. Defaults to 0.0.0.0 for LAN access.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind. Defaults to a free port.")
    parser.add_argument("--no-browser", action="store_true", help="Print URLs without opening the default browser.")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    args = parse_arguments(arguments)
    try:
        serve_browser_target(
            target_path=args.target,
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
        )
    except ValueError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
