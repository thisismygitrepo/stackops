from inspect import Parameter, signature
from pathlib import Path
from typing import Protocol, cast

from stackops.utils.schemas.installer.installer_types import InstallerData


INSTALLER_PYTHON_SCRIPT_MAIN_SIGNATURE = """main(installer_data: InstallerData, version: str | None, update: bool)"""


class InstallerPythonScriptMain(Protocol):
    def __call__(
        self,
        installer_data: InstallerData,
        version: str | None,
        update: bool,
    ) -> object: ...


def load_installer_python_script_main(
    module_globals: dict[str, object],
    installer_path: Path,
) -> InstallerPythonScriptMain:
    main_candidate = module_globals.get("main")
    if main_candidate is None:
        raise TypeError(
            f"""{installer_path} must define {INSTALLER_PYTHON_SCRIPT_MAIN_SIGNATURE}"""
        )
    if not callable(main_candidate):
        raise TypeError(
            f"""{installer_path} must export a callable {INSTALLER_PYTHON_SCRIPT_MAIN_SIGNATURE}"""
        )
    if not _matches_installer_python_script_main_signature(main_candidate):
        raise TypeError(
            f"""{installer_path} must define {INSTALLER_PYTHON_SCRIPT_MAIN_SIGNATURE}; any extra parameters must be optional"""
        )
    return cast(InstallerPythonScriptMain, main_candidate)


def _matches_installer_python_script_main_signature(main_candidate: object) -> bool:
    if not callable(main_candidate):
        return False
    try:
        parameters = tuple(signature(main_candidate).parameters.values())
    except (TypeError, ValueError):
        return False
    if len(parameters) < 3:
        return False

    expected_names = ("installer_data", "version", "update")
    disallowed_kinds = {
        Parameter.POSITIONAL_ONLY,
        Parameter.VAR_POSITIONAL,
        Parameter.VAR_KEYWORD,
    }
    for expected_name, parameter in zip(expected_names, parameters[:3], strict=True):
        if parameter.name != expected_name:
            return False
        if parameter.kind in disallowed_kinds:
            return False

    for parameter in parameters[3:]:
        if parameter.kind in {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD}:
            continue
        if parameter.default is Parameter.empty:
            return False
    return True
