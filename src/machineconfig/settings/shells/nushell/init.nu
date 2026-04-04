# machineconfig Nushell initialization

def get_home []: nothing -> string {
    $nu.home-dir
}

def ensure_directory [dir: string] {
    if not ($dir | path exists) {
        mkdir $dir
    }
}

def temp_file [prefix: string, suffix: string]: nothing -> string {
    let base_dir = $nu.temp-dir
    ensure_directory $base_dir
    let token = (random uuid | str replace "-" "" | str substring 0..16)
    let file_path = ($base_dir | path join $"($prefix)($token)($suffix)")
    "" | save --force $file_path
    $file_path
}

export def wrap_in_shell_script [command: string, ...args: string] {
    let op_dir = ((get_home) | path join "tmp_results" "tmp_scripts" "machineconfig")
    ensure_directory $op_dir
    let random_name = (random uuid | str replace "-" "" | str substring 0..16)
    let op_program_path = ($op_dir | path join $"($random_name).sh")
    let timestamp = (date now | format date "%Y-%m-%d %H:%M:%SZ")

    print $"machineconfig: running ($command) at ($timestamp)"
    print $"machineconfig: op program path ($op_program_path)"

    with-env { OP_PROGRAM_PATH: $op_program_path } { ^$command ...$args }

    if ($op_program_path | path exists) {
        print (open --raw $op_program_path)
        ^bash $op_program_path
    }

    print $"machineconfig: completed ($command)"
}

export def --env br [...args: string] {
    let cmd_file = (temp_file "broot-" ".cmd")
    try { ^broot "--outcmd" $cmd_file ...$args } catch { rm --force $cmd_file; return }
    if ($cmd_file | path exists) {
        let command_text = (open --raw $cmd_file | str trim)
        rm --force $cmd_file
        if ($command_text | str length) > 0 {
            let parsed_cd = try {
                $command_text | parse "cd \"{path}\"" | get path | first
            } catch { null }
            if $parsed_cd != null and ($parsed_cd | str length) > 0 {
                cd $parsed_cd
            } else {
                try { nu -c $command_text } catch { }
            }
        }
    }
}

export def --env lfcd [...args: string] {
    let tmp = (temp_file "lf-" ".tmp")
    try { ^lf $"--last-dir-path=($tmp)" ...$args } catch { }
    if ($tmp | path exists) {
        let dir = (open --raw $tmp | str trim)
        rm --force $tmp
        if ($dir | str length) > 0 and ($dir | path exists) {
            cd $dir
        }
    }
}

export def --env y [...args: string] {
    let tmp = (temp_file "yazi-" ".tmp")
    try { ^yazi ...$args $"--cwd-file=($tmp)" } catch { }
    if ($tmp | path exists) {
        let dir = (open --raw $tmp | str trim)
        rm --force $tmp
        if ($dir | str length) > 0 and ($dir | path exists) {
            cd $dir
        }
    }
}

export def --env tere_cd [...args: string] {
    let result = try { ^tere ...$args | complete } catch { null }
    if $result != null {
        let dest = ($result.stdout | str trim)
        if ($dest | str length) > 0 and ($dest | path exists) {
            cd $dest
        }
    }
}

export def --env --wrapped z [...args: string] {
    let dest = match $args {
        [] => { "~" }
        [ "-" ] => { "-" }
        [ $arg ] if ($arg | path expand | path type) == "dir" => { $arg }
        _ => { ^zoxide query --exclude $env.PWD -- ...$args | str trim -r -c "\n" }
    }
    cd $dest
}

export def --env --wrapped zi [...args: string] {
    cd $'(^zoxide query --interactive -- ...$args | str trim -r -c "\n")'
}

export alias lf = lfcd

export def d [...args: string] { wrap_in_shell_script "devops" ...$args }
export def c [...args: string] { wrap_in_shell_script "cloud" ...$args }
export def a [...args: string] { wrap_in_shell_script "agents" ...$args }
export def s [...args: string] { wrap_in_shell_script "sessions" ...$args }
export def fx [...args: string] { wrap_in_shell_script "ftpx" ...$args }
export def f [...args: string] { wrap_in_shell_script "fire" ...$args }
export def r [...args: string] { wrap_in_shell_script "croshell" ...$args }
export def u [...args: string] { wrap_in_shell_script "utils" ...$args }
export def t [...args: string] { wrap_in_shell_script "terminal" ...$args }
export def ms [...args: string] { wrap_in_shell_script "msearch" ...$args }
export def x [...args: string] { wrap_in_shell_script "explore" ...$args }

export alias l = lsd -la
