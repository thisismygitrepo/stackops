import glob
import re
from pathlib import Path
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_webui.constants import MACHINE_NAME_PATTERN, SSH_CONFIG_INCLUDE_DEPTH, SSH_GIT_HOSTS

CONFIG_LINE = re.compile(r"([A-Za-z]+)[ \t]*=?[ \t]*(.*)")
CONFIG_WORD = re.compile(r'"([^"]*)"|(\S+)')


class SshHost(TypedDict):
    name: str
    address: str


class HostBlock(TypedDict):
    names: list[str]
    settings: dict[str, str]


# The machines the SSH config names, in its order. Design choice: the file is read here and not asked of `ssh -G`, which answers for one name
# at a time and cannot list them. Only `Host` lines count, so a name that exists through a `Match` block alone is not offered.
def read_ssh_hosts() -> list[SshHost]:
    ssh_folder = Path.home().joinpath(".ssh")
    blocks: list[HostBlock] = []

    def read_file(path: Path, depth: int) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:  # No SSH config, or an `Include` of a file that is not there, which SSH also passes over.
            return
        block: HostBlock | None = None
        for line in text.splitlines():
            parts = CONFIG_LINE.fullmatch(line.strip())
            if parts is None:  # Empty lines and comments.
                continue
            keyword = parts.group(1).lower()
            words = [quoted or bare for quoted, bare in CONFIG_WORD.findall(parts.group(2))]
            match keyword:
                case "host" | "match":
                    block = {"names": words if keyword == "host" else [], "settings": {}}
                    blocks.append(block)
                case "hostname" | "user" if block is not None and words:
                    block["settings"].setdefault(keyword, words[0])  # SSH keeps the first value it meets.
                case "include" if depth < SSH_CONFIG_INCLUDE_DEPTH:
                    for word in words:
                        pattern = Path(word).expanduser()
                        for included in sorted(glob.glob(str(pattern if pattern.is_absolute() else ssh_folder.joinpath(pattern)))):
                            read_file(Path(included), depth + 1)
                case _:
                    continue

    read_file(ssh_folder.joinpath("config"), 0)
    hosts: dict[str, SshHost] = {}
    for block in blocks:
        address = block["settings"].get("hostname", "")
        target = (address or " ".join(block["names"])).lower()
        if block["settings"].get("user", "").lower() == "git" or any(word == host or word.endswith(f""".{host}""") for word in target.split() for host in SSH_GIT_HOSTS):
            continue
        names = [name for name in block["names"] if re.fullmatch(MACHINE_NAME_PATTERN, name) is not None]
        # Several names with one fixed address are one machine, so the first stands for it. Without an address, or with one built from the
        # name (%h), each name is a machine of its own.
        for name in names[:1] if address != "" and "%" not in address else names:
            hosts.setdefault(name, {"name": name, "address": address})
    return list(hosts.values())
