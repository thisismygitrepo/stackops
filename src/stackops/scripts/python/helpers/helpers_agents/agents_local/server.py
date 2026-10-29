from ipaddress import ip_address
from urllib.parse import urlsplit, urlunsplit


def normalize_host(*, host: str, default_host: str, default_port: int, backend: str) -> str:
    value = host.strip() or default_host
    scheme, separator, address = value.partition("://")
    if separator:
        default_port = 443 if scheme == "https" else 80
    else:
        scheme, address = "http", value
    authority, slash, path = address.partition("/")
    if authority.count(":") > 1 and not authority.startswith("["):
        authority = f"""[{ip_address(authority)}]"""
    parsed = urlsplit(f"""{scheme}://{authority}{slash}{path}""")
    if parsed.scheme not in {"http", "https"} or parsed.query or parsed.fragment or parsed.username is not None:
        raise ValueError(f"""{backend} host must be an HTTP(S) address without credentials, query, or fragment""")
    hostname = parsed.hostname or ("127.0.0.1" if authority.startswith(":") else "")
    if not hostname or any(character.isspace() for character in hostname):
        raise ValueError(f"""{backend} host must include a valid hostname""")
    hostname = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(hostname, hostname)
    if ":" in hostname:
        hostname = f"""[{hostname}]"""
    port = parsed.port if parsed.port is not None else default_port
    if port == 0:
        raise ValueError(f"""{backend} host port must be between 1 and 65535""")
    return urlunsplit((parsed.scheme, f"""{hostname}:{port}""", parsed.path.rstrip("/"), "", ""))
