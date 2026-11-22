import asyncio
import os
import platform
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass

from stackops.scripts.python.helpers.helpers_webui.constants import PTY_POLL_SECONDS, PTY_READ_CHUNK_BYTES

# Python starts with SIGPIPE ignored and an exec keeps that, which leaves a shell pipeline such as `tr … | head` in the command running for ever.
POSIX_TRAMPOLINE = (
    "import os, signal, sys; os.login_tty(int(sys.argv[1])); signal.signal(signal.SIGPIPE, signal.SIG_DFL); os.execvp(sys.argv[2], sys.argv[2:])"
)


@dataclass(frozen=True)
class PtyHandle:
    pump: Callable[[Callable[[bytes], None]], int]
    write: Callable[[bytes], None]
    resize: Callable[[int, int], None]
    stop: Callable[[bool], None]
    close: Callable[[], None]


def spawn_pty(argv: list[str], working_directory: str, environment: dict[str, str], rows: int, columns: int) -> PtyHandle:
    if platform.system() == "Windows":
        return _spawn_windows_pty(argv=argv, working_directory=working_directory, environment=environment, rows=rows, columns=columns)
    return _spawn_posix_pty(argv=argv, working_directory=working_directory, environment=environment, rows=rows, columns=columns)


def _spawn_posix_pty(argv: list[str], working_directory: str, environment: dict[str, str], rows: int, columns: int) -> PtyHandle:
    import fcntl
    import pty
    import select
    import signal
    import struct
    import termios

    loop = asyncio.get_running_loop()
    pending_input = bytearray()
    master_fd, slave_fd = pty.openpty()
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
    # The trampoline makes the pty the controlling terminal in a fresh interpreter, so no Python runs between fork and exec in this threaded server.
    process = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", POSIX_TRAMPOLINE, str(slave_fd), *argv], cwd=working_directory, env=environment, pass_fds=(slave_fd,)
    )
    os.close(slave_fd)
    os.set_blocking(master_fd, False)

    def pump(on_output: Callable[[bytes], None]) -> int:
        while True:
            readable, _writable, _exceptional = select.select([master_fd], [], [], PTY_POLL_SECONDS)
            if readable:
                try:
                    chunk = os.read(master_fd, PTY_READ_CHUNK_BYTES)
                except OSError:  # Linux reports the end of a pty as EIO instead of an empty read.
                    chunk = b""
                if chunk == b"":
                    break
                on_output(chunk)
            elif process.poll() is not None:
                break
        return process.wait()

    # Runs on the event loop only, like `write` and `close`. What the terminal's input queue cannot take yet (a paste into a busy program) is kept
    # and written once the program reads again, in order. Design choice: no cap on what is kept; it is what one person typed or pasted.
    def flush_input() -> None:
        while pending_input:
            try:
                written = os.write(master_fd, pending_input)
            except BlockingIOError:
                loop.add_writer(master_fd, flush_input)
                return
            except OSError:  # The program is gone, so nothing is left to read the rest.
                pending_input.clear()
                break
            del pending_input[:written]
        loop.remove_writer(master_fd)

    def write(data: bytes) -> None:
        pending_input.extend(data)
        flush_input()

    def resize(new_rows: int, new_columns: int) -> None:
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", new_rows, new_columns, 0, 0))

    def stop(force: bool) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
        except ProcessLookupError:  # The command exited between the request and the signal.
            return

    def close() -> None:
        loop.remove_writer(master_fd)
        os.close(master_fd)

    return PtyHandle(pump=pump, write=write, resize=resize, stop=stop, close=close)


def _spawn_windows_pty(argv: list[str], working_directory: str, environment: dict[str, str], rows: int, columns: int) -> PtyHandle:
    from winpty import PtyProcess  # type: ignore[import-not-found]  # pywinpty is supplied on the fly by `stackops webui` on Windows.

    process = PtyProcess.spawn(argv, cwd=working_directory, env=environment, dimensions=(rows, columns))

    def pump(on_output: Callable[[bytes], None]) -> int:
        while True:
            try:
                text: str = process.read(PTY_READ_CHUNK_BYTES)
            except EOFError:
                break
            on_output(text.encode("utf-8"))
        exit_status: int | None = process.wait()
        return -1 if exit_status is None else exit_status

    def write(data: bytes) -> None:
        process.write(data.decode("utf-8", errors="replace"))

    def resize(new_rows: int, new_columns: int) -> None:
        process.setwinsize(new_rows, new_columns)

    def stop(force: bool) -> None:
        process.terminate(force=force)

    def close() -> None:
        process.close(force=True)

    return PtyHandle(pump=pump, write=write, resize=resize, stop=stop, close=close)
