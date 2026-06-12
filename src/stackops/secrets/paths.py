from pathlib import Path

from stackops.paths import DOTFILES_STACKOPS_ROOT

SECRETS_DOFILE: Path = DOTFILES_STACKOPS_ROOT.joinpath("secrets/secrets.json")
