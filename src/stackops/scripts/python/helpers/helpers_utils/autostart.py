import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

import typer

if TYPE_CHECKING:
    from rich.table import Table

AutostartScope: TypeAlias = Literal["boot", "login"]
AutostartCategory: TypeAlias = Literal[
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
    stock: bool = False


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


def categorize(name: str, fallback: AutostartCategory = "other") -> AutostartCategory:
    lowered = name.lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in lowered for keyword in keywords):
            return category
    return fallback


def _systemctl_base(user: bool) -> list[str]:
    return ["systemctl", "--user"] if user else ["systemctl"]


def _list_enabled_services(user: bool) -> list[str]:
    process = subprocess.run(
        [*_systemctl_base(user), "list-unit-files", "--type=service", "--state=enabled", "--no-legend", "--plain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        return []
    units: list[str] = []
    for line in process.stdout.splitlines():
        fields = line.split()
        if fields and fields[0].endswith(".service"):
            units.append(fields[0])
    return units


def _parse_show_output(stdout: str) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    current_id: str | None = None
    for line in stdout.splitlines():
        if line.startswith("Id="):
            current_id = line[3:]
        elif line.startswith("Description=") and current_id is not None:
            descriptions[current_id] = line[12:].strip()
            current_id = None
    return descriptions


def _fetch_descriptions(units: list[str], user: bool) -> dict[str, str]:
    if not units:
        return {}
    base = _systemctl_base(user)
    properties = ["--property=Id", "--property=Description", "--no-pager"]
    # Template units such as getty@.service are not valid 'show' targets and would abort the whole batch.
    showable = [unit for unit in units if "@" not in unit]
    descriptions: dict[str, str] = {}
    chunk_size = 25
    for start in range(0, len(showable), chunk_size):
        chunk = showable[start : start + chunk_size]
        batch = subprocess.run([*base, "show", *chunk, *properties], capture_output=True, text=True, check=False)
        if batch.returncode == 0:
            descriptions.update(_parse_show_output(batch.stdout))
            continue
        for unit in chunk:
            single = subprocess.run([*base, "show", unit, *properties], capture_output=True, text=True, check=False)
            if single.returncode == 0:
                descriptions.update(_parse_show_output(single.stdout))
    return descriptions


def _parse_reboot_lines(content: str, source: str, scope: AutostartScope) -> list[AutostartEntry]:
    entries: list[AutostartEntry] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line.startswith("@reboot"):
            continue
        tokens = line.split()[1:]
        # Only keep the executable to avoid leaking any arguments that may carry secrets.
        while tokens and "=" in tokens[0] and not tokens[0].startswith(("/", ".", "@")):
            tokens = tokens[1:]
        executable = tokens[0] if tokens else "-"
        entries.append(
            AutostartEntry(
                name=executable,
                description="runs at reboot",
                category=categorize(executable),
                scope=scope,
                source=source,
            )
        )
    return entries


def _cron_reboot_entries() -> list[AutostartEntry]:
    entries: list[AutostartEntry] = []
    user_crontab = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    if user_crontab.returncode == 0:
        entries.extend(_parse_reboot_lines(user_crontab.stdout, "cron @reboot (user)", "login"))
    system_cron_files: list[Path] = []
    crontab_path = Path("/etc/crontab")
    if crontab_path.is_file():
        system_cron_files.append(crontab_path)
    cron_d = Path("/etc/cron.d")
    if cron_d.is_dir():
        system_cron_files.extend(sorted(path for path in cron_d.iterdir() if path.is_file()))
    for path in system_cron_files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        entries.extend(_parse_reboot_lines(content, f"cron @reboot ({path.name})", "boot"))
    return entries


def _rc_local_entries() -> list[AutostartEntry]:
    path = Path("/etc/rc.local")
    if not path.is_file():
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    has_commands = any(
        stripped
        for line in content.splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#") and stripped != "exit 0"
    )
    if not has_commands:
        return []
    return [AutostartEntry(name="rc.local", description="legacy boot script", category="other", scope="boot", source="/etc/rc.local")]


def _xdg_autostart_entries() -> list[AutostartEntry]:
    autostart_dir = Path.home() / ".config" / "autostart"
    if not autostart_dir.is_dir():
        return []
    entries: list[AutostartEntry] = []
    for desktop_file in sorted(autostart_dir.glob("*.desktop")):
        try:
            content = desktop_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        display_name = desktop_file.stem
        for line in content.splitlines():
            if line.startswith("Name="):
                display_name = line[5:].strip()
                break
        entries.append(
            AutostartEntry(
                name=display_name,
                description=desktop_file.name,
                category=categorize(display_name),
                scope="login",
                source="XDG autostart",
                stock=is_stock(display_name) or is_stock(desktop_file.name),
            )
        )
    return entries


def collect_autostart_entries() -> list[AutostartEntry]:
    entries: list[AutostartEntry] = []
    for user in (False, True):
        units = _list_enabled_services(user=user)
        descriptions = _fetch_descriptions(units, user=user)
        scope: AutostartScope = "login" if user else "boot"
        for unit in units:
            entries.append(
                AutostartEntry(
                    name=unit,
                    description=descriptions.get(unit, ""),
                    category=categorize(unit, fallback="system-os"),
                    scope=scope,
                    source="systemd",
                    stock=is_stock(unit),
                )
            )
    entries.extend(_cron_reboot_entries())
    entries.extend(_rc_local_entries())
    entries.extend(_xdg_autostart_entries())
    return entries


def build_autostart_table(entries: list[AutostartEntry], show_all: bool) -> "Table":
    from rich import box
    from rich.table import Table

    title = "Auto-start services and programs" if show_all else "Auto-start services and programs (notable)"
    table = Table(title=title, box=box.SIMPLE_HEAVY, header_style="bold cyan", show_lines=False)
    table.add_column("Category", no_wrap=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green", overflow="fold")
    table.add_column("Scope", style="yellow", no_wrap=True)
    table.add_column("Source", style="dim", no_wrap=True)
    for category in CATEGORY_ORDER:
        for entry in sorted((item for item in entries if item.category == category), key=lambda item: item.name):
            table.add_row(
                f"[{CATEGORY_STYLES[category]}]{CATEGORY_LABELS[category]}[/]",
                entry.name,
                entry.description or "-",
                entry.scope,
                entry.source,
            )
    return table


def print_autostart_report(show_all: bool = False) -> None:
    from rich.console import Console

    if shutil.which("systemctl") is None:
        raise RuntimeError("systemctl not found; autostart inspection requires systemd")
    entries = collect_autostart_entries()
    if not entries:
        typer.echo("No auto-start entries found")
        return
    visible = [entry for entry in entries if show_all or not entry.stock]
    hidden_count = len(entries) - len(visible)
    console = Console()
    console.print(build_autostart_table(visible, show_all=show_all))
    console.print("[dim]scope 'boot' = starts at system boot; 'login' = starts when you log in.[/dim]")
    if not show_all and hidden_count:
        console.print(f"[dim]{hidden_count} standard OS services hidden; pass --all to include them.[/dim]")
