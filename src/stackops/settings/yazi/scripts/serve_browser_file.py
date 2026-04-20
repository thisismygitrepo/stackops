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
BROWSER_FILE_SUFFIXES: Final[frozenset[str]] = frozenset({".html", ".htm", ".pdf"})
SUPPORTED_FILE_DESCRIPTION: Final[str] = ", ".join(sorted(BROWSER_FILE_SUFFIXES))


def is_browser_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in BROWSER_FILE_SUFFIXES


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


def make_file_url(host: str, port: int, target_path: Path, root: Path) -> str:
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    relative_parts = target_path.relative_to(root).parts
    quoted_path = "/".join(quote(part) for part in relative_parts)
    return f"http://{display_host}:{port}/{quoted_path}"


def make_index_html(root: Path, target_path: Path) -> bytes:
    browser_files = sorted(path for path in root.iterdir() if is_browser_file(path))
    items: list[str] = []
    for path in browser_files:
        relative_name = path.name
        href = quote(relative_name)
        label = html.escape(relative_name)
        marker = " (selected)" if path.resolve() == target_path.resolve() else ""
        items.append(f'<li><a href="/{href}">{label}</a>{html.escape(marker)}</li>')
    list_markup = "\n".join(items) or "<li>No browser-viewable files found.</li>"
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(target_path.name)}</title>
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
  </style>
</head>
<body>
  <h1>{html.escape(root.name)}</h1>
  <p>Serving <code>{html.escape(str(root))}</code></p>
  <ul>
    {list_markup}
  </ul>
</body>
</html>
"""
    return body.encode("utf-8")


class BrowserFileDirectoryHandler(SimpleHTTPRequestHandler):
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

    def do_GET(self) -> None:
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if self.path in {"/", "/index.html"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(make_index_html(root=self._root, target_path=self._target_path))
            return
        super().do_GET()

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


def serve_browser_file(target_path: Path, host: str, port: int, open_browser: bool) -> None:
    target_path = target_path.resolve()
    if not is_browser_file(target_path):
        raise ValueError(f"Expected a browser-viewable file ({SUPPORTED_FILE_DESCRIPTION}), got: {target_path}")

    root = target_path.parent
    selected_port = port or find_free_port(host)
    handler = functools.partial(BrowserFileDirectoryHandler, root=root, target_path=target_path)
    server = ThreadingHTTPServer((host, selected_port), handler)
    local_url = make_file_url(host=host, port=selected_port, target_path=target_path, root=root)

    print(f"Serving {target_path}")
    print(f"Local URL: {local_url}")
    for address in get_lan_addresses():
        print(f"Network URL: http://{address}:{selected_port}/{quote(target_path.name)}")

    if open_browser:
        webbrowser.open(local_url)

    server_thread = threading.Thread(target=server.serve_forever, name="stackops-yazi-browser-file-server", daemon=True)
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
    parser = argparse.ArgumentParser(description="Serve a local HTML or PDF file in the browser.")
    parser.add_argument("target", type=Path, help="HTML or PDF file to serve")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address. Defaults to 0.0.0.0 for LAN access.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind. Defaults to a free port.")
    parser.add_argument("--no-browser", action="store_true", help="Print URLs without opening the default browser.")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    args = parse_arguments(arguments)
    try:
        serve_browser_file(
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
