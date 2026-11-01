import shutil
from pathlib import Path
from typing import get_args

import pytest

from stackops.scripts.python.helpers.helpers_seek.semantic.backend_grepai import check_grepai_config_is_local, find_grepai_project_root, search_grepai
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_names import SemanticBackend
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_qmd import has_qmd_local_index
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_semtools import list_text_files
from stackops.scripts.python.helpers.helpers_seek.semantic.run_semantic_search import required_tools, run_semantic_search
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import SemanticFailure
from stackops.utils.installer_utils.installer_catalog import LIBRARY_INSTALLER_DATA_PATH, load_installer_data_file


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


@pytest.mark.parametrize(
    ("provider", "endpoint", "store", "is_local"),
    [
        ("ollama", "http://localhost:11434", "gob", True),
        ("lmstudio", "http://127.0.0.1:1234", "gob", True),
        ("openai", "https://api.openai.com/v1", "gob", False),
        ("ollama", "http://gpu-box.lan:11434", "gob", False),
        ("ollama", "http://localhost:11434", "qdrant", False),
    ],
)
def test_grepai_runs_only_against_a_loopback_embedder_and_local_store(tmp_path: Path, provider: str, endpoint: str, store: str, is_local: bool) -> None:
    tmp_path.joinpath(".grepai").mkdir()
    tmp_path.joinpath(".grepai", "config.yaml").write_text(
        f"""version: 1\nembedder:\n    provider: {provider}\n    model: m\n    endpoint: {endpoint}\nstore:\n    backend: {store}\n""", encoding="utf-8"
    )

    failure = check_grepai_config_is_local(project_root=tmp_path)

    assert (failure is None) == is_local
    if failure is not None:
        assert (failure.backend, failure.stage) == ("grepai", "options")


def test_grepai_refuses_an_inherited_cloud_config_before_indexing(tmp_path: Path) -> None:
    nested = tmp_path.joinpath("notes")
    nested.mkdir()
    tmp_path.joinpath(".grepai").mkdir()
    tmp_path.joinpath(".grepai", "config.yaml").write_text(
        "embedder:\n    provider: openrouter\n    endpoint: https://openrouter.ai/api/v1\nstore:\n    backend: gob\n", encoding="utf-8"
    )

    failure = search_grepai(root=nested, query="x", extension=None, top_k=1)

    assert isinstance(failure, SemanticFailure)
    assert (failure.backend, failure.stage) == ("grepai", "options")


def test_every_tool_a_backend_requires_has_an_installer_in_the_bundled_catalog() -> None:
    catalog = load_installer_data_file(path=LIBRARY_INSTALLER_DATA_PATH)
    catalog_app_names = {installer["appName"] for installer in catalog["installers"]}

    for backend in get_args(SemanticBackend):
        assert set(required_tools(backend=backend)) <= catalog_app_names
