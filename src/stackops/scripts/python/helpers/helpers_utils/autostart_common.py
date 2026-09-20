from dataclasses import dataclass
from typing import Literal

type AutostartScope = Literal["boot", "login"]
type AutostartCategory = Literal[
    "remote-access",
    "containers-storage",
    "apps-services",
    "monitoring-hardware",
    "desktop-session",
    "system-os",
    "other",
]

CATEGORY_ORDER: tuple[AutostartCategory, ...] = (
    "remote-access",
    "containers-storage",
    "apps-services",
    "monitoring-hardware",
    "desktop-session",
    "system-os",
    "other",
)

CATEGORY_LABELS: dict[AutostartCategory, str] = {
    "remote-access": "🌐 network",
    "containers-storage": "📦 storage",
    "apps-services": "🧩 apps",
    "monitoring-hardware": "📈 monitoring",
    "desktop-session": "🖥 desktop",
    "system-os": "🧱 system",
    "other": "❓ other",
}

CATEGORY_FILTERS: dict[str, AutostartCategory] = {
    "network": "remote-access",
    "storage": "containers-storage",
    "apps": "apps-services",
    "monitoring": "monitoring-hardware",
    "desktop": "desktop-session",
    "system": "system-os",
    "other": "other",
}

CATEGORY_STYLES: dict[AutostartCategory, str] = {
    "remote-access": "bold cyan",
    "containers-storage": "bold blue",
    "apps-services": "bold magenta",
    "monitoring-hardware": "bold yellow",
    "desktop-session": "bold green",
    "system-os": "bold white",
    "other": "dim",
}

CATEGORY_RULES: list[tuple[AutostartCategory, tuple[str, ...]]] = [
    (
        "remote-access",
        (
            "tailscale", "cloudflared", "warp", "ssh", "samba", "smbd", "nmbd", "avahi",
            "network", "resolve", "wpa_supplicant", "modemmanager", "chrony", "ufw",
            "firewalld", "rpcbind", "iscsi", "openvpn", "wireguard", "zerotier",
            "netbird", "nebula", "frp", "ngrok", "code-tunnel", "nfs",
        ),
    ),
    (
        "containers-storage",
        ("docker", "containerd", "podman", "lvm", "multipath", "e2scrub", "blk-", "mdmon", "dm-event", "zfs", "sanoid", "smartd"),
    ),
    (
        "apps-services",
        (
            "ollama", "redis", "postgres", "mysql", "mariadb", "mongo", "nginx",
            "apache", "caddy", "grafana", "prometheus", "homeassistant", "syncthing",
            "jellyfin", "plex", "kodi", "cups", "bluetooth", "mosquitto", "mqtt",
            "influx", "clickhouse", "rabbitmq", "memcached",
        ),
    ),
    (
        "monitoring-hardware",
        ("atop", "sysstat", "thermal", "gpu", "fwupd", "upower", "power", "sensor", "acpid"),
    ),
    (
        "desktop-session",
        ("pipewire", "wireplumber", "pulse", "switcheroo", "xdg", "gnome", "gdm", "sddm", "lightdm", "plasma", "kde", "colord", "filter-chain", "session"),
    ),
]


@dataclass
class AutostartEntry:
    name: str
    description: str
    category: AutostartCategory
    scope: AutostartScope
    source: str
    stock: bool


# Units and programs that ship with a stock Ubuntu/Debian install; hidden unless --all is passed.
STOCK_PREFIXES: tuple[str, ...] = (
    "systemd-", "cloud-init", "cloud-config", "cloud-final", "snapd", "snap.",
    "networkmanager", "networkd-dispatcher", "plymouth", "getty@", "user@", "dbus",
    "polkit", "modemmanager", "avahi", "wpa_supplicant", "chrony", "chronyd", "ufw",
    "rpcbind", "open-iscsi", "iscsid", "accounts-daemon", "apparmor", "apport", "atd",
    "cron", "anacron", "dmesg", "e2scrub", "finalrd", "grub-", "keyboard-setup",
    "console-setup", "lvm2", "multipath", "open-vm-tools", "vgauth", "pollinate",
    "rsyslog", "secureboot-db", "setvtrgb", "thermald", "gpu-manager", "ua-",
    "ubuntu-advantage", "udisks2", "unattended-upgrades", "blk-availability", "nfs-",
    "pipewire", "wireplumber", "switcheroo-control", "session-migration",
    "xdg-desktop-portal", "gnome-", "gdm", "sddm", "lightdm", "colord", "cups",
    "bluetooth", "upower", "fwupd", "power-profiles", "iio-sensor", "packagekit",
    "whoopsie", "kerneloops", "motd", "plocate", "fstrim", "logrotate", "dpkg-",
    "apt-", "man-db", "popularity-contest", "qemu-guest-agent", "spice-vdagentd",
    "x11-common", "acpid", "alsa-", "org.gnome", "org.kde", "update-notifier",
    "im-launch", "nm-applet", "snap-",
)


def is_stock(name: str) -> bool:
    lowered = name.lower().removesuffix(".service")
    return lowered.startswith(STOCK_PREFIXES)


def categorize(name: str, fallback: AutostartCategory) -> AutostartCategory:
    lowered = name.lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in lowered for keyword in keywords):
            return category
    return fallback
