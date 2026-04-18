from __future__ import annotations

from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils import path_reference_validation as module


def test_audit_repository_path_references_defaults_to_src_directory(tmp_path: Path) -> None:
    repo_root = tmp_path
    package_dir = repo_root.joinpath("src", "pkg")
    package_dir.mkdir(parents=True)
    package_dir.joinpath("asset.txt").write_text("ok\n", encoding="utf-8")
    package_dir.joinpath("__init__.py").write_text('ASSET_PATH_REFERENCE = "asset.txt"\n', encoding="utf-8")
    repo_root.joinpath("ignored", "__init__.py").parent.mkdir(parents=True)
    repo_root.joinpath("ignored", "__init__.py").write_text('IGNORED_PATH_REFERENCE = "missing.txt"\n', encoding="utf-8")

    audit = module.audit_repository_path_references(repo_path=repo_root, search_root=None)

    assert audit.repo_root == repo_root.resolve()
    assert audit.search_root == repo_root.joinpath("src").resolve()
    assert audit.scanned_init_files == 1
    assert audit.reference_count == 1
    assert audit.resolved_reference_count() == 1
    assert audit.invalid_references == ()
    assert audit.missing_references == ()


def test_format_path_reference_audit_reports_invalid_and_missing_items(tmp_path: Path) -> None:
    repo_root = tmp_path
    package_dir = repo_root.joinpath("pkg")
    package_dir.mkdir(parents=True)
    package_dir.joinpath("__init__.py").write_text(
        'GOOD_PATH_REFERENCE = "asset.txt"\nBAD_PATH_REFERENCE = Path("dynamic.txt")\nMISSING_PATH_REFERENCE = "missing.txt"\n',
        encoding="utf-8",
    )
    package_dir.joinpath("asset.txt").write_text("ok\n", encoding="utf-8")

    audit = module.audit_repository_path_references(repo_path=repo_root, search_root=repo_root)
    formatted = module.format_path_reference_audit(audit=audit)

    assert audit.scanned_init_files == 1
    assert audit.reference_count == 2
    assert audit.invalid_count() == 1
    assert audit.missing_count() == 1
    assert audit.resolved_reference_count() == 1
    assert "Invalid _PATH_REFERENCE definitions" in formatted
    assert "BAD_PATH_REFERENCE" in formatted
    assert "Missing _PATH_REFERENCE targets" in formatted
    assert "MISSING_PATH_REFERENCE" in formatted