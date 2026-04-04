use ($nu.home-dir | path join ".config" "machineconfig" "settings" "shells" "nushell" "init.nu") *

def __machineconfig_has_command [command: string] {
    which $command | is-not-empty
}

def --env __machineconfig_init_starship [] {
    if ($env.__MACHINECONFIG_STARSHIP_INIT? | default false) {
        return
    }

    let starship_path = (which starship | get 0.path)

    $env.STARSHIP_SHELL = "nu"
    $env.STARSHIP_SESSION_KEY = (random chars -l 16)
    $env.PROMPT_MULTILINE_INDICATOR = (^$starship_path prompt --continuation)
    $env.PROMPT_INDICATOR = ""

    $env.PROMPT_COMMAND = {||
        let cmd_duration = if $env.CMD_DURATION_MS == "0823" { 0 } else { $env.CMD_DURATION_MS }
        let jobs_args = if (which "job list" | where type == built-in | is-not-empty) {
            ["--jobs", (job list | length)]
        } else {
            []
        }

        ^$starship_path prompt --cmd-duration $cmd_duration $"--status=($env.LAST_EXIT_CODE)" --terminal-width (term size).columns ...$jobs_args
    }

    $env.PROMPT_COMMAND_RIGHT = {||
        let cmd_duration = if $env.CMD_DURATION_MS == "0823" { 0 } else { $env.CMD_DURATION_MS }
        let jobs_args = if (which "job list" | where type == built-in | is-not-empty) {
            ["--jobs", (job list | length)]
        } else {
            []
        }

        ^$starship_path prompt --right --cmd-duration $cmd_duration $"--status=($env.LAST_EXIT_CODE)" --terminal-width (term size).columns ...$jobs_args
    }

    $env.config = ($env.config? | default {} | merge { render_right_prompt_on_last_line: true })
    $env.__MACHINECONFIG_STARSHIP_INIT = true
}

def --env __machineconfig_init_zoxide [] {
    if ($env.__MACHINECONFIG_ZOXIDE_INIT? | default false) {
        return
    }

    $env.config = (
        $env.config?
        | default {}
        | upsert hooks { default {} }
        | upsert hooks.env_change { default {} }
        | upsert hooks.env_change.PWD { default [] }
    )

    let zoxide_hooked = (
        $env.config.hooks.env_change.PWD
        | any {|hook| $hook | get __machineconfig_zoxide_hook? | default false }
    )

    if not $zoxide_hooked {
        $env.config.hooks.env_change.PWD = (
            $env.config.hooks.env_change.PWD
            | append {
                __machineconfig_zoxide_hook: true
                code: {|_, dir| ^zoxide add -- $dir }
            }
        )
    }

    $env.__MACHINECONFIG_ZOXIDE_INIT = true
}

def __machineconfig_atuin_search_cmd [...flags: string] {
    [
        ($env.__MACHINECONFIG_ATUIN_KEYBINDING_TOKEN? | default ""),
        ([
            `with-env { ATUIN_LOG: error, ATUIN_QUERY: (commandline), ATUIN_SHELL: nu } {`,
                ([
                    "let output = (run-external atuin search",
                    ($flags | append [--interactive] | each {|flag| $'"($flag)"'}),
                    "e>| str trim)",
                ] | flatten | str join " "),
                'if ($output | str starts-with "__atuin_accept__:") {',
                'commandline edit --accept ($output | str replace "__atuin_accept__:" "")',
                "} else {",
                "commandline edit $output",
                "}",
            `}`,
        ] | flatten | str join "\n"),
    ] | str join "\n"
}

def --env __machineconfig_init_atuin [] {
    if ($env.__MACHINECONFIG_ATUIN_INIT? | default false) {
        return
    }

    if "ATUIN_SESSION" not-in $env or ("ATUIN_SHLVL" not-in $env) or ($env.ATUIN_SHLVL != ($env.SHLVL? | default "")) {
        $env.ATUIN_SESSION = (random uuid -v 7 | str replace -a "-" "")
        $env.ATUIN_SHLVL = ($env.SHLVL? | default "")
    }

    hide-env -i ATUIN_HISTORY_ID
    $env.__MACHINECONFIG_ATUIN_KEYBINDING_TOKEN = $"# (random uuid)"

    let atuin_pre_execution = {||
        if ($nu | get history-enabled?) == false {
            return
        }

        let cmd = (commandline)
        if ($cmd | is-empty) {
            return
        }

        if not ($cmd | str starts-with $env.__MACHINECONFIG_ATUIN_KEYBINDING_TOKEN) {
            $env.ATUIN_HISTORY_ID = (atuin history start -- $cmd e>| complete | get stdout | str trim)
        }
    }

    let atuin_pre_prompt = {||
        let last_exit = $env.LAST_EXIT_CODE

        if "ATUIN_HISTORY_ID" not-in $env {
            return
        }

        with-env { ATUIN_LOG: error } {
            if (version).minor >= 104 or (version).major > 0 {
                job spawn {
                    ^atuin history end $'--exit=($env.LAST_EXIT_CODE)' -- $env.ATUIN_HISTORY_ID | complete
                } | ignore
            } else {
                do { atuin history end $'--exit=($last_exit)' -- $env.ATUIN_HISTORY_ID } | complete
            }
        }

        hide-env ATUIN_HISTORY_ID
    }

    $env.config = (
        $env.config?
        | default {}
        | upsert hooks { default {} }
        | upsert keybindings { default [] }
    )

    $env.config = (
        $env.config
        | upsert hooks (
            $env.config.hooks
            | upsert pre_execution (($env.config.hooks.pre_execution? | default []) | append $atuin_pre_execution)
            | upsert pre_prompt (($env.config.hooks.pre_prompt? | default []) | append $atuin_pre_prompt)
        )
        | upsert keybindings (
            $env.config.keybindings
            | where {|binding| ($binding | get name? | default "") not-in ["machineconfig_atuin_ctrl_r", "machineconfig_atuin_up"] }
            | append {
                name: "machineconfig_atuin_ctrl_r"
                modifier: control
                keycode: char_r
                mode: [emacs, vi_normal, vi_insert]
                event: { send: executehostcommand cmd: (__machineconfig_atuin_search_cmd) }
            }
            | append {
                name: "machineconfig_atuin_up"
                modifier: none
                keycode: up
                mode: [emacs, vi_normal, vi_insert]
                event: {
                    until: [
                        { send: menuup }
                        { send: executehostcommand cmd: (__machineconfig_atuin_search_cmd "--shell-up-key-binding") }
                    ]
                }
            }
        )
    )

    $env.__MACHINECONFIG_ATUIN_INIT = true
}

def __machineconfig_tv_history_cmd [] {
    [
        "let output = (run-external tv nu-history --input (commandline) --inline e>| str trim)",
        "if ($output | is-not-empty) {",
        "commandline edit $output",
        "}",
    ] | str join "\n"
}

def --env __machineconfig_init_tv_history [] {
    if ($env.__MACHINECONFIG_TV_HISTORY_INIT? | default false) {
        return
    }

    $env.config = (
        $env.config?
        | default {}
        | upsert keybindings { default [] }
    )

    $env.config = (
        $env.config
        | upsert keybindings (
            $env.config.keybindings
            | where {|binding| ($binding | get name? | default "") != "machineconfig_tv_history" }
            | append {
                name: "machineconfig_tv_history"
                modifier: control
                keycode: char_r
                mode: [emacs, vi_normal, vi_insert]
                event: { send: executehostcommand cmd: (__machineconfig_tv_history_cmd) }
            }
        )
    )

    $env.__MACHINECONFIG_TV_HISTORY_INIT = true
}

if (__machineconfig_has_command "zoxide") {
    __machineconfig_init_zoxide
}

if (__machineconfig_has_command "starship") {
    __machineconfig_init_starship
}

if (__machineconfig_has_command "atuin") {
    __machineconfig_init_atuin
} else if (__machineconfig_has_command "tv") {
    __machineconfig_init_tv_history
}

const machineconfig_user_init = if (($nu.home-dir | path join "dotfiles" "machineconfig" "init_nu.nu") | path exists) {
    ($nu.home-dir | path join "dotfiles" "machineconfig" "init_nu.nu")
} else {
    null
}

source $machineconfig_user_init
