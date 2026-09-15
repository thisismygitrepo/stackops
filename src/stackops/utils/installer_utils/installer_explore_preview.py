from io import StringIO
from shutil import get_terminal_size

from rich import box
from rich.console import Console, Group, RenderableType
from rich.table import Table
from rich.text import Text

from stackops.utils.installer_utils.linux_package_manager import LINUX_PACKAGE_MANAGERS
from stackops.utils.schemas.installer.installer_types import CPU_ARCHITECTURES, OPERATING_SYSTEMS, InstallerData


def _render_preview(renderable: RenderableType, preview_size_percent: float) -> str:
    terminal_width = get_terminal_size(fallback=(120, 40)).columns
    preview_width = max(20, int(terminal_width * preview_size_percent / 100) - 4)
    output = StringIO()
    console = Console(file=output, width=preview_width, color_system=None, force_terminal=False, safe_box=False)
    console.print(renderable)
    return output.getvalue()


def render_category_preview(
    category_label: str,
    label: str,
    description: str,
    installers: list[InstallerData],
    preview_size_percent: float,
) -> str:
    table = Table(
        box=box.ROUNDED,
        expand=True,
        show_lines=True,
        caption=Text(f"""{len(installers)} apps · {category_label}"""),
        caption_justify="left",
    )
    table.add_column("Application", ratio=1, overflow="fold")
    table.add_column("Description", ratio=3, overflow="fold")
    for installer_data in sorted(installers, key=lambda installer_data: installer_data["appName"].lower()):
        table.add_row(Text(installer_data["appName"]), Text(installer_data["doc"]))
    return _render_preview(
        renderable=Group(Text(label), Text(description), Text(""), table),
        preview_size_percent=preview_size_percent,
    )


def render_installer_preview(installer_data: InstallerData, preview_size_percent: float) -> str:
    lines: list[str] = [
        f"""📦 {installer_data['appName']}""",
        installer_data["doc"],
        "",
        f"""⚖️ {installer_data['license']}""",
    ]
    if installer_data["repoURL"] != "CMD":
        lines.append(f"""🔗 {installer_data['repoURL']}""")
    lines.append(f"""🏷️ {' · '.join(installer_data['categoryLabels'])}""")
    if "lastCommitDate" in installer_data:
        lines.append(f"""📅 Last commit: {installer_data['lastCommitDate'][:10]}""")
    lines.extend(["", "Platforms"])

    architectures: dict[CPU_ARCHITECTURES, str] = {"amd64": "x86_64", "arm64": "ARM64"}
    operating_systems: dict[OPERATING_SYSTEMS, str] = {"windows": "🪟 Windows", "linux": "🐧 Linux", "darwin": "🍎 macOS"}
    for operating_system, platform_label in operating_systems.items():
        available_architectures: list[str] = []
        for architecture, architecture_label in architectures.items():
            pattern = installer_data["fileNamePattern"][architecture][operating_system]
            if isinstance(pattern, dict):
                package_managers = [package_manager for package_manager in LINUX_PACKAGE_MANAGERS if pattern[package_manager] is not None]
                if package_managers:
                    available_architectures.append(f"""{architecture_label} ({', '.join(package_managers)})""")
            elif pattern is not None:
                available_architectures.append(architecture_label)
        support = " · ".join(available_architectures) if available_architectures else "Unavailable"
        lines.append(f"""{platform_label} · {support}""")
    return _render_preview(renderable=Text("\n".join(lines)), preview_size_percent=preview_size_percent)
