import base64
import hashlib
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from stackops.scripts.python.helpers.helpers_serve.constants import VENDOR_CACHE_FOLDER, VENDOR_DOWNLOAD_TIMEOUT_SECONDS


@dataclass(frozen=True)
class VendorAsset:
    url: str
    sha384: str
    media_type: str


VENDOR_ASSETS: Final[dict[str, VendorAsset]] = {
    "xterm.mjs": VendorAsset(
        url="https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/lib/xterm.mjs",
        sha384="8Xik+BkzF4UFDtZa8HkUiQ0FE/Xl+03xMuv69uQB3ichDzm8dWs4kPRihQxSZDiY",
        media_type="text/javascript",
    ),
    "xterm.css": VendorAsset(
        url="https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/css/xterm.css",
        sha384="n2n7twoohnW+d3myBKaUgl7DSiwidw6MkQy9oesGzkPpMjejKRR3XlnD+5yCdtBD",
        media_type="text/css",
    ),
    "addon-fit.mjs": VendorAsset(
        url="https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.11.0/lib/addon-fit.mjs",
        sha384="0/1EW6dUPoaun7dgdlOtb5Wk8x5UQRW6hYM3ihuCCnaA2Xd4HwMFcn378RpxmoAc",
        media_type="text/javascript",
    ),
    "plotly.min.js": VendorAsset(
        url="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@4.3.0/plotly.min.js",
        sha384="AtW63zbFwwiEVUeSPFC1ydmqJUwWWoXmyZHP8OC449teZ+00wVajF4cFhd/hy7jG",
        media_type="text/javascript",
    ),
}


def resolve_vendor_asset(name: str) -> Path:
    import requests

    asset = VENDOR_ASSETS[name]
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME", "")
    cache_root = Path(xdg_cache_home).expanduser() if xdg_cache_home != "" else Path.home().joinpath(".cache")
    cache_path = cache_root.joinpath("stackops", VENDOR_CACHE_FOLDER, f"""{base64.b64decode(asset.sha384).hex()[:16]}-{name}""")
    if cache_path.is_file():
        return cache_path
    response = requests.get(asset.url, timeout=VENDOR_DOWNLOAD_TIMEOUT_SECONDS)
    response.raise_for_status()
    digest = base64.b64encode(hashlib.sha384(response.content).digest()).decode("ascii")
    if digest != asset.sha384:
        raise ValueError(f"""Downloaded {asset.url} does not match its pinned SHA-384 (got {digest}).""")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = cache_path.with_name(f"""{cache_path.name}.{os.getpid()}.{threading.get_ident()}.part""")
    partial_path.write_bytes(response.content)
    partial_path.replace(cache_path)
    return cache_path
