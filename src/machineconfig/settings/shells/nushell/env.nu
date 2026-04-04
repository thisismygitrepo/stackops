let home = (($env.HOME? | default ($env.USERPROFILE? | default $nu.home-dir)) | path expand)
let config_root = (($env.CONFIG_ROOT? | default ($home | path join ".config" "machineconfig")) | path expand)
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
    _ => [
        ($config_root | path join "scripts")
        ($home | path join ".local" "bin")
        ($home | path join ".cargo" "bin")
    ]
}

for path_entry in $paths_to_add {
    if ($path_entry | path exists) {
        path add --append $path_entry
    }
}
