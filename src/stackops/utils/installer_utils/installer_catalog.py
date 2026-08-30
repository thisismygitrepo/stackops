import json
from pathlib import Path
from typing import cast, get_args

import stackops.utils.schemas.installer as installer_schema_assets
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import (
    INSTALLER_DATA_SOURCE_MAP,
    ArchitectureInstallerPattern,
    InstallerData,
    InstallerDataFiles,
    InstallerDataSource,
    InstallerCategoryLabel,
    InstallerFileNamePatterns,
    LinuxInstallerPattern,
    LinuxPackageManagerInstallerPattern,
)
from stackops.utils.source_of_truth import DOTFILES_USER_INSTALLER_DATA_PATH


LIBRARY_INSTALLER_DATA_PATH = get_path_reference_path(
    module=installer_schema_assets,
    path_reference=installer_schema_assets.INSTALLER_DATA_PATH_REFERENCE,
)
USER_INSTALLER_DATA_PATH = DOTFILES_USER_INSTALLER_DATA_PATH


class InstallerDataFileError(ValueError):
    pass


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise InstallerDataFileError(f"{context} must be an object with string keys")
    return cast(dict[str, object], value)


def _require_exact_keys(mapping: dict[str, object], required: set[str], optional: set[str], context: str) -> None:
    missing_keys = sorted(required - set(mapping))
    if missing_keys:
        raise InstallerDataFileError(f"Missing {context} keys: {', '.join(missing_keys)}")
    unexpected_keys = sorted(set(mapping) - required - optional)
    if unexpected_keys:
        raise InstallerDataFileError(f"Unexpected {context} keys: {', '.join(unexpected_keys)}")


def _require_non_empty_string(mapping: dict[str, object], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise InstallerDataFileError(f"{context}.{key} must be a non-empty string")
    return value


def _require_installer_pattern(value: object, context: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise InstallerDataFileError(f"{context} must be a string or null")


def _normalize_linux_pattern(value: object, context: str) -> LinuxInstallerPattern:
    if value is None or isinstance(value, str):
        return value
    mapping = _require_mapping(value=value, context=context)
    package_manager_keys = {"apk", "apt", "dnf", "pacman"}
    _require_exact_keys(mapping=mapping, required=package_manager_keys, optional=set(), context=context)
    return LinuxPackageManagerInstallerPattern(
        apk=_require_installer_pattern(mapping["apk"], f"{context}.apk"),
        apt=_require_installer_pattern(mapping["apt"], f"{context}.apt"),
        dnf=_require_installer_pattern(mapping["dnf"], f"{context}.dnf"),
        pacman=_require_installer_pattern(mapping["pacman"], f"{context}.pacman"),
    )


def _normalize_architecture_pattern(value: object, context: str) -> ArchitectureInstallerPattern:
    mapping = _require_mapping(value=value, context=context)
    _require_exact_keys(mapping=mapping, required={"windows", "linux", "darwin"}, optional=set(), context=context)
    return ArchitectureInstallerPattern(
        windows=_require_installer_pattern(mapping["windows"], f"{context}.windows"),
        linux=_normalize_linux_pattern(mapping["linux"], f"{context}.linux"),
        darwin=_require_installer_pattern(mapping["darwin"], f"{context}.darwin"),
    )


def _normalize_file_name_patterns(value: object, context: str) -> InstallerFileNamePatterns:
    mapping = _require_mapping(value=value, context=context)
    _require_exact_keys(mapping=mapping, required={"amd64", "arm64"}, optional=set(), context=context)
    return InstallerFileNamePatterns(
        amd64=_normalize_architecture_pattern(mapping["amd64"], f"{context}.amd64"),
        arm64=_normalize_architecture_pattern(mapping["arm64"], f"{context}.arm64"),
    )


def _normalize_category_labels(value: object, context: str) -> list[InstallerCategoryLabel]:
    if not isinstance(value, list) or len(value) == 0:
        raise InstallerDataFileError(f"{context} must be a non-empty list")
    valid_labels = frozenset(cast(tuple[str, ...], get_args(InstallerCategoryLabel)))
    normalized_labels: list[InstallerCategoryLabel] = []
    for label in value:
        if not isinstance(label, str) or label not in valid_labels:
            raise InstallerDataFileError(f"Invalid {context} value: {label!r}")
        normalized_label = cast(InstallerCategoryLabel, label)
        if normalized_label in normalized_labels:
            raise InstallerDataFileError(f"Duplicate {context} value: {label}")
        normalized_labels.append(normalized_label)
    return normalized_labels


def _normalize_installer_data(value: object, index: int, path: Path) -> InstallerData:
    context = f"{path}.installers[{index}]"
    mapping = _require_mapping(value=value, context=context)
    _require_exact_keys(
        mapping=mapping,
        required={"appName", "license", "repoURL", "doc", "categoryLabels", "fileNamePattern"},
        optional={"lastCommitDate", "lastCommitDateCheckDate"},
        context=context,
    )
    installer = InstallerData(
        appName=_require_non_empty_string(mapping=mapping, key="appName", context=context),
        license=_require_non_empty_string(mapping=mapping, key="license", context=context),
        repoURL=_require_non_empty_string(mapping=mapping, key="repoURL", context=context),
        doc=_require_non_empty_string(mapping=mapping, key="doc", context=context),
        categoryLabels=_normalize_category_labels(mapping["categoryLabels"], f"{context}.categoryLabels"),
        fileNamePattern=_normalize_file_name_patterns(mapping["fileNamePattern"], f"{context}.fileNamePattern"),
    )
    if "lastCommitDate" in mapping:
        installer["lastCommitDate"] = _require_non_empty_string(mapping=mapping, key="lastCommitDate", context=context)
    if "lastCommitDateCheckDate" in mapping:
        installer["lastCommitDateCheckDate"] = _require_non_empty_string(
            mapping=mapping,
            key="lastCommitDateCheckDate",
            context=context,
        )
    return installer


def load_installer_data_file(path: Path) -> InstallerDataFiles:
    if not path.exists():
        raise InstallerDataFileError(f"Installer data file does not exist: {path}")
    if not path.is_file():
        raise InstallerDataFileError(f"Installer data path is not a file: {path}")
    try:
        payload_value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallerDataFileError(f"Could not load installer data file {path}: {exc}") from exc
    payload = _require_mapping(value=payload_value, context=f"Installer data root {path}")
    _require_exact_keys(mapping=payload, required={"version", "installers"}, optional={"$schema"}, context=f"installer data {path}")
    version = payload.get("version")
    if not isinstance(version, str) or version.strip() == "":
        raise InstallerDataFileError(f"Installer data version must be a non-empty string: {path}")
    installer_values = payload.get("installers")
    if not isinstance(installer_values, list):
        raise InstallerDataFileError(f"Installer data 'installers' must be a list: {path}")

    installers = [
        _normalize_installer_data(value=installer_value, index=index, path=path)
        for index, installer_value in enumerate(installer_values)
    ]

    catalog: InstallerDataFiles = {"version": version, "installers": installers}
    schema_reference = payload.get("$schema")
    if schema_reference is not None:
        if not isinstance(schema_reference, str):
            raise InstallerDataFileError(f"Installer data '$schema' must be a string: {path}")
        catalog["$schema"] = schema_reference
    return catalog


def _index_installers(installers: list[InstallerData], path: Path) -> dict[str, InstallerData]:
    indexed: dict[str, InstallerData] = {}
    for installer in installers:
        normalized_app_name = installer["appName"].casefold()
        if normalized_app_name in indexed:
            raise InstallerDataFileError(f"Duplicate installer appName in {path}: {installer['appName']}")
        indexed[normalized_app_name] = installer
    return indexed


def read_installer_data(source: InstallerDataSource) -> list[InstallerData]:
    normalized_source = INSTALLER_DATA_SOURCE_MAP[source]
    match normalized_source:
        case "library":
            library_catalog = load_installer_data_file(path=LIBRARY_INSTALLER_DATA_PATH)
            return list(_index_installers(library_catalog["installers"], LIBRARY_INSTALLER_DATA_PATH).values())
        case "user":
            user_catalog = load_installer_data_file(path=USER_INSTALLER_DATA_PATH)
            return list(_index_installers(user_catalog["installers"], USER_INSTALLER_DATA_PATH).values())
        case "all":
            library_catalog = load_installer_data_file(path=LIBRARY_INSTALLER_DATA_PATH)
            merged_installers = _index_installers(library_catalog["installers"], LIBRARY_INSTALLER_DATA_PATH)
            if not USER_INSTALLER_DATA_PATH.exists():
                return list(merged_installers.values())
            user_catalog = load_installer_data_file(path=USER_INSTALLER_DATA_PATH)
            merged_installers.update(_index_installers(user_catalog["installers"], USER_INSTALLER_DATA_PATH))
            return list(merged_installers.values())
