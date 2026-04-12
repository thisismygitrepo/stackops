from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_cloud import helpers2
from machineconfig.utils.ve import CLOUD


def _cloud(
    *,
    cloud: str,
    root: str,
    rel2home: bool,
    pwd: str | None,
    key: str | None,
    encrypt: bool,
    os_specific: bool,
    zip_: bool,
    share: bool,
    overwrite: bool,
) -> CLOUD:
    return {
        "cloud": cloud,
        "root": root,
        "rel2home": rel2home,
        "pwd": pwd,
        "key": key,
        "encrypt": encrypt,
        "os_specific": os_specific,
        "zip": zip_,
        "share": share,
        "overwrite": overwrite,
    }


def test_merge_cloud_config_overrides_only_non_default_fields() -> None:
    base = _cloud(
        cloud="base-cloud",
        root="base-root",
        rel2home=False,
        pwd="base-pwd",
        key="base-key",
        encrypt=False,
        os_specific=False,
        zip_=False,
        share=False,
        overwrite=False,
    )
    defaults = _cloud(
        cloud="", root="default-root", rel2home=False, pwd=None, key=None, encrypt=False, os_specific=False, zip_=False, share=False, overwrite=False
    )
    explicit = _cloud(
        cloud="",
        root="default-root",
        rel2home=False,
        pwd=None,
        key="explicit-key",
        encrypt=False,
        os_specific=False,
        zip_=False,
        share=False,
        overwrite=True,
    )

    assert helpers2.merge_cloud_config(cloud_config_base=base, cloud_config_explicit=explicit, cloud_config_defaults=defaults) == _cloud(
        cloud="base-cloud",
        root="base-root",
        rel2home=False,
        pwd="base-pwd",
        key="explicit-key",
        encrypt=False,
        os_specific=False,
        zip_=False,
        share=False,
        overwrite=True,
    )


def test_parse_cloud_source_target_uses_default_cloud_for_implicit_remote_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    local_target = tmp_path.joinpath("notes")

    def fake_my_abs(path: str) -> Path:
        return Path(path)

    def fake_find_cloud_config(path: Path) -> CLOUD | None:
        _ = path
        return None

    def fake_read_ini(path: Path) -> dict[str, dict[str, str]]:
        _ = path
        return {"general": {"rclone_config_name": "default-remote"}}

    def fake_console_print(*objects: object, **kwargs: object) -> None:
        _ = objects, kwargs

    def fake_pprint(value: object, title: str) -> None:
        _ = value, title

    monkeypatch.setattr(helpers2, "my_abs", fake_my_abs)
    monkeypatch.setattr(helpers2, "find_cloud_config", fake_find_cloud_config)
    monkeypatch.setattr(helpers2, "read_ini", fake_read_ini)
    monkeypatch.setattr(helpers2.console, "print", fake_console_print)
    monkeypatch.setattr(helpers2, "pprint", fake_pprint)

    cloud, source, target = helpers2.parse_cloud_source_target(
        cloud_config_explicit=_cloud(
            cloud="", root="root", rel2home=False, pwd=None, key=None, encrypt=False, os_specific=False, zip_=False, share=False, overwrite=False
        ),
        cloud_config_defaults=_cloud(
            cloud="", root="root", rel2home=False, pwd=None, key=None, encrypt=False, os_specific=False, zip_=False, share=False, overwrite=False
        ),
        cloud_config_name=None,
        source=":notes",
        target=str(local_target),
    )

    assert (cloud, source, target) == ("default-remote", "default-remote:notes", str(local_target))


def test_parse_cloud_source_target_infers_remote_target_and_appends_zip_and_gpg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_path = tmp_path.joinpath("report.txt")

    def fake_my_abs(path: str) -> Path:
        return Path(path)

    def fake_get_remote_path(local_path: Path, os_specific: bool, root: str, rel2home: bool, strict: bool) -> Path:
        assert local_path == source_path
        assert os_specific is False
        assert root == "archive-root"
        assert rel2home is False
        assert strict is False
        return Path("archive/report.txt")

    def fake_console_print(*objects: object, **kwargs: object) -> None:
        _ = objects, kwargs

    def fake_pprint(value: object, title: str) -> None:
        _ = value, title

    monkeypatch.setattr(helpers2, "my_abs", fake_my_abs)
    monkeypatch.setattr(helpers2, "get_remote_path", fake_get_remote_path)
    monkeypatch.setattr(helpers2.console, "print", fake_console_print)
    monkeypatch.setattr(helpers2, "pprint", fake_pprint)

    cloud, source, target = helpers2.parse_cloud_source_target(
        cloud_config_explicit=_cloud(
            cloud="",
            root="archive-root",
            rel2home=False,
            pwd=None,
            key=None,
            encrypt=True,
            os_specific=False,
            zip_=True,
            share=False,
            overwrite=False,
        ),
        cloud_config_defaults=_cloud(
            cloud="",
            root="archive-root",
            rel2home=False,
            pwd=None,
            key=None,
            encrypt=False,
            os_specific=False,
            zip_=False,
            share=False,
            overwrite=False,
        ),
        cloud_config_name=None,
        source=str(source_path),
        target="backup:^",
    )

    assert (cloud, source, target) == ("backup", str(source_path), "backup:archive/report.txt.zip.gpg")


def test_parse_cloud_source_target_rejects_two_local_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_console_print(*objects: object, **kwargs: object) -> None:
        _ = objects, kwargs

    monkeypatch.setattr(helpers2.console, "print", fake_console_print)

    with pytest.raises(ValueError, match="Either source or target must be a remote path"):
        helpers2.parse_cloud_source_target(
            cloud_config_explicit=_cloud(
                cloud="", root="root", rel2home=False, pwd=None, key=None, encrypt=False, os_specific=False, zip_=False, share=False, overwrite=False
            ),
            cloud_config_defaults=_cloud(
                cloud="", root="root", rel2home=False, pwd=None, key=None, encrypt=False, os_specific=False, zip_=False, share=False, overwrite=False
            ),
            cloud_config_name=None,
            source="local-left.txt",
            target="local-right.txt",
        )
