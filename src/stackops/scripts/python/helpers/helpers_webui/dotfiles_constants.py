from typing import Final

# What the export and import commands run, by the name each is found under.
DOTFILES_PROTECT_TOOL: Final[str] = "gpg"
DOTFILES_SHARE_TOOL: Final[str] = "miniserve"
DOTFILES_TRANSFER_TOOL: Final[str] = "cloud"
# Where the export command shares the archive: every interface, on a port fixed in the command, so the page can say the address before the share starts.
DOTFILES_SHARE_HOST: Final[str] = "0.0.0.0"
DOTFILES_SHARE_PORT: Final[int] = 8888
# How many paths of each kind the export leaves out are named on the page; the rest are counted.
DOTFILES_LEFT_OUT_EXAMPLES: Final[int] = 5
# Archives are looked for in the home folder only. That is where the export command leaves one, where a transfer over SSH and a download put
# one, and where the page saves one dropped onto it. Downloads and Desktop are left out: on macOS reading them can raise a permission dialog.
DOTFILES_ARCHIVE_PATTERN: Final[str] = "*.zip.gpg"
DOTFILES_ARCHIVES_SHOWN: Final[int] = 6
DOTFILES_RECEIVED_NAME: Final[str] = "dotfiles.received.{stamp}.zip.gpg"
DOTFILES_RECEIVED_STAMP: Final[str] = "%Y%m%d-%H%M%S"
# Rows of an archive's listing sent to the page. What changes comes first, so only files that stay the same are ever cut.
DOTFILES_LISTING_ROWS: Final[int] = 4000
DOTFILES_HASH_CHUNK_BYTES: Final[int] = 1024 * 1024
# A folder typed into "Add one file" is measured up to this many files: a home folder would otherwise be walked whole on every keystroke.
DOTFILES_MEASURE_FILE_LIMIT: Final[int] = 20000
