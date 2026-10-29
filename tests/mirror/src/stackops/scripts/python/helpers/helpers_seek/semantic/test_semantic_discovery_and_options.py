import json
import shutil
from pathlib import Path
from typing import cast, get_args

import pytest

import stackops.utils.schemas.installer as installer_schema_assets
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_grepai import find_grepai_project_root, search_grepai
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_names import SemanticBackend
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_qmd import has_qmd_local_index
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_semtools import list_text_files
from stackops.scripts.python.helpers.helpers_seek.semantic.run_semantic_search import required_tools, run_semantic_search
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import SemanticFailure
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import InstallerData


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep is required")
def test_semtools_file_discovery_skips_binary_and_empty_files_and_honours_extension(tmp_path: Path) -> None:
    tmp_path.joinpath("module.py").write_text("print('hello')\n", encoding="utf-8")
    tmp_path.joinpath("notes.md").write_text("# notes\n", encoding="utf-8")
    tmp_path.joinpath("empty.py").write_text("", encoding="utf-8")
    tmp_path.joinpath("blob.bin").write_bytes(b"\x00\xff\xfe\x00binary\x00")

    all_files = list_text_files(root=tmp_path, extension=None)
    python_files = list_text_files(root=tmp_path, extension=".py")

    assert isinstance(all_files, list) and isinstance(python_files, list)
    assert sorted(file.name for file in all_files) == ["module.py", "notes.md"]
    assert [file.name for file in python_files] == ["module.py"]


def test_semtools_file_root_is_searched_as_given(tmp_path: Path) -> None:
    single_file = tmp_path.joinpath("only.py")
    single_file.write_text("x = 1\n", encoding="utf-8")

    assert list_text_files(root=single_file, extension=None) == [single_file]


def test_ancestor_index_markers_are_found_from_nested_directories(tmp_path: Path) -> None:
    nested = tmp_path.joinpath("a", "b")
    nested.mkdir(parents=True)

    assert find_grepai_project_root(root=nested) is None
    assert not has_qmd_local_index(root=nested)

    tmp_path.joinpath(".grepai").mkdir()
    tmp_path.joinpath(".grepai", "config.yaml").write_text("version: 1\n", encoding="utf-8")
    tmp_path.joinpath(".qmd").mkdir()
    tmp_path.joinpath(".qmd", "index.yml").write_text("collections: {}\n", encoding="utf-8")

    assert find_grepai_project_root(root=nested) == tmp_path
    assert has_qmd_local_index(root=nested)


def test_index_backends_reject_a_single_file_root_before_running_anything(tmp_path: Path) -> None:
    single_file = tmp_path.joinpath("only.py")
    single_file.write_text("x = 1\n", encoding="utf-8")

    for backend in ("ck", "grepai", "qmd"):
        failure = run_semantic_search(path=str(single_file), query="x", extension=None, max_files=0, backend=backend, edit=False)
        assert isinstance(failure, SemanticFailure)
        assert (failure.backend, failure.stage) == (backend, "options")


def test_grepai_rejects_extension_filter_before_running_anything(tmp_path: Path) -> None:
    failure = search_grepai(root=tmp_path, query="x", extension=".py", top_k=1)

    assert isinstance(failure, SemanticFailure)
    assert (failure.backend, failure.stage) == ("grepai", "options")


def test_every_tool_a_backend_requires_has_an_installer_in_the_bundled_catalog() -> None:
    catalog_path = get_path_reference_path(module=installer_schema_assets, path_reference=installer_schema_assets.INSTALLER_DATA_PATH_REFERENCE)
    catalog = cast(dict[str, list[InstallerData]], json.loads(catalog_path.read_text(encoding="utf-8")))
    catalog_app_names = {installer["appName"] for installer in catalog["installers"]}

    for backend in get_args(SemanticBackend):
        assert set(required_tools(backend=backend)) <= catalog_app_names
