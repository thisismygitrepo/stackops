from typing import TypedDict


class SoftwareApp(TypedDict):
    name: str
    summary: str
    license: str
    homepage: str
    categories: list[str]
    installed: bool
    updated_at: str
    mine: bool
    repository: str


class SoftwareCategory(TypedDict):
    label: str
    title: str
    description: str


class SoftwareBundle(TypedDict):
    name: str
    apps: list[str]


class SoftwareCatalog(TypedDict):
    apps: list[SoftwareApp]
    categories: list[SoftwareCategory]
    bundles: list[SoftwareBundle]


class CatalogProblem(TypedDict):
    error: str


def load_software_catalog() -> SoftwareCatalog | CatalogProblem:
    from stackops.scripts.python.helpers.helpers_serve.software_versions import github_release_repository
    from stackops.utils.cli_utils.command_lookup import check_tool_exists
    from stackops.utils.installer_utils.installer_catalog import USER_INSTALLER_DATA_PATH, InstallerDataFileError, read_installer_data
    from stackops.utils.installer_utils.installer_class import Installer
    from stackops.utils.installer_utils.installer_runner import get_installers_from_source
    from stackops.utils.schemas.installer.installer_categories import installer_category_definition
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name
    from stackops.utils.schemas.installer.package_groups import PACKAGE_GROUP2NAMES

    # A design choice: a user catalog that does not load hides the library apps too, as it does on the command line, because no install can run until it is fixed.
    try:
        installers = get_installers_from_source(source="all", user_path=None, os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
        user_installers = read_installer_data(source="user", user_path=None) if USER_INSTALLER_DATA_PATH.exists() else []
    except InstallerDataFileError as error:
        return {"error": str(error)}
    user_names = {installer["appName"].casefold() for installer in user_installers}
    apps: list[SoftwareApp] = [
        {
            "name": installer["appName"],
            "summary": installer["doc"],
            "license": installer["license"],
            "homepage": installer["repoURL"] if installer["repoURL"].startswith("http") else "",
            "categories": list(installer["categoryLabels"]),
            "installed": check_tool_exists(tool_name=Installer(installer).get_exe_name()),
            "updated_at": installer.get("lastCommitDate") or "",
            "mine": installer["appName"].casefold() in user_names,
            "repository": github_release_repository(installer=installer) or "",
        }
        for installer in sorted(installers, key=lambda item: item["appName"].casefold())
    ]
    definitions = {label: installer_category_definition(label=label) for installer in installers for label in installer["categoryLabels"]}
    categories: list[SoftwareCategory] = [
        {"label": label, "title": definition["title"], "description": definition["description"]} for label, definition in definitions.items()
    ]
    shown_names = {app["name"].casefold(): app["name"] for app in apps}
    bundles: list[SoftwareBundle] = [
        {"name": group, "apps": [shown_names[name] for name in dict.fromkeys(name.casefold() for name in group_names) if name in shown_names]}
        for group, group_names in PACKAGE_GROUP2NAMES.items()
    ]
    return {
        "apps": apps,
        "categories": sorted(categories, key=lambda category: category["title"]),
        "bundles": [bundle for bundle in bundles if len(bundle["apps"]) > 0],
    }
