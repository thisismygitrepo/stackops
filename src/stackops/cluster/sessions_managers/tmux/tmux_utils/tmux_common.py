#!/usr/bin/env python3
from pathlib import Path
import random
import shlex
import string


def generate_random_suffix(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def normalize_cwd(cwd: str) -> str:
    normalized = cwd.replace("$HOME", str(Path.home()))
    return str(Path(normalized).expanduser())


def shell_quote(value: str) -> str:
    return shlex.quote(value)