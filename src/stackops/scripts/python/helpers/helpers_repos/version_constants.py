from typing import Literal


VERSIONS_FILE_NAME = "versions.json"
VERSIONS_SCHEMA_VERSION: Literal["2"] = "2"
CHECKOUT_BACKUP_REF_PREFIX = "refs/stackops/version-checkout-backups"
IN_PROGRESS_GIT_MARKERS = ("BISECT_LOG", "CHERRY_PICK_HEAD", "MERGE_HEAD", "REVERT_HEAD", "rebase-apply", "rebase-merge")
