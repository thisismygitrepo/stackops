from pathlib import Path

import pytest

from stackops.utils import rclone_wrapper


@pytest.mark.parametrize(
    ("share_url", "direct_download_url"),
    [
        (
            "https://drive.google.com/open?id=1AgHG8wkcNaJw2RvRrswUWu9dArJjZw2L",
            "https://drive.google.com/uc?export=download&id=1AgHG8wkcNaJw2RvRrswUWu9dArJjZw2L",
        ),
        (
            "https://drive.google.com/file/d/1AgHG8wkcNaJw2RvRrswUWu9dArJjZw2L/view?usp=sharing",
            "https://drive.google.com/uc?export=download&id=1AgHG8wkcNaJw2RvRrswUWu9dArJjZw2L",
        ),
        ("https://example.com/file.zip", None),
    ],
)
def test_google_drive_direct_download_url(share_url: str, direct_download_url: str | None) -> None:
    assert rclone_wrapper.google_drive_direct_download_url(share_url=share_url) == direct_download_url


def test_to_cloud_prints_share_and_direct_download_urls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    archive_path = tmp_path.joinpath("archive.zip")
    archive_path.write_text("zip-bytes", encoding="utf-8")

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        assert in_path == archive_path.as_posix()
        assert out_path == "gdp:/stackops/archive.zip"
        assert transfers == 10
        assert show_command is True
        assert show_progress is True

    def fake_link(*, target: str, show_command: bool) -> str:
        assert target == "gdp:/stackops/archive.zip"
        assert show_command is True
        return "https://drive.google.com/open?id=test-file-id"

    monkeypatch.setattr(rclone_wrapper.rclone_utils, "copyto", fake_copyto)
    monkeypatch.setattr(rclone_wrapper.rclone_utils, "link", fake_link)

    share_url = rclone_wrapper.to_cloud(
        local_path=archive_path,
        cloud="gdp",
        remote_path=Path("/stackops/archive.zip"),
        share=True,
        verbose=True,
        transfers=10,
    )

    captured_output = capsys.readouterr().out
    assert share_url == "https://drive.google.com/open?id=test-file-id"
    assert "🔗 SHARE URL: https://drive.google.com/open?id=test-file-id" in captured_output
    assert "⬇️ DIRECT DOWNLOAD URL: https://drive.google.com/uc?export=download&id=test-file-id" in captured_output
