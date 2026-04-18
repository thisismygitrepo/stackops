
"""Devops Devapps Install
"""

import json
from typing import Annotated, Literal, TypedDict

import typer

from stackops.utils.schemas.installer.installer_types import InstallRequest, InstallationResult, InstallerData


class InteractiveGroupPreview(TypedDict):
    type: Literal["package_group"]
    groupName: str
    apps: list[str]


def _render_preview_json(value: InstallerData | InteractiveGroupPreview) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _build_installer_option_to_data(installers: list[InstallerData]) -> dict[str, InstallerData]:
    from stackops.utils.installer_utils.installer_class import Installer

    installer_option_to_data: dict[str, InstallerData] = {}
    for installer_data in installers:
        option_label = Installer(installer_data=installer_data).get_description()
        if option_label in installer_option_to_data:
            raise ValueError(f"Duplicate installer option label: {option_label}")
        installer_option_to_data[option_label] = installer_data
    return installer_option_to_data


def _build_interactive_option_previews(
    category_display_to_name: dict[str, str], installer_option_to_data: dict[str, InstallerData]
) -> dict[str, str]:
    from stackops.jobs.installer.package_groups import PACKAGE_GROUP2NAMES, PACKAGE_NAME

    option_previews: dict[str, str] = {}
    for display_label, group_name in category_display_to_name.items():
        group_name_typed: PACKAGE_NAME = next(package_name for package_name in PACKAGE_GROUP2NAMES if package_name == group_name)
        option_previews[display_label] = _render_preview_json(
            InteractiveGroupPreview(
                type="package_group",
                groupName=group_name_typed,
                apps=list(PACKAGE_GROUP2NAMES[group_name_typed]),
            )
        )
    for option_label, installer_data in installer_option_to_data.items():
        option_previews[option_label] = _render_preview_json(installer_data)
    return option_previews


def main_installer_cli(
    which: Annotated[str | None, typer.Argument(..., help="Comma-separated list of program/groups names to install (if --group flag is set).")] = None,
    group: Annotated[bool, typer.Option(..., "--group", "-g", help="Treat 'which' as a group name. A group is bundle of apps.")] = False,
    interactive: Annotated[bool, typer.Option(..., "--interactive", "-i", help="Interactive selection of programs to install.")] = False,
    update: Annotated[bool, typer.Option(..., "--update", "-u", help="Allow reinstalling or upgrading already installed apps when supported.")] = False,
    version: Annotated[str | None, typer.Option(..., "--version", "-v", help="Specific version or tag to install when supported.")] = None,
) -> None:
    install_request = InstallRequest(version=version, update=update)
    if interactive:
        return install_interactively(install_request=install_request)
    if which is not None:
        if group:
            for a_group in [x.strip() for x in which.split(",") if x.strip() != ""]:
                return install_group(package_group=a_group, install_request=install_request)
        else:
            return install_clis(clis_names=[x.strip() for x in which.split(",") if x.strip() != ""], install_request=install_request)
    else:
        if group:
            from rich.console import Console
            from rich.table import Table
            console = Console()

            typer.echo("❌ You must provide a group name when using the --group/-g option.")
            from stackops.utils.installer_utils.installer_helper import get_group_name_to_repr
            res = get_group_name_to_repr()
            console.print("[bold blue]Here are the available groups:[/bold blue]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Group", style="cyan", no_wrap=True)
            table.add_column("AppsBundled", style="green", overflow="fold")
            for display, group_name in res.items():
                # Parse display
                if "   --   " in display:
                    group_part, items_part = display.split("   --   ", 1)
                    group_name_parsed = group_part.replace("📦 ", "").strip()
                    items_str = items_part.strip()
                else:
                    group_name_parsed = display
                    items_str = group_name
                table.add_row(group_name_parsed, items_str)
            console.print(table)
            raise typer.Exit(1)
    typer.echo("❌ You must provide either a program name/group name, or use --interactive/-ia option.")
    import click
    ctx = click.get_current_context()
    typer.echo(ctx.get_help())
    raise typer.Exit(1)


def install_interactively(install_request: InstallRequest) -> None:
    from stackops.utils.options import choose_from_options
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview
    from stackops.utils.installer_utils.installer_locator_utils import check_tool_exists
    from stackops.utils.installer_utils.installer_summary import render_installation_summary
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name
    from stackops.utils.installer_utils.installer_runner import get_installers
    from stackops.utils.installer_utils.installer_class import Installer
    from stackops.utils.installer_utils.installer_helper import get_group_name_to_repr
    from rich.console import Console
    from rich.panel import Panel

    installers = get_installers(os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
    installer_option_to_data = _build_installer_option_to_data(installers)
    category_display_to_name = get_group_name_to_repr()
    options = list(category_display_to_name.keys()) + list(installer_option_to_data.keys())

    if check_tool_exists("tv"):
        option_previews = _build_interactive_option_previews(
            category_display_to_name=category_display_to_name,
            installer_option_to_data=installer_option_to_data,
        )
        program_names = choose_from_dict_with_preview(
            options_to_preview_mapping=option_previews,
            extension="json",
            multi=True,
            preview_size_percent=55.0,
        )
    else:
        program_names = choose_from_options(
            multi=True,
            msg="Categories are prefixed with 📦",
            options=options,
            header="🚀 CHOOSE DEV APP OR CATEGORY",
            tv=True,
        )

    if program_names is None or len(program_names) == 0:
        Console().print(Panel("❓ Selection cancelled. Nothing to install.", title="Cancelled", border_style="yellow"))
        return

    installation_results: list[InstallationResult] = []
    for a_program_name in program_names:
        if a_program_name.startswith("📦 "):
            category_name = category_display_to_name.get(a_program_name)
            if category_name:
                install_group(package_group=category_name, install_request=install_request)
        else:
            an_installer_data = installer_option_to_data[a_program_name]
            installation_result = Installer(an_installer_data).install_robust(install_request=install_request)
            installation_results.append(installation_result)
    if installation_results:
        render_installation_summary(results=installation_results, console=Console(), title="📊 Installation Summary")


def install_group(package_group: str, install_request: InstallRequest) -> None:
    from stackops.utils.installer_utils.installer_runner import get_installers, install_bulk
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name
    from rich.console import Console
    from rich.panel import Panel
    # from rich.table import Table
    from stackops.jobs.installer.package_groups import PACKAGE_GROUP2NAMES, PACKAGE_NAME
    if package_group in PACKAGE_GROUP2NAMES:
        panel = Panel(f"[bold yellow]Installing programs from category: [green]{package_group}[/green][/bold yellow]", title="[bold blue]📦 Category Installation[/bold blue]", border_style="blue", padding=(1, 2))
        console = Console()
        console.print(panel)
        package_group_typed: PACKAGE_NAME = next(group_name for group_name in PACKAGE_GROUP2NAMES if group_name == package_group)
        installers_ = get_installers(os=get_os_name(), arch=get_normalized_arch(), which_cats=[package_group_typed])
        install_bulk(installers_data=installers_, install_request=install_request)
        return
    console = Console()
    console.print(f"❌ ERROR: Unknown package group: {package_group}. Available groups are: {list(PACKAGE_GROUP2NAMES.keys())}")


def install_clis(clis_names: list[str], install_request: InstallRequest) -> None:
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name
    from stackops.utils.installer_utils.installer_summary import render_installation_summary
    from stackops.utils.installer_utils.installer_runner import get_installers
    from stackops.utils.installer_utils.installer_class import Installer
    from rich.console import Console
    all_installers_data = get_installers(os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
    total_results: list[InstallationResult] = []
    for a_cli_name in clis_names:
        if "github.com" in a_cli_name.lower():
            from stackops.utils.installer_utils.install_from_url import install_from_github_url
            install_from_github_url(github_url=a_cli_name)
            continue
        elif a_cli_name.startswith("https://") or a_cli_name.startswith("http://"):
            print(f"⏳ Installing from binary URL: {a_cli_name} ...")
            from stackops.utils.installer_utils.install_from_url import install_from_binary_url
            install_from_binary_url(binary_url=a_cli_name)
            continue

        selected_installer = None
        for installer in all_installers_data:
            app_name = installer["appName"]
            if app_name.lower() == a_cli_name.lower():
                selected_installer = installer
                break
        if selected_installer is None:
            from stackops.utils.installer_utils.installer_helper import handle_installer_not_found
            clis_names_chosen_interactively = handle_installer_not_found(a_cli_name, all_installers_data)
            if len(clis_names_chosen_interactively)  == 0:
                continue
            install_clis(clis_names=clis_names_chosen_interactively, install_request=install_request)
            continue
        result = Installer(selected_installer).install_robust(install_request=install_request)
        total_results.append(result)
    if total_results:
        render_installation_summary(results=total_results, console=Console(), title="📊 Installation Results")
    return None
def install_if_missing(which: str, binary_name: str | None, verbose: bool) -> bool:
    from stackops.utils.installer_utils.installer_locator_utils import check_tool_exists
    if binary_name is None:
        binary_name = which
    exists = check_tool_exists(binary_name)
    if exists:
        if verbose:
            print(f"✅ {which} is already installed.")
        return True
    if verbose:
        print(f"⏳ {which} not found. Installing...")
    try:
        main_installer_cli(which=which, interactive=False, update=False, version=None)
        return True
    except Exception as e:
        if verbose:
            print(f"❌ Error installing {which}: {e}")
    return False
