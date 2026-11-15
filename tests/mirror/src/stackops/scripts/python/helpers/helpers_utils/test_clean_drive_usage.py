import os
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_utils.clean_drive_usage import combine_usages, measure_path, parse_size, reclaimable_bytes


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("47.35GB", 47_350_000_000),
        ("724MB", 724_000_000),
        ("4.1kB", 4_100),
        ("0B", 0),
        ("3.9G", round(3.9 * 1024**3)),
        ("512.0M", 512 * 1024**2),
        ("1.5GiB", round(1.5 * 1024**3)),
        ("2.5 MB", 2_500_000),
    ],
)
def test_parse_size_reads_docker_systemd_and_bleachbit_units(text: str, expected: int) -> None:
    assert parse_size(text) == expected


def test_parse_size_rejects_unknown_text() -> None:
    with pytest.raises(ValueError):
        parse_size("about a gig")


def test_hardlinked_files_count_only_when_every_link_is_measured(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    venv = tmp_path / "venv"
    cache.mkdir()
    venv.mkdir()
    (cache / "shared.so").write_bytes(os.urandom(64_000))
    os.link(cache / "shared.so", venv / "shared.so")
    (cache / "own.whl").write_bytes(os.urandom(32_000))
    cache_usage = measure_path(cache)
    venv_usage = measure_path(venv)
    shared_size = next(iter(cache_usage.shared.values())).size
    assert reclaimable_bytes(cache_usage) == cache_usage.exclusive
    assert reclaimable_bytes(combine_usages([cache_usage, venv_usage])) == cache_usage.exclusive + venv_usage.exclusive + shared_size


def test_measure_path_of_missing_path_is_empty(tmp_path: Path) -> None:
    usage = measure_path(tmp_path / "missing")
    assert reclaimable_bytes(usage) == 0
    assert not usage.denied
