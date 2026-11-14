import platform
from pathlib import Path

import pytest

from stackops.profile import migration_until_2028_01_bash_zsh_hook as migration

CURRENT_HOOK = "source $HOME/.config/stackops/settings/shells/bash_zsh/init.sh"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home_path = tmp_path.joinpath("home")
    home_path.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home_path))
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    return home_path


def test_stale_hook_is_rewritten_in_place_with_backup(home: Path) -> None:
    bashrc = home.joinpath(".bashrc")
    original = """export BEFORE=1
  source $HOME/.config/stackops/settings/shells/bash/init.sh
# source $HOME/.config/stackops/settings/shells/bash/init.sh
source $HOME/.config/stackops/settings/shells/bash/init.sh.bak
export AFTER=1
"""
    bashrc.write_text(original, encoding="utf-8")

    migration.migrate_stale_shell_hooks(config_root=home.joinpath(".config", "stackops"))

    assert bashrc.read_text(encoding="utf-8") == f"""export BEFORE=1
  {CURRENT_HOOK}
# source $HOME/.config/stackops/settings/shells/bash/init.sh
source $HOME/.config/stackops/settings/shells/bash/init.sh.bak
export AFTER=1
"""
    assert home.joinpath(".bashrc.before_stackops_bash_zsh_migration").read_text(encoding="utf-8") == original


def test_stale_hook_beside_current_hook_is_dropped(home: Path) -> None:
    zshrc = home.joinpath(".zshrc")
    zshrc.write_text(f"""{CURRENT_HOOK}\nsource $HOME/.config/stackops/settings/shells/zsh/init.sh\n""", encoding="utf-8")

    migration.migrate_stale_shell_hooks(config_root=home.joinpath(".config", "stackops"))

    assert zshrc.read_text(encoding="utf-8") == f"""{CURRENT_HOOK}\n"""


def test_profiles_without_stale_hooks_are_untouched(home: Path) -> None:
    bashrc = home.joinpath(".bashrc")
    bashrc.write_text(f"""{CURRENT_HOOK}\n""", encoding="utf-8")

    migration.migrate_stale_shell_hooks(config_root=home.joinpath(".config", "stackops"))

    assert bashrc.read_text(encoding="utf-8") == f"""{CURRENT_HOOK}\n"""
    assert sorted(path.name for path in home.iterdir()) == [".bashrc"]
