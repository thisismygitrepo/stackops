let home = ($nu.home-dir | path expand)
let config_root = ($home | path join ".config" "machineconfig")
$env.CONFIG_ROOT = $config_root

use std/util "path add"

let os_name = ($nu.os-info.name | str downcase)
let paths_to_add = match $os_name {
    "windows" => [
        ($home | path join ".local" "bin")
        ($home | path join ".local" "share" "poppler" "Library" "bin")
        ($home | path join ".bun" "bin")
        ($config_root | path join "scripts")
        ($home | path join "dotfiles" "scripts" "windows")
        "C:\\Program Files (x86)\\GnuWin32\\bin"
        "C:\\Program Files\\CodeBlocks\\MinGW\\bin"
        "C:\\Program Files\\nu\\bin"
        "C:\\Program Files\\Graphviz\\bin"
        "C:\\Program Files\\7-Zip"
    ]
    "linux" => [
        ($config_root | path join "scripts")
        ($home | path join "dotfiles" "scripts" "linux")
        ($home | path join ".local" "bin")
        ($home | path join ".cargo" "bin")
        ($home | path join ".duckdb" "cli" "latest")
        "/usr/games"
    ]
    "macos" => [
        ($config_root | path join "scripts")
        ($home | path join "dotfiles" "scripts" "macos")
        ($home | path join ".local" "bin")
        ($home | path join ".cargo" "bin")
        "/usr/games"
    ]
    "darwin" => [
        ($config_root | path join "scripts")
        ($home | path join "dotfiles" "scripts" "macos")
        ($home | path join ".local" "bin")
        ($home | path join ".cargo" "bin")
        "/usr/games"
    ]
}

path add --append ...$paths_to_add
