use ($nu.home-dir | path join ".config" "stackops" "settings" "shells" "nushell" "init.nu") *

def --env __stackops_init_starship [] {
    if ($env.__STACKOPS_STARSHIP_INIT? | default false) {
        return
    }

    let starship_path = (which starship | get 0.path)

    $env.STARSHIP_SHELL = "nu"
    $env.STARSHIP_SESSION_KEY = (random chars -l 16)
    $env.PROMPT_MULTILINE_INDICATOR = (^$starship_path prompt --continuation)
    $env.PROMPT_INDICATOR = ""

    $env.PROMPT_COMMAND = {||
        let cmd_duration = if $env.CMD_DURATION_MS == "0823" { 0 } else { $env.CMD_DURATION_MS }
        let jobs_args = ["--jobs", (job list | length)]

        ^$starship_path prompt --cmd-duration $cmd_duration $"--status=($env.LAST_EXIT_CODE)" --terminal-width (term size).columns ...$jobs_args
    }

    $env.PROMPT_COMMAND_RIGHT = {||
        let cmd_duration = if $env.CMD_DURATION_MS == "0823" { 0 } else { $env.CMD_DURATION_MS }
        let jobs_args = ["--jobs", (job list | length)]

        ^$starship_path prompt --right --cmd-duration $cmd_duration $"--status=($env.LAST_EXIT_CODE)" --terminal-width (term size).columns ...$jobs_args
    }

    $env.config = ($env.config | merge { render_right_prompt_on_last_line: true })
    $env.__STACKOPS_STARSHIP_INIT = true
}

def --env __stackops_init_zoxide [] {
    if ($env.__STACKOPS_ZOXIDE_INIT? | default false) {
        return
    }

    let config_hooks = ($env.config.hooks? | default {})
    let env_change_hooks = ($config_hooks | get env_change? | default {})

    $env.config = (
        $env.config
        | upsert hooks (
            $config_hooks
            | upsert env_change (
                $env_change_hooks
                | upsert PWD (
                    ($env_change_hooks | get PWD? | default [])
                    | append {
                        __stackops_zoxide_hook: true
                        code: {|_, dir| ^zoxide add -- $dir }
                    }
                )
            )
        )
    )

    $env.__STACKOPS_ZOXIDE_INIT = true
}

def __stackops_atuin_search_cmd [...flags: string] {
    [
        ($env.__STACKOPS_ATUIN_KEYBINDING_TOKEN? | default ""),
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

def --env __stackops_init_atuin [] {
    if ($env.__STACKOPS_ATUIN_INIT? | default false) {
        return
    }

    if "ATUIN_SESSION" not-in $env or ("ATUIN_SHLVL" not-in $env) or ($env.ATUIN_SHLVL != ($env.SHLVL? | default "")) {
        $env.ATUIN_SESSION = (random uuid -v 7 | str replace -a "-" "")
        $env.ATUIN_SHLVL = ($env.SHLVL? | default "")
    }

    hide-env -i ATUIN_HISTORY_ID
    $env.__STACKOPS_ATUIN_KEYBINDING_TOKEN = $"# (random uuid)"

    let atuin_pre_execution = {||
        if ($nu | get history-enabled?) == false {
            return
        }

        let cmd = (commandline)
        if ($cmd | is-empty) {
            return
        }

        if not ($cmd | str starts-with $env.__STACKOPS_ATUIN_KEYBINDING_TOKEN) {
            $env.ATUIN_HISTORY_ID = (atuin history start -- $cmd e>| complete | get stdout | str trim)
        }
    }

    let atuin_pre_prompt = {||
        let last_exit = $env.LAST_EXIT_CODE

        if "ATUIN_HISTORY_ID" not-in $env {
            return
        }

        with-env { ATUIN_LOG: error } {
            job spawn {
                ^atuin history end $'--exit=($env.LAST_EXIT_CODE)' -- $env.ATUIN_HISTORY_ID | complete
            } | ignore
        }

        hide-env ATUIN_HISTORY_ID
    }

    let config_hooks = ($env.config.hooks? | default {})
    let keybindings = ($env.config.keybindings? | default [])

    $env.config = (
        $env.config
        | upsert hooks (
            $config_hooks
            | upsert pre_execution (($config_hooks | get pre_execution? | default []) | append $atuin_pre_execution)
            | upsert pre_prompt (($config_hooks | get pre_prompt? | default []) | append $atuin_pre_prompt)
        )
        | upsert keybindings (
            $keybindings
            | append {
                name: "stackops_atuin_ctrl_r"
                modifier: control
                keycode: char_r
                mode: [emacs, vi_normal, vi_insert]
                event: { send: executehostcommand cmd: (__stackops_atuin_search_cmd) }
            }
            | append {
                name: "stackops_atuin_up"
                modifier: none
                keycode: up
                mode: [emacs, vi_normal, vi_insert]
                event: {
                    until: [
                        { send: menuup }
                        { send: executehostcommand cmd: (__stackops_atuin_search_cmd "--shell-up-key-binding") }
                    ]
                }
            }
        )
    )

    $env.__STACKOPS_ATUIN_INIT = true
}

__stackops_init_zoxide
__stackops_init_starship
__stackops_init_atuin

const stackops_user_init = if (($nu.home-dir | path join "dotfiles" "stackops" "init_nu.nu") | path exists) {
    ($nu.home-dir | path join "dotfiles" "stackops" "init_nu.nu")
} else {
    null
}

if $stackops_user_init != null {
    source $stackops_user_init
}
