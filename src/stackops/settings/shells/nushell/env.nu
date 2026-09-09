let stackops_home = ($nu.home-dir | path expand)
let config_root = ($stackops_home | path join ".config" "stackops")
$env.CONFIG_ROOT = $config_root

use std/util "path add"

let os_name = $nu.os-info.name
let paths_to_add = match $os_name {
    "windows" => [
        ($stackops_home | path join ".local" "bin")
        ($stackops_home | path join ".local" "share" "poppler" "Library" "bin")
        ($stackops_home | path join ".bun" "bin")
        ($config_root | path join "scripts")
        ($stackops_home | path join "dotfiles" "stackops" "scripts" "windows")
        "C:\\Program Files (x86)\\GnuWin32\\bin"
        "C:\\Program Files\\CodeBlocks\\MinGW\\bin"
        "C:\\Program Files\\nu\\bin"
        "C:\\Program Files\\Graphviz\\bin"
        "C:\\Program Files\\7-Zip"
    ]
    "linux" => [
        ($config_root | path join "scripts")
        ($stackops_home | path join "dotfiles" "stackops" "scripts" "linux")
        ($stackops_home | path join ".local" "bin")
        ($stackops_home | path join ".cargo" "bin")
        ($stackops_home | path join ".duckdb" "cli" "latest")
        "/usr/games"
    ]
    "macos" => [
        ($config_root | path join "scripts")
        ($stackops_home | path join "dotfiles" "stackops" "scripts" "macos")
        ($stackops_home | path join ".local" "bin")
        ($stackops_home | path join ".cargo" "bin")
        "/usr/games"
    ]
}

path add --append ($config_root | path join "scripts" "nu") ...$paths_to_add
