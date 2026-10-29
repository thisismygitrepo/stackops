from collections.abc import Mapping
from pathlib import Path
from typing import Final, cast, get_type_hints

import yaml

import stackops.utils.schemas.installer as installer_schema_assets
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import (
    INSTALLER_CATEGORY_LABELS,
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
from stackops.utils.schemas.yaml_document import yaml_document_text
from stackops.utils.schemas.yaml_schema import yaml_language_server_schema_comment
from stackops.utils.source_of_truth import DOTFILES_USER_INSTALLER_DATA_PATH


LIBRARY_INSTALLER_DATA_PATH = get_path_reference_path(
    module=installer_schema_assets,
    path_reference=installer_schema_assets.INSTALLER_DATA_PATH_REFERENCE,
)
USER_INSTALLER_DATA_PATH = DOTFILES_USER_INSTALLER_DATA_PATH
_INSTALLER_DATA_KEYS: Final[tuple[str, ...]] = tuple(get_type_hints(InstallerData))
_CATEGORY_LABEL_BY_NAME: Final[dict[str, InstallerCategoryLabel]] = {category_label: category_label for category_label in INSTALLER_CATEGORY_LABELS}


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
        raise InstallerDataFileError(
            f"""{context}.{key} must be a non-empty string (quote YAML values that look like dates, numbers or booleans), got {value!r}"""
        )
    return value


def _require_installer_pattern(value: object, context: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise InstallerDataFileError(f"""{context} must be a string or null (quote YAML values that look like dates, numbers or booleans), got {value!r}""")


def _normalize_linux_pattern(value: object, context: str) -> LinuxInstallerPattern:
    if value is None or isinstance(value, str):
        return value
    mapping = _require_mapping(value=value, context=context)
    package_manager_keys = {"apk", "apt", "dnf", "pacman"}
    _require_exact_keys(mapping=mapping, required=package_manager_keys, optional={"omarchy"}, context=context)
    normalized = LinuxPackageManagerInstallerPattern(
        apk=_require_installer_pattern(mapping["apk"], f"{context}.apk"),
        apt=_require_installer_pattern(mapping["apt"], f"{context}.apt"),
        dnf=_require_installer_pattern(mapping["dnf"], f"{context}.dnf"),
        pacman=_require_installer_pattern(mapping["pacman"], f"{context}.pacman"),
    )
    if "omarchy" in mapping:
        normalized["omarchy"] = _require_installer_pattern(mapping["omarchy"], f"{context}.omarchy")
    return normalized


def _normalize_architecture_pattern(value: object, context: str) -> ArchitectureInstallerPattern:
    mapping = _require_mapping(value=value, context=context)
    _require_exact_keys(mapping=mapping, required={"windows", "linux", "darwin"}, optional=set(), context=context)
    return ArchitectureInstallerPattern(
        linux=_normalize_linux_pattern(mapping["linux"], f"{context}.linux"),
        darwin=_require_installer_pattern(mapping["darwin"], f"{context}.darwin"),
        windows=_require_installer_pattern(mapping["windows"], f"{context}.windows"),
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
    normalized_labels: list[InstallerCategoryLabel] = []
    for label in cast(list[object], value):
        category_label = _CATEGORY_LABEL_BY_NAME.get(label) if isinstance(label, str) else None
        if category_label is None:
            raise InstallerDataFileError(f"Invalid {context} value: {label!r}")
        if category_label in normalized_labels:
            raise InstallerDataFileError(f"Duplicate {context} value: {category_label}")
        normalized_labels.append(category_label)
    return normalized_labels


def normalize_installer_data(value: object, context: str) -> InstallerData:
    mapping = _require_mapping(value=value, context=context)
    _require_exact_keys(
        mapping=mapping,
        required={"appName", "license", "repoURL", "doc", "categoryLabels", "fileNamePattern"},
        optional={"lastCommitDate", "lastCommitDateCheckDate", "comment"},
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
    if "comment" in mapping:
        installer["comment"] = _require_non_empty_string(mapping=mapping, key="comment", context=context)
    return installer


def load_installer_data_file(path: Path) -> InstallerDataFiles:
    if path.suffix != LIBRARY_INSTALLER_DATA_PATH.suffix:
        raise InstallerDataFileError(f"""Installer data files must be YAML with the '{LIBRARY_INSTALLER_DATA_PATH.suffix}' suffix: {path}""")
    if not path.exists():
        raise InstallerDataFileError(f"Installer data file does not exist: {path}")
    if not path.is_file():
        raise InstallerDataFileError(f"Installer data path is not a file: {path}")
    try:
        payload_value = cast(object, yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader))
    except (OSError, yaml.YAMLError) as exc:
        raise InstallerDataFileError(f"Could not load installer data file {path}: {exc}") from exc
    payload = _require_mapping(value=payload_value, context=f"Installer data root {path}")
    _require_exact_keys(mapping=payload, required={"version", "installers"}, optional=set(), context=f"installer data {path}")
    version = payload["version"]
    if not isinstance(version, str) or version.strip() == "":
        raise InstallerDataFileError(f"""Installer data 'version' must be a non-empty quoted string, e.g. version: "4", got {version!r}: {path}""")
    installer_values = payload.get("installers")
    if not isinstance(installer_values, list):
        raise InstallerDataFileError(f"Installer data 'installers' must be a list: {path}")

    installers: list[InstallerData] = []
    app_names: set[str] = set()
    for index, installer_value in enumerate(installer_values):
        installer = normalize_installer_data(value=installer_value, context=f"{path}.installers[{index}]")
        normalized_app_name = installer["appName"].casefold()
        if normalized_app_name in app_names:
            raise InstallerDataFileError(f"""Duplicate installer appName in {path}: {installer['appName']}""")
        app_names.add(normalized_app_name)
        installers.append(installer)

    return {"version": version, "installers": installers}


def installer_data_file_text(path: Path, catalog: InstallerDataFiles) -> str:
    installer_documents = [
        {key: cast(Mapping[str, object], installer)[key] for key in _INSTALLER_DATA_KEYS if key in installer} for installer in catalog["installers"]
    ]
    return f"""{yaml_language_server_schema_comment(yaml_path=path)}

{yaml_document_text(document={"version": catalog["version"], "installers": installer_documents})}"""


def read_installer_data(source: InstallerDataSource, user_path: Path | None) -> list[InstallerData]:
    normalized_source = INSTALLER_DATA_SOURCE_MAP[source]
    if user_path is not None and normalized_source == "library":
        raise InstallerDataFileError("--custom-path cannot be combined with --source library.")
    user_catalog_path = USER_INSTALLER_DATA_PATH if user_path is None else user_path.expanduser().absolute()
    match normalized_source:
        case "library":
            library_catalog = load_installer_data_file(path=LIBRARY_INSTALLER_DATA_PATH)
            return library_catalog["installers"]
        case "user":
            user_catalog = load_installer_data_file(path=user_catalog_path)
            return user_catalog["installers"]
        case "all":
            library_catalog = load_installer_data_file(path=LIBRARY_INSTALLER_DATA_PATH)
            merged_installers = {installer["appName"].casefold(): installer for installer in library_catalog["installers"]}
            if user_path is None and not user_catalog_path.exists():
                return list(merged_installers.values())
            user_catalog = load_installer_data_file(path=user_catalog_path)
            merged_installers.update({installer["appName"].casefold(): installer for installer in user_catalog["installers"]})
            return list(merged_installers.values())
