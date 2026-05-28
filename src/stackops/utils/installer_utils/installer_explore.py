"""Category-label explorer for `devops install --explore`."""

import json
from typing import Any, Literal, TypedDict

import typer

from stackops.utils.schemas.installer.installer_types import InstallRequest, InstallationResult, InstallerData


class CategoryLabelDefinition(TypedDict):
    label: str
    description: str


class CategoryLabelAppPreview(TypedDict):
    appName: str
    doc: str
    repoURL: str
    categoryLabels: list[str]


class CategoryLabelPreview(TypedDict):
    type: Literal["category_label"]
    categoryLabel: str
    label: str
    description: str
    installerCount: int
    installers: list[CategoryLabelAppPreview]


def _render_preview_json(value: object) -> str:
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


def _load_category_label_definitions() -> dict[str, CategoryLabelDefinition]:
    import stackops.utils.schemas.installer as installer_schema_assets
    from stackops.utils.files.read import read_json
    from stackops.utils.path_reference import get_path_reference_path

    schema_path = get_path_reference_path(
        module=installer_schema_assets,
        path_reference=installer_schema_assets.INSTALLER_TYPE_SCHEMA_PATH_REFERENCE,
    )
    schema_raw: dict[str, Any] = read_json(schema_path)
    definitions_raw = schema_raw.get("x-categoryLabelDefinitions")
    if not isinstance(definitions_raw, dict):
        return {}

    definitions: dict[str, CategoryLabelDefinition] = {}
    for category_label, metadata in definitions_raw.items():
        if not isinstance(category_label, str) or not isinstance(metadata, dict):
            continue
        label_raw = metadata.get("label")
        description_raw = metadata.get("description")
        definitions[category_label] = CategoryLabelDefinition(
            label=label_raw if isinstance(label_raw, str) else category_label,
            description=description_raw if isinstance(description_raw, str) else "",
        )
    return definitions


def _group_installers_by_category_label(installers: list[InstallerData]) -> dict[str, list[InstallerData]]:
    category_to_installers: dict[str, list[InstallerData]] = {}
    for installer_data in installers:
        for category_label in installer_data["categoryLabels"]:
            category_to_installers.setdefault(category_label, []).append(installer_data)
    return category_to_installers


def _sorted_category_labels(
    category_to_installers: dict[str, list[InstallerData]],
    category_definitions: dict[str, CategoryLabelDefinition],
) -> list[str]:
    labels_in_definition_order = [category_label for category_label in category_definitions if category_label in category_to_installers]
    unknown_labels = sorted(set(category_to_installers) - set(labels_in_definition_order))
    return labels_in_definition_order + unknown_labels


def _build_category_label_options(
    category_to_installers: dict[str, list[InstallerData]],
    category_definitions: dict[str, CategoryLabelDefinition],
) -> dict[str, str]:
    category_option_to_label: dict[str, str] = {}
    for category_label in _sorted_category_labels(
        category_to_installers=category_to_installers,
        category_definitions=category_definitions,
    ):
        category_metadata = category_definitions.get(category_label)
        label = category_metadata["label"] if category_metadata is not None else category_label
        installer_count = len(category_to_installers[category_label])
        option_label = f"🏷 {category_label:<36} {installer_count:>3} apps  --  {label}"
        category_option_to_label[option_label] = category_label
    return category_option_to_label


def _build_category_label_preview(
    category_label: str,
    installers: list[InstallerData],
    category_definitions: dict[str, CategoryLabelDefinition],
) -> CategoryLabelPreview:
    metadata = category_definitions.get(category_label)
    app_previews = [
        CategoryLabelAppPreview(
            appName=installer_data["appName"],
            doc=installer_data["doc"],
            repoURL=installer_data["repoURL"],
            categoryLabels=list(installer_data["categoryLabels"]),
        )
        for installer_data in sorted(installers, key=lambda installer_data: installer_data["appName"].lower())
    ]
    return CategoryLabelPreview(
        type="category_label",
        categoryLabel=category_label,
        label=metadata["label"] if metadata is not None else category_label,
        description=metadata["description"] if metadata is not None else "",
        installerCount=len(app_previews),
        installers=app_previews,
    )


def _build_category_label_option_previews(
    category_option_to_label: dict[str, str],
    category_to_installers: dict[str, list[InstallerData]],
    category_definitions: dict[str, CategoryLabelDefinition],
) -> dict[str, str]:
    option_previews: dict[str, str] = {}
    for option_label, category_label in category_option_to_label.items():
        option_previews[option_label] = _render_preview_json(
            _build_category_label_preview(
                category_label=category_label,
                installers=category_to_installers[category_label],
                category_definitions=category_definitions,
            )
        )
    return option_previews


def _dedupe_installers(installers: list[InstallerData]) -> list[InstallerData]:
    app_name_to_installer: dict[str, InstallerData] = {}
    for installer_data in installers:
        app_name_to_installer.setdefault(installer_data["appName"].lower(), installer_data)
    return sorted(app_name_to_installer.values(), key=lambda installer_data: installer_data["appName"].lower())


def explore_installers_by_category_labels(install_request: InstallRequest, category_labels: list[str] | None) -> None:
    from rich.console import Console
    from rich.panel import Panel

    from stackops.utils.installer_utils.installer_class import Installer
    from stackops.utils.installer_utils.installer_locator_utils import check_tool_exists
    from stackops.utils.installer_utils.installer_runner import get_installers
    from stackops.utils.installer_utils.installer_summary import render_installation_summary
    from stackops.utils.options import choose_from_options
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name

    console = Console()
    installers = get_installers(os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
    category_definitions = _load_category_label_definitions()
    category_to_installers = _group_installers_by_category_label(installers=installers)
    category_option_to_label = _build_category_label_options(
        category_to_installers=category_to_installers,
        category_definitions=category_definitions,
    )

    if category_labels is None:
        if check_tool_exists("tv"):
            selected_category_options = choose_from_dict_with_preview(
                options_to_preview_mapping=_build_category_label_option_previews(
                    category_option_to_label=category_option_to_label,
                    category_to_installers=category_to_installers,
                    category_definitions=category_definitions,
                ),
                extension="json",
                multi=True,
                preview_size_percent=60.0,
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
        unknown_category_labels = [category_label for category_label in category_labels if category_label not in category_to_installers]
        if unknown_category_labels:
            console.print(f"❌ ERROR: Unknown installer categoryLabels: {unknown_category_labels}")
            console.print("[bold blue]Available categoryLabels:[/bold blue]")
            for option_label in category_option_to_label:
                console.print(f"  {option_label}")
            raise typer.Exit(1)
        selected_category_labels = category_labels

    selected_installers = _dedupe_installers(
        [
            installer_data
            for category_label in selected_category_labels
            for installer_data in category_to_installers[category_label]
        ]
    )
    installer_option_to_data = _build_installer_option_to_data(selected_installers)

    if check_tool_exists("tv"):
        selected_installer_options = choose_from_dict_with_preview(
            options_to_preview_mapping={
                option_label: _render_preview_json(installer_data)
                for option_label, installer_data in installer_option_to_data.items()
            },
            extension="json",
            multi=True,
            preview_size_percent=55.0,
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
