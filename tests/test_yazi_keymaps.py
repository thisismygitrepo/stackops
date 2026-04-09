from pathlib import Path


KEYMAP_PATHS = (
    Path("src/machineconfig/settings/yazi/keymap_linux.toml"),
    Path("src/machineconfig/settings/yazi/keymap_darwin.toml"),
    Path("src/machineconfig/settings/yazi/keymap_windows.toml"),
)
FULLSCREEN_PREVIEW_BINDINGS = {
    Path("src/machineconfig/settings/yazi/keymap_linux.toml"): """[[mgr.prepend_keymap]]
on   = "v"
run  = 'shell --block -- uv run --python 3.14 "$HOME/.config/yazi/scripts/fullscreen_preview.py" __YAZI_HOVERED__ %h __YAZI_SELECTED__ %s'
desc = "Open a standalone fullscreen preview"
""",
    Path("src/machineconfig/settings/yazi/keymap_darwin.toml"): """[[mgr.prepend_keymap]]
on   = "v"
run  = 'shell --block -- uv run --python 3.14 "$HOME/.config/yazi/scripts/fullscreen_preview.py" __YAZI_HOVERED__ %h __YAZI_SELECTED__ %s'
desc = "Open a standalone fullscreen preview"
""",
    Path("src/machineconfig/settings/yazi/keymap_windows.toml"): """[[mgr.prepend_keymap]]
on   = "v"
run  = 'shell --block -- powershell -NoLogo -NoProfile -Command uv run --python 3.14 "$HOME/AppData/Roaming/yazi/config/scripts/fullscreen_preview.py" __YAZI_HOVERED__ %h __YAZI_SELECTED__ %s'
desc = "Open a standalone fullscreen preview"
""",
}


def test_ouch_decompress_uses_hovered_placeholder() -> None:
    expected_binding = 'run  = \'shell --block -- ouch decompress "%h"\''

    for keymap_path in KEYMAP_PATHS:
        keymap_text = keymap_path.read_text(encoding="utf-8")

        assert expected_binding in keymap_text, str(keymap_path)


def test_fullscreen_preview_binding_exists() -> None:
    for keymap_path, expected_binding in FULLSCREEN_PREVIEW_BINDINGS.items():
        keymap_text = keymap_path.read_text(encoding="utf-8")

        assert expected_binding in keymap_text, str(keymap_path)
