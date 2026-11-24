from typing import Final

# Key files that are not keys to sign in with: a certificate sits beside its key under the same name.
SSH_CERTIFICATE_SUFFIX: Final[str] = "-cert.pub"
SSH_FINGERPRINT_PREFIX: Final[str] = "SHA256:"
# The longest text the page may send to be checked as public keys. A key line is a few hundred characters; an RSA one about 750.
SSH_KEY_TEXT_LIMIT: Final[int] = 64 * 1024

# How long a stopped forward is given to go before the answer says it is still there.
FORWARD_STOP_WAIT_SECONDS: Final[float] = 2.5
FORWARD_STOP_POLL_SECONDS: Final[float] = 0.1
# What the port-mapping command puts on every SSH command line it builds (`cli_ssh_port.build_map_port_command`), and only it.
FORWARD_STACKOPS_MARKS: Final[tuple[str, ...]] = ("ExitOnForwardFailure=yes", "ClearAllForwardings=no", "ForkAfterAuthentication=no")
# What the machine switcher puts on the SSH command lines of the tunnels it opens (`constants.MACHINE_SSH_OPTIONS`), and only it.
FORWARD_SWITCHER_MARKS: Final[tuple[str, ...]] = ("RemoteCommand=none", "ExitOnForwardFailure=no")

WIFI_COMMAND_SECONDS: Final[float] = 5.0
# The system report with the signal in it takes about three seconds on a Mac, so the page asks for it apart from everything else.
WIFI_SIGNAL_SECONDS: Final[float] = 20.0
WIFI_SCAN_SECONDS: Final[float] = 30.0
WIFI_LOGIN_TAG: Final[str] = "wifi"
# Signal strength in dBm that counts as full and as none when it is shown as a share.
WIFI_STRONGEST_DBM: Final[int] = -50
WIFI_WEAKEST_DBM: Final[int] = -100

WARP_COMMAND: Final[str] = "warp-cli"
WARP_STATUS_SECONDS: Final[float] = 8.0

CLOUDFLARED_COMMAND: Final[str] = "cloudflared"
# Where the tunnel commands of the CLI expect things to be (`cli_cloudflare.py`, `cli_cloudflare_tunnel.py`).
CLOUDFLARED_DEFAULT_BINARY: Final[str] = "~/.local/bin/cloudflared"
CLOUDFLARED_USER_FOLDER: Final[str] = ".cloudflared"
CLOUDFLARED_CONFIG_NAMES: Final[tuple[str, ...]] = ("config.yml", "config.yaml")
CLOUDFLARED_SERVICE_CONFIG: Final[str] = "/etc/cloudflared/config.yml"
CLOUDFLARED_SERVICE_NAME: Final[str] = "cloudflared"
CLOUDFLARED_BACKGROUND_UNIT: Final[str] = "cloudflared-tunnel"
CLOUDFLARED_LOCAL_SECONDS: Final[float] = 5.0
CLOUDFLARED_ACCOUNT_SECONDS: Final[float] = 25.0
# How many connections to Cloudflare one running copy of a tunnel keeps open.
CLOUDFLARED_CONNECTIONS_PER_CONNECTOR: Final[int] = 4
