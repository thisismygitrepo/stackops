

from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_utils.path_reference_validation import audit_repository_path_references, format_path_reference_audit


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_all_path_reference_targets_exist(capsys: pytest.CaptureFixture[str]) -> None:
    audit = audit_repository_path_references(repo_path=REPO_ROOT, search_root=None)
    with capsys.disabled():
        print(f"Picked up {audit.reference_count} _PATH_REFERENCE variables.")
    if audit.has_failures():
        pytest.fail(format_path_reference_audit(audit=audit))
