from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenSSHCommandDestination:
    hostname: str
    username: str | None
    port: int | None


def parse_open_ssh_destination(destination: str) -> OpenSSHCommandDestination:
    if destination == "":
        raise ValueError("SSH destination must not be empty.")

    inline_username, username_separator, address = destination.rpartition("@")
    if not username_separator:
        inline_username = ""
        address = destination
    elif inline_username == "" or address == "":
        raise ValueError(f"Invalid SSH destination: {destination!r}.")

    inline_port: int | None = None
    if address.startswith("["):
        closing_bracket = address.find("]")
        if closing_bracket == -1:
            raise ValueError(f"Invalid bracketed SSH hostname: {address!r}.")
        hostname = address[1:closing_bracket]
        port_suffix = address[closing_bracket + 1 :]
        if port_suffix != "":
            if not port_suffix.startswith(":"):
                raise ValueError(f"Invalid bracketed SSH destination: {address!r}.")
            inline_port = _parse_port(port_text=port_suffix[1:], source=destination)
    elif address.count(":") == 1:
        hostname, port_text = address.rsplit(":", maxsplit=1)
        inline_port = _parse_port(port_text=port_text, source=destination)
    else:
        hostname = address

    if hostname == "":
        raise ValueError(f"SSH hostname must not be empty: {destination!r}.")
    if any(character.isspace() or ord(character) < 32 for character in hostname):
        raise ValueError(f"SSH hostname contains whitespace or control characters: {hostname!r}.")
    if inline_username != "" and any(character.isspace() or ord(character) < 32 for character in inline_username):
        raise ValueError(f"SSH username contains whitespace or control characters: {inline_username!r}.")
    return OpenSSHCommandDestination(hostname=hostname, username=inline_username or None, port=inline_port)


def build_open_ssh_destination_arguments(destination: OpenSSHCommandDestination) -> tuple[str, ...]:
    arguments: list[str] = []
    if destination.username is not None:
        arguments.extend(("-l", destination.username))
    if destination.port is not None:
        arguments.extend(("-p", str(destination.port)))
    arguments.extend(("--", destination.hostname))
    return tuple(arguments)


def _parse_port(port_text: str, source: str) -> int:
    try:
        port = int(port_text)
    except ValueError as error:
        raise ValueError(f"Invalid SSH port from {source}: {port_text!r}.") from error
    if not 1 <= port <= 65_535:
        raise ValueError(f"SSH port from {source} must be between 1 and 65535, received {port}.")
    return port
