#!/usr/bin/env python3
import random
import shlex
import string


RUN_ALL_STATE_OPTION = "@stackops-run-all-state"


def generate_random_suffix(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def shell_quote(value: str) -> str:
    return shlex.quote(value)
