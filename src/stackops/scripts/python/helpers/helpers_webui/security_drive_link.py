import importlib.util
import re
import shutil
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from typing import Literal, TypedDict
from urllib.parse import unquote, urlparse

from stackops.scripts.python.helpers.helpers_webui.security_constants import (
    DOWNLOAD_ROOT,
    DRIVE_FILE_ADDRESS,
    DRIVE_ID_PATTERN,
    DRIVE_PROBE_READ_BYTES,
    DRIVE_PROBE_TIMEOUT_SECONDS,
)

# What the pasted text is: a file's link or ID, a folder's link (which the download command cannot take), or nothing it can use.
type LinkForm = Literal["file", "folder", "unrecognised"]
# What Google Drive said about the file when asked, without fetching it.
type LinkState = Literal["found", "private", "missing", "busy", "offline", "unknown"]


class DriveLink(TypedDict):
    form: LinkForm
    id: str
    state: LinkState
    name: str
    size: int | None
    size_text: str


# Where a download goes and whether this machine can run one.
class DownloadPlace(TypedDict):
    folder: str
    free: int
    ready: bool


# The file ID, read the way the download command reads it (`download_google_drive_file`), so the page checks the file that would be fetched.
def _file_id(text: str) -> str:
    if "id=" in text:
        return text.split("id=")[1].split("&")[0]
    if "/d/" in text:
        return text.split("/d/")[1].split("/")[0]
    return text


def _named_file(headers: Message) -> str:
    disposition = headers.get("Content-Disposition", "")
    encoded = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", disposition, flags=re.IGNORECASE)
    if encoded is not None:
        return unquote(encoded.group(1).strip().strip('"'))
    plain = re.search(r'filename="?([^";]+)"?', disposition, flags=re.IGNORECASE)
    return "" if plain is None else plain.group(1).strip()


def _total_size(headers: Message) -> int | None:
    ranged = re.search(r"/(\d+)$", headers.get("Content-Range", ""))
    if ranged is not None:
        return int(ranged.group(1))
    length = headers.get("Content-Length", "")
    return int(length) if length.isdigit() else None


# One request that asks for the file's first byte only. A file anyone may fetch answers with its name and size, a large one with a page that
# names them, a private one sends the browser to a sign-in page, and an unknown ID gets "not found".
def _probe(file_id: str) -> tuple[LinkState, str, int | None, str]:
    request = urllib.request.Request(f"""{DRIVE_FILE_ADDRESS}{file_id}""", headers={"Range": "bytes=0-0", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=DRIVE_PROBE_TIMEOUT_SECONDS) as response:
            if urlparse(response.geturl()).netloc.lower().startswith("accounts.google."):
                return "private", "", None, ""
            headers: Message = response.headers
            if "attachment" in headers.get("Content-Disposition", "").lower():
                return "found", _named_file(headers), _total_size(headers), ""
            if "text/html" not in headers.get("Content-Type", ""):
                return "unknown", "", None, ""
            page = response.read(DRIVE_PROBE_READ_BYTES).decode(encoding="utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return ("missing" if error.code == 404 else "private" if error.code in (401, 403) else "unknown"), "", None, ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return "offline", "", None, ""
    named = re.search(r'class="uc-name-size"><a[^>]*>([^<]+)</a>\s*\(([^)]+)\)', page)
    if named is not None:
        return "found", named.group(1), None, named.group(2)
    return ("busy" if "Too many users" in page else "unknown"), "", None, ""


def check_drive_link(text: str) -> DriveLink:
    typed = text.strip()
    file_id = _file_id(typed)
    link: DriveLink = {"form": "file", "id": file_id, "state": "unknown", "name": "", "size": None, "size_text": ""}
    if "/folders/" in typed:
        return {**link, "form": "folder", "id": ""}
    if re.fullmatch(DRIVE_ID_PATTERN, file_id) is None:
        return {**link, "form": "unrecognised", "id": ""}
    state, name, size, size_text = _probe(file_id)
    return {**link, "state": state, "name": name, "size": size, "size_text": size_text}


def read_download_place() -> DownloadPlace:
    folder = Path.home().joinpath(*DOWNLOAD_ROOT)
    return {"folder": str(folder), "free": shutil.disk_usage(Path.home()).free, "ready": importlib.util.find_spec("gdown") is not None}
