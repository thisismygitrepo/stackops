import shutil
import subprocess
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.autostart_common import (
    AutostartEntry,
    AutostartScope,
    categorize,
    is_stock,
)


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
                category=categorize(executable, fallback="other"),
                scope=scope,
                source=source,
                stock=False,
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
    return [AutostartEntry(name="rc.local", description="legacy boot script", category="other", scope="boot", source="/etc/rc.local", stock=False)]


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
                category=categorize(display_name, fallback="other"),
                scope="login",
                source="XDG autostart",
                stock=is_stock(display_name) or is_stock(desktop_file.name),
            )
        )
    return entries


def collect_linux_entries() -> list[AutostartEntry]:
    if shutil.which("systemctl") is None:
        raise RuntimeError("systemctl not found; Linux autostart inspection requires systemd")
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
    if shutil.which("crontab") is not None:
        entries.extend(_cron_reboot_entries())
    entries.extend(_rc_local_entries())
    entries.extend(_xdg_autostart_entries())
    return entries
