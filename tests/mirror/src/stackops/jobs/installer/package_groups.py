

from typing import get_args

from stackops.jobs.installer import package_groups


def _duplicates(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return tuple(duplicates)


def test_package_group_keys_match_package_name_literal() -> None:
    literal_keys = set(get_args(package_groups.PACKAGE_NAME))
    dict_keys = set(package_groups.PACKAGE_GROUP2NAMES)

    assert dict_keys == literal_keys


def test_aggregate_groups_keep_expected_order_and_contents() -> None:
    assert package_groups.PACKAGES_DATABASE == [*package_groups.DB_TUIS, *package_groups.DB_CLI, *package_groups.DB_DESKTOP, *package_groups.DB_WEB]
    assert package_groups.PACKAGE_GROUP2NAMES["db-all"] == package_groups.PACKAGES_DATABASE
    assert package_groups.PACKAGE_GROUP2NAMES["termabc"] == [
        *package_groups.PACKAGES_CODE_ANALYSIS,
        *package_groups.PACKAGES_SYSTEM_MONITORS,
        *package_groups.PACKAGES_TERMINAL_SHELL,
        *package_groups.PACKAGES_FILE,
    ]
    assert package_groups.PACKAGE_GROUP2NAMES["dev"] == [
        *package_groups.PACKAGES_TERMINAL_EMULATORS,
        *package_groups.PACKAGES_BROWSERS,
        *package_groups.PACKAGES_CODE_EDITORS,
        *package_groups.PACKAGES_DATABASE,
        *package_groups.PACKAGES_MEDIA,
        *package_groups.PACKAGES_FILE_SHARING,
        *package_groups.PACKAGES_DEV_UTILS,
        *package_groups.PACKAGES_CODE_ANALYSIS,
        *package_groups.PACKAGES_PRODUCTIVITY,
        *package_groups.TERMINAL_EYE_CANDY,
    ]


def test_package_groups_do_not_repeat_values_within_same_group() -> None:
    for group_name, package_names in package_groups.PACKAGE_GROUP2NAMES.items():
        assert package_names
        assert _duplicates(package_names) == (), group_name
