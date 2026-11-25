import hashlib
import json
import subprocess
import sys
import time
from typing import TypedDict, cast


class ClipboardClearRequest(TypedDict):
    seconds: int
    digest: str
    copy: list[str]
    paste: list[str]


def clipboard_digest(content: bytes) -> str:
    return hashlib.sha256(content.rstrip(b"\r\n")).hexdigest()


def main() -> None:
    request = cast(ClipboardClearRequest, json.loads(sys.stdin.read()))
    time.sleep(request["seconds"])
    pasted = subprocess.run(request["paste"], stdin=subprocess.DEVNULL, capture_output=True, check=True).stdout
    if clipboard_digest(pasted) == request["digest"]:
        subprocess.run(request["copy"], input=b"", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


if __name__ == "__main__":
    main()
