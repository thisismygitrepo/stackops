import subprocess
import sys
from collections.abc import Sequence

from stackops.scripts.python.helpers.helpers_devops.devops_status_constants import ALL_STATUS_SECTIONS, StatusSection


def resolve_sections(
    *,
    machine: bool,
    shell: bool,
    repos: bool,
    ssh: bool,
    configs: bool,
    apps: bool,
    backup: bool,
) -> tuple[StatusSection, ...]:
    """Resolve CLI section flags into the ordered set of sections to display."""
    section_flags: dict[StatusSection, bool] = {
        "system": machine,
        "shell": shell,
        "repos": repos,
        "ssh": ssh,
        "configs": configs,
        "apps": apps,
        "backup": backup,
    }
    selected_sections = tuple(section for section in ALL_STATUS_SECTIONS if section_flags[section])
    return selected_sections or ALL_STATUS_SECTIONS


def _run_status_tui(*, sections: tuple[StatusSection, ...]) -> None:
    from stackops.scripts.python.helpers.helpers_devops.devops_status_tui import StatusApp

    app = StatusApp(sections=sections)
    app.run()


def main(*, sections: Sequence[StatusSection], plain: bool) -> None:
    if plain or not (sys.stdin.isatty() and sys.stdout.isatty()):
        from rich.console import Console

        from stackops.scripts.python.helpers.helpers_devops.devops_status_data import collect_status_section
        from stackops.scripts.python.helpers.helpers_devops.devops_status_display import display_report_footer, display_report_header

        console = Console()
        display_report_header()
        for section in sections:
            console.print(collect_status_section(section).content)
        display_report_footer()
        return

    from stackops.utils.meta import lambda_to_python_script

    worker_source = lambda_to_python_script(
        lambda: _run_status_tui(sections=tuple(sections)),
        in_global=True,
        import_module=False,
    )
    result = subprocess.run(
        ["uv", "run", "--no-project", "--python", sys.executable, "--with", "textual", "python", "-c", worker_source],
        check=False,
    )
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main(sections=ALL_STATUS_SECTIONS, plain=False)
