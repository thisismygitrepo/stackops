from pathlib import Path


KEYMAP_PATHS = (
    Path("src/machineconfig/settings/yazi/keymap_linux.toml"),
    Path("src/machineconfig/settings/yazi/keymap_darwin.toml"),
    Path("src/machineconfig/settings/yazi/keymap_windows.toml"),
)


def test_ouch_decompress_uses_hovered_placeholder() -> None:
    expected_binding = 'run  = \'shell --block -- ouch decompress "%h"\''

    for keymap_path in KEYMAP_PATHS:
        keymap_text = keymap_path.read_text(encoding="utf-8")

        assert expected_binding in keymap_text, str(keymap_path)