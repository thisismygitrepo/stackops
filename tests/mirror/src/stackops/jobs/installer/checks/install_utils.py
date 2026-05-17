from stackops.jobs.installer.checks import install_utils


def test_download_safe_apps_returns_false_when_some_installs_fail(monkeypatch) -> None:
    monkeypatch.setattr(
        install_utils,
        "load_app_metadata_report",
        lambda: [
            {"app_name": "demo-a", "app_url": "https://example.com/a"},
            {"app_name": "demo-b", "app_url": "https://example.com/b"},
        ],
    )

    installed_urls: list[str] = []

    def fake_install_cli_app(app_url: str) -> bool:
        installed_urls.append(app_url)
        return app_url.endswith("/a")

    monkeypatch.setattr(install_utils, "install_cli_app", fake_install_cli_app)

    result = install_utils.download_safe_apps("essentials")

    assert result is False
    assert installed_urls == ["https://example.com/a", "https://example.com/b"]


def test_download_safe_apps_returns_true_when_all_requested_installs_succeed(monkeypatch) -> None:
    monkeypatch.setattr(
        install_utils,
        "load_app_metadata_report",
        lambda: [
            {"app_name": "demo-a", "app_url": "https://example.com/a"},
            {"app_name": "demo-b", "app_url": "https://example.com/b"},
        ],
    )

    installed_urls: list[str] = []

    def fake_install_cli_app(app_url: str) -> bool:
        installed_urls.append(app_url)
        return True

    monkeypatch.setattr(install_utils, "install_cli_app", fake_install_cli_app)

    result = install_utils.download_safe_apps("demo-b")

    assert result is True
    assert installed_urls == ["https://example.com/b"]
