from pathlib import Path

import typer

from stackops.utils.installer_utils.installer_explore_preview import render_category_preview, render_installer_preview
from stackops.utils.schemas.installer.installer_categories import installer_category_definition
from stackops.utils.schemas.installer.installer_types import (
    INSTALLER_CATEGORY_LABELS,
    InstallRequest,
    InstallationResult,
    InstallerCategoryLabel,
    InstallerData,
    InstallerDataSource,
)


def _build_installer_option_to_data(installers: list[InstallerData]) -> dict[str, InstallerData]:
    from stackops.utils.installer_utils.installer_class import Installer

    installer_option_to_data: dict[str, InstallerData] = {}
    for installer_data in installers:
        option_label = Installer(installer_data=installer_data).get_description()
        if option_label in installer_option_to_data:
            raise ValueError(f"Duplicate installer option label: {option_label}")
        installer_option_to_data[option_label] = installer_data
    return installer_option_to_data


def _group_installers_by_category_label(installers: list[InstallerData]) -> dict[InstallerCategoryLabel, list[InstallerData]]:
    category_to_installers: dict[InstallerCategoryLabel, list[InstallerData]] = {}
    for installer_data in installers:
        for category_label in installer_data["categoryLabels"]:
            category_to_installers.setdefault(category_label, []).append(installer_data)
    return category_to_installers


def _build_category_label_options(category_to_installers: dict[InstallerCategoryLabel, list[InstallerData]]) -> dict[str, InstallerCategoryLabel]:
    category_option_to_label: dict[str, InstallerCategoryLabel] = {}
    for category_label in INSTALLER_CATEGORY_LABELS:
        if category_label not in category_to_installers:
            continue
        title = installer_category_definition(label=category_label)["title"]
        installer_count = len(category_to_installers[category_label])
        option_label = f"🏷 {category_label:<36} {installer_count:>3} apps  --  {title}"
        category_option_to_label[option_label] = category_label
    return category_option_to_label


def _build_category_label_option_previews(
    category_option_to_label: dict[str, InstallerCategoryLabel],
    category_to_installers: dict[InstallerCategoryLabel, list[InstallerData]],
    preview_size_percent: float,
) -> dict[str, str]:
    option_previews: dict[str, str] = {}
    for option_label, category_label in category_option_to_label.items():
        category_definition = installer_category_definition(label=category_label)
        option_previews[option_label] = render_category_preview(
            category_label=category_label,
            label=category_definition["title"],
            description=category_definition["description"],
            installers=category_to_installers[category_label],
            preview_size_percent=preview_size_percent,
        )
    return option_previews


def _dedupe_installers(installers: list[InstallerData]) -> list[InstallerData]:
    app_name_to_installer: dict[str, InstallerData] = {}
    for installer_data in installers:
        app_name_to_installer.setdefault(installer_data["appName"].lower(), installer_data)
    return sorted(app_name_to_installer.values(), key=lambda installer_data: installer_data["appName"].lower())


def explore_installers_by_category_labels(
    install_request: InstallRequest,
    category_labels: list[str] | None,
    source: InstallerDataSource,
    user_path: Path | None,
) -> None:
    from rich.console import Console
    from rich.panel import Panel

    from stackops.utils.installer_utils.installer_class import Installer
    from stackops.utils.cli_utils.command_lookup import check_tool_exists
    from stackops.utils.installer_utils.installer_runner import get_installers_from_source
    from stackops.utils.installer_utils.installer_summary import render_installation_summary
    from stackops.utils.options_utils.options import choose_from_options
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name

    console = Console()
    installers = get_installers_from_source(source=source, user_path=user_path, os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
    category_to_installers = _group_installers_by_category_label(installers=installers)
    category_option_to_label = _build_category_label_options(category_to_installers=category_to_installers)

    selected_category_labels: list[InstallerCategoryLabel]
    if category_labels is None:
        selected_category_options: list[str] | None
        if check_tool_exists("tv"):
            category_preview_size_percent = 60.0
            selected_category_options = choose_from_dict_with_preview(
                options_to_preview_mapping=_build_category_label_option_previews(
                    category_option_to_label=category_option_to_label,
                    category_to_installers=category_to_installers,
                    preview_size_percent=category_preview_size_percent,
                ),
                extension="txt",
                multi=True,
                preview_size_percent=category_preview_size_percent,
            )
        else:
            selected_category_options = choose_from_options(
                multi=True,
                msg="Choose installer categoryLabels to browse.",
                options=list(category_option_to_label.keys()),
                header="🏷 EXPLORE INSTALLER CATEGORIES",
                tv=True,
            )

        if selected_category_options is None or len(selected_category_options) == 0:
            console.print(Panel("❓ Selection cancelled. Nothing to install.", title="Cancelled", border_style="yellow"))
            return
        selected_category_labels = [category_option_to_label[option] for option in selected_category_options]
    else:
        available_category_labels: dict[str, InstallerCategoryLabel] = {category_label: category_label for category_label in category_to_installers}
        unknown_category_labels = [category_label for category_label in category_labels if category_label not in available_category_labels]
        if unknown_category_labels:
            console.print(f"❌ ERROR: Unknown installer categoryLabels: {unknown_category_labels}")
            console.print("[bold blue]Available categoryLabels:[/bold blue]")
            for option_label in category_option_to_label:
                console.print(f"  {option_label}")
            raise typer.Exit(1)
        selected_category_labels = [available_category_labels[category_label] for category_label in category_labels]

    selected_installers = _dedupe_installers(
        [
            installer_data
            for category_label in selected_category_labels
            for installer_data in category_to_installers[category_label]
        ]
    )
    installer_option_to_data = _build_installer_option_to_data(selected_installers)

    selected_installer_options: list[str] | None
    if check_tool_exists("tv"):
        installer_preview_size_percent = 55.0
        selected_installer_options = choose_from_dict_with_preview(
            options_to_preview_mapping={
                option_label: render_installer_preview(installer_data=installer_data, preview_size_percent=installer_preview_size_percent)
                for option_label, installer_data in installer_option_to_data.items()
            },
            extension="txt",
            multi=True,
            preview_size_percent=installer_preview_size_percent,
        )
    else:
        selected_installer_options = choose_from_options(
            multi=True,
            msg=f"Choose installers from categoryLabels: {', '.join(selected_category_labels)}",
            options=list(installer_option_to_data.keys()),
            header="🚀 CHOOSE INSTALLERS",
            tv=True,
        )

    if selected_installer_options is None or len(selected_installer_options) == 0:
        console.print(Panel("❓ Selection cancelled. Nothing to install.", title="Cancelled", border_style="yellow"))
        return

    installation_results: list[InstallationResult] = []
    for selected_installer_option in selected_installer_options:
        installer_data = installer_option_to_data[selected_installer_option]
        installation_results.append(Installer(installer_data).install_robust(install_request=install_request))

    if installation_results:
        render_installation_summary(results=installation_results, console=console, title="📊 Installation Summary")
