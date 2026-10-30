from stackops.profile.dotfiles_mapper import MapperDocument, RawMapperEntry, compose_mapper_documents


def _entry(self_managed: str) -> RawMapperEntry:
    return {"original": "~/x", "self_managed": self_managed, "os": ["linux"]}


def test_user_entries_replace_library_entries_with_the_same_group_and_name() -> None:
    library_mapper: MapperDocument = {"yazi": {"yazi": _entry("CONFIG_ROOT/y"), "keymap": _entry("CONFIG_ROOT/k")}, "helix": {"config": _entry("CONFIG_ROOT/h")}}
    user_mapper: MapperDocument = {"yazi": {"yazi": _entry("DOTFILES_ROOT/y")}, "helix": {"config": _entry("DOTFILES_ROOT/h")}, "ssh": {"keys": _entry("DOTFILES_ROOT/s")}}

    assert compose_mapper_documents(library_mapper=library_mapper, user_mapper=user_mapper, source="library") == {"yazi": {"keymap": _entry("CONFIG_ROOT/k")}}
    assert compose_mapper_documents(library_mapper=library_mapper, user_mapper=user_mapper, source="all") == {
        "yazi": {"keymap": _entry("CONFIG_ROOT/k"), "yazi": _entry("DOTFILES_ROOT/y")},
        "helix": {"config": _entry("DOTFILES_ROOT/h")},
        "ssh": {"keys": _entry("DOTFILES_ROOT/s")},
    }
