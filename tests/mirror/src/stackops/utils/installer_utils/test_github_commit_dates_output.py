from pathlib import Path

import pytest

from stackops.utils.installer_utils.github_commit_dates_output import TextOutput, commit_text_outputs


def test_commit_text_outputs_stages_every_file_before_replacing_targets(tmp_path: Path) -> None:
    existing_path = tmp_path.joinpath("existing.txt")
    existing_path.write_text("original\n", encoding="utf-8")
    blocked_parent = tmp_path.joinpath("not-a-directory")
    blocked_parent.write_text("blocking file\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        commit_text_outputs(
            outputs=(
                TextOutput(path=existing_path, content="replacement\n"),
                TextOutput(path=blocked_parent.joinpath("report.csv"), content="report\n"),
            )
        )

    assert existing_path.read_text(encoding="utf-8") == "original\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["existing.txt", "not-a-directory"]
