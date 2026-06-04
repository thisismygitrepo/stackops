import tarfile
from pathlib import Path

from stackops.utils.path_compression import decompress_path


def test_decompress_path_extracts_tgz_archive(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    payload = source_dir / "himalaya"
    payload.write_text("binary placeholder", encoding="utf-8")

    archive_path = tmp_path / "himalaya.x86_64-linux.tgz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(payload, arcname=payload.name)

    extracted_path = decompress_path(
        archive_path,
        folder=None,
        name=None,
        path=None,
        inplace=False,
        orig=False,
        verbose=False,
    )

    assert extracted_path.is_dir()
    assert extracted_path.joinpath("himalaya").read_text(encoding="utf-8") == "binary placeholder"
