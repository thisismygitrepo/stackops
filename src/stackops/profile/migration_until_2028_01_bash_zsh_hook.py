import platform
from pathlib import Path

from stackops.profile.shell_profile_source import build_shell_profile_source

STALE_HOOKS: tuple[str, ...] = (
    "source $HOME/.config/stackops/settings/shells/bash/init.sh",
    "source $HOME/.config/stackops/settings/shells/zsh/init.sh",
)


def migrate_stale_shell_hooks(config_root: Path) -> None:
    from rich.console import Console
    from rich.panel import Panel

    if platform.system() == "Windows":
        return
    console = Console()
    for shell_variable in ("/bin/bash", "/bin/zsh"):
        profile_source = build_shell_profile_source(system_name=platform.system(), shell_variable=shell_variable, config_root=config_root)
        profile_path = profile_source.profile_path
        if not profile_path.is_file():
            continue
        profile_text = profile_path.read_text(encoding="utf-8")
        profile_lines = profile_text.splitlines(keepends=True)
        if not any(line.strip() in STALE_HOOKS for line in profile_lines):
            continue
        source_line_present = any(line.strip() == profile_source.source_line for line in profile_lines)
        migrated_lines: list[str] = []
        for line in profile_lines:
            if line.strip() not in STALE_HOOKS:
                migrated_lines.append(line)
            elif not source_line_present:
                migrated_lines.append(line.replace(line.strip(), profile_source.source_line, 1))
                source_line_present = True
        backup_path = profile_path.with_name(f"""{profile_path.name}.before_stackops_bash_zsh_migration""")
        backup_path.write_text(profile_text, encoding="utf-8")
        profile_path.write_text("".join(migrated_lines), encoding="utf-8")
        console.print(
            Panel(
                f"""🔁 MIGRATION | StackOps merged its bash and zsh init into one script.
Updated the hook in `{profile_path}` to `{profile_source.source_line}`.
Backup of the previous file: `{backup_path}`""",
                title="[bold yellow]Shell Hook Migration[/bold yellow]",
                border_style="yellow",
            )
        )
