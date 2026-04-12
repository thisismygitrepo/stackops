from __future__ import annotations

from pathlib import Path

from machineconfig.scripts.python.helpers.helpers_network.ssh import ssh_cloud_init as target


def _map_posix_path(root_dir: Path, value: str | Path) -> Path:
    raw_path = Path(value)
    if raw_path.is_absolute():
        return root_dir.joinpath(*raw_path.parts[1:])
    return raw_path


def _build_path_class(root_dir: Path) -> type[object]:
    class MappedPath:
        def __new__(cls, value: str | Path) -> Path:
            return _map_posix_path(root_dir=root_dir, value=value)

    return MappedPath


def test_check_cloud_init_overrides_collects_supported_keys(monkeypatch: object, tmp_path: Path) -> None:
    root_dir = tmp_path.joinpath("root")
    conf_dir = root_dir.joinpath("etc", "ssh", "sshd_config.d")
    conf_dir.mkdir(parents=True)
    conf_dir.joinpath("10-base.conf").write_text(
        """
# comment
PasswordAuthentication no
PubkeyAuthentication YES
SomeOtherDirective value
""".strip(),
        encoding="utf-8",
    )
    conf_dir.joinpath("20-extra.conf").write_text(
        """
KbdInteractiveAuthentication No
PermitRootLogin prohibit-password
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(target, "Path", _build_path_class(root_dir=root_dir))

    override_files, auth_overrides = target.check_cloud_init_overrides()

    assert [path.name for path in override_files] == ["10-base.conf", "20-extra.conf"]
    assert auth_overrides["PasswordAuthentication"][1] == "no"
    assert auth_overrides["PubkeyAuthentication"][1] == "yes"
    assert auth_overrides["KbdInteractiveAuthentication"][1] == "no"
    assert auth_overrides["PermitRootLogin"][1] == "prohibit-password"
    assert "SomeOtherDirective" not in auth_overrides


def test_generate_cloud_init_fix_script_only_targets_disabled_auth_methods(tmp_path: Path) -> None:
    password_conf = tmp_path.joinpath("10-password.conf")
    pubkey_conf = tmp_path.joinpath("20-pubkey.conf")
    script = target.generate_cloud_init_fix_script(
        auth_overrides={
            "PasswordAuthentication": (password_conf, "no"),
            "PubkeyAuthentication": (pubkey_conf, "no"),
            "PermitRootLogin": (tmp_path.joinpath("30-root.conf"), "no"),
            "KbdInteractiveAuthentication": (tmp_path.joinpath("40-kbd.conf"), "yes"),
        }
    )

    assert "# Fix PasswordAuthentication in 10-password.conf" in script
    assert f"sudo sed -i 's/^PasswordAuthentication.*no/PasswordAuthentication yes/' {password_conf}" in script
    assert "# Fix PubkeyAuthentication in 20-pubkey.conf" in script
    assert f"sudo sed -i 's/^PubkeyAuthentication.*no/PubkeyAuthentication yes/' {pubkey_conf}" in script
    assert "PermitRootLogin" not in script
    assert "KbdInteractiveAuthentication" not in script
