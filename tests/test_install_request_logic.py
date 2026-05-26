from stackops.utils.installer_utils.install_request_logic import build_install_target, validate_install_request
from stackops.utils.schemas.installer.installer_types import InstallRequest


def test_script_installers_preserve_version_and_update_request() -> None:
    install_target = build_install_target(
        repo_url="https://github.com/tramhao/termusic",
        installer_value="termusic.py",
    )

    resolution = validate_install_request(
        install_target=install_target,
        install_request=InstallRequest(version="v0.13.2", update=True),
    )

    assert install_target.installer_kind == "script"
    assert resolution.install_request == InstallRequest(version="v0.13.2", update=True)
    assert resolution.warnings == ()
