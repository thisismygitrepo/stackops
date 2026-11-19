from typing import TypedDict


class SoftwareApp(TypedDict):
    name: str
    summary: str
    license: str
    homepage: str
    categories: list[str]
    installed: bool
    updated_at: str


class SoftwareCategory(TypedDict):
    label: str
    title: str
    description: str


class SoftwareCatalog(TypedDict):
    apps: list[SoftwareApp]
    categories: list[SoftwareCategory]


def load_software_catalog() -> SoftwareCatalog:
    from stackops.utils.cli_utils.command_lookup import check_tool_exists
    from stackops.utils.installer_utils.installer_class import Installer
    from stackops.utils.installer_utils.installer_runner import get_installers_from_source
    from stackops.utils.schemas.installer.installer_categories import installer_category_definition
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name

    installers = get_installers_from_source(source="all", user_path=None, os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
    apps: list[SoftwareApp] = [
        {
            "name": installer["appName"],
            "summary": installer["doc"],
            "license": installer["license"],
            "homepage": installer["repoURL"] if installer["repoURL"].startswith("http") else "",
            "categories": list(installer["categoryLabels"]),
            "installed": check_tool_exists(tool_name=Installer(installer).get_exe_name()),
            "updated_at": installer.get("lastCommitDate") or "",
        }
        for installer in sorted(installers, key=lambda item: item["appName"].casefold())
    ]
    definitions = {label: installer_category_definition(label=label) for installer in installers for label in installer["categoryLabels"]}
    categories: list[SoftwareCategory] = [
        {"label": label, "title": definition["title"], "description": definition["description"]} for label, definition in definitions.items()
    ]
    return {"apps": apps, "categories": sorted(categories, key=lambda category: category["title"])}
