export use ../../../scripts/nu/wrap_stackops.nu wrap_in_shell_script

export def --env --wrapped br [...args: string] {
    let cmd_file = (mktemp -t broot.XXXXXX)
    let command_text = try {
        ^broot --outcmd $cmd_file ...$args
        open --raw $cmd_file
    } finally {
        rm --force $cmd_file
    }
    if ($command_text | is-not-empty) {
        let dest = (
            $command_text
            | parse -r `(?s)^cd\s+(?<quote>"|'|)(?<path>.+?)\k<quote>[\s\r\n]*$`
            | get path
            | first
            | str replace --all `'"'"'` "'"
        )
        cd $dest
    }
}

export def --env --wrapped lfcd [...args: string] {
    let cwd_file = (mktemp -t lf.XXXXXX)
    let dest = try {
        ^lf -last-dir-path $cwd_file ...$args
        open --raw $cwd_file | str replace -r '\r?\n$' ''
    } finally {
        rm --force $cwd_file
    }
    if ($dest | is-not-empty) {
        cd $dest
    }
}

export def --env --wrapped y [...args: string] {
    let cwd_file = (mktemp -t yazi.XXXXXX)
    let dest = try {
        ^yazi ...$args --cwd-file $cwd_file
        open --raw $cwd_file
    } finally {
        rm --force $cwd_file
    }
    if ($dest | is-not-empty) and $dest != $env.PWD {
        cd $dest
    }
}

export def --env --wrapped tere_cd [...args: string] {
    if ($args | any {|arg| $arg in ["--help" "-h" "--version" "-V"] }) {
        ^tere ...$args
        return
    }
    let dest = (^tere ...$args | str replace -r '\r?\n$' '')
    if ($dest | is-not-empty) {
        cd $dest
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
    let dest = (^zoxide query --interactive -- ...$args | str trim -r -c "\n")
    if ($dest | is-not-empty) {
        cd $dest
    }
}

export alias lf = lfcd
export alias d = wrap_in_shell_script devops
export alias c = wrap_in_shell_script cloud
export alias a = wrap_in_shell_script agents
export alias s = wrap_in_shell_script seek
export alias f = wrap_in_shell_script fire
export alias p = wrap_in_shell_script preview
export alias u = wrap_in_shell_script utils
export alias t = wrap_in_shell_script terminal
export alias l = ^lsd -la
