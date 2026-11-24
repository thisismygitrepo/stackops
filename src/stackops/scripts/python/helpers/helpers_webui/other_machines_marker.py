import base64
import json
import os
import re
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_webui.constants import MACHINE_HOME_ADDRESS_PATTERN, MACHINE_OPENED_FROM_VARIABLE


class MachineSummary(TypedDict):
    name: str
    user: str
    platform: str


# What a web UI started from another machine's page knows about where it came from: that machine's name, the address its server has in the
# person's browser, and the name this machine goes by in that machine's SSH config.
class OpenedFrom(TypedDict):
    name: str
    address: str
    machine: str


def read_opened_from() -> OpenedFrom | None:
    # Taken out of the environment, so the commands this server runs do not carry it on.
    text = os.environ.pop(MACHINE_OPENED_FROM_VARIABLE, "")
    if text == "":
        return None
    fields: dict[str, object] = json.loads(base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)))
    name, address, machine = fields["name"], fields["address"], fields["machine"]
    # The address becomes a link on the page, so only a plain web address passes.
    if not (isinstance(name, str) and isinstance(address, str) and isinstance(machine, str)) or re.fullmatch(MACHINE_HOME_ADDRESS_PATTERN, address) is None:
        raise ValueError(f"""{MACHINE_OPENED_FROM_VARIABLE} does not hold a machine name and a web UI address.""")
    return {"name": name, "address": address, "machine": machine}
