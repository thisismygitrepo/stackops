import stackops
from pathlib import Path

LIBRARY_ROOT = Path(stackops.__file__).resolve().parent
REPO_ROOT = LIBRARY_ROOT.parent.parent
DOTFILES_ROOT = Path.home().joinpath("dotfiles")
DOTFILES_STACKOPS_ROOT = DOTFILES_ROOT.joinpath("stackops")
