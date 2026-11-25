from typing import Final, Literal

from stackops.utils.managed_files import ManagedFileKind

# Whether the schema a settings file is checked against also lies beside it, where an editor finds it: not there, the same as the one StackOps
# ships, or an older copy.
type SchemaStanding = Literal["missing", "current", "outdated"]
# Where a settings file belongs: to the person, in one fixed place under the home folder, or to the project the page's working folder is part of.
type FileScope = Literal["home", "folder"]

# The kinds a project has a file of. Each has a second file, the person's own, which agents read in every project. `devops config` only
# works on the project's, so that one is what a request means when it names no scope.
FOLDER_FILE_KINDS: Final[frozenset[ManagedFileKind]] = frozenset({"prompts", "mcp"})
# What Python and Finder leave behind in a folder. The Packaged files view leaves these out on both sides: they are no part of what StackOps ships.
ASSET_NOISE_NAMES: Final[frozenset[str]] = frozenset({"__pycache__", ".DS_Store"})
# How many file names of one kind (changed, missing, only on this machine) a folder's row is sent. The counts beside them are always whole.
ASSET_NAMES_SENT: Final[int] = 40
# The one packaged settings file that is filled in as it is copied (`create_helper.copy_assets_to_machine`), and the word that is replaced in it.
ASSET_TEMPLATED_FILE: Final[str] = "marimo/marimo.toml"
ASSET_TEMPLATE_TOKEN: Final[str] = "{STACKOPS_CONFIG_ROOT}"
