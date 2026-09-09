#!/usr/bin/env nu

def read-shell-environment [file_path: path, powershell: bool]: nothing -> record {
    if $powershell {
        open --raw $file_path | from json
    } else {
        open --raw $file_path
        | split row (char nul)
        | where {|entry| $entry != "" }
        | parse --regex '(?s)^(?<key>[^=]+)=(?<value>.*)$'
        | transpose --header-row --as-record
    }
}

export def --env --wrapped wrap_in_shell_script [command: string, ...args: string]: nothing -> nothing {
    let powershell = $nu.os-info.name == "windows"
    let extension = if $powershell { "ps1" } else { "sh" }
    let op_dir = ($nu.home-dir | path join "tmp_results" "tmp_scripts" "stackops")
    mkdir $op_dir
    let op_program_path = ($op_dir | path join $"(random uuid).($extension)")

    with-env {OP_PROGRAM_PATH: $op_program_path} {
        ^$command ...$args
    }

    if ($op_program_path | path exists) {
        let before_path = $"($op_program_path).before"
        let after_path = $"($op_program_path).after"
        print --stderr $"stackops: running ($op_program_path)"
        try {
            with-env {
                OP_PROGRAM_PATH: $op_program_path
                STACKOPS_ENV_BEFORE: $before_path
                STACKOPS_ENV_AFTER: $after_path
            } {
                if $powershell {
                    ^powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command r#'
function Save-StackOpsEnvironment([string]$Path) {
    $snapshot = [Environment]::GetEnvironmentVariables()
    $snapshot["PWD"] = (Get-Location).ProviderPath
    [IO.File]::WriteAllText($Path, ($snapshot | ConvertTo-Json -Compress))
}
Save-StackOpsEnvironment $env:STACKOPS_ENV_BEFORE
$global:LASTEXITCODE = 0
try {
    . $env:OP_PROGRAM_PATH
    $stackopsSucceeded = $?
    $stackopsExitCode = $LASTEXITCODE
    if (-not $stackopsSucceeded -and $stackopsExitCode -eq 0) { $stackopsExitCode = 1 }
} finally {
    Save-StackOpsEnvironment $env:STACKOPS_ENV_AFTER
}
exit $stackopsExitCode
'#
                } else {
                    ^bash --noprofile --norc -c r#'
umask 077
stackops_capture_environment() {
    local stackops_env_key
    while IFS= read -r stackops_env_key; do
        printf "%s=%s\0" "$stackops_env_key" "${!stackops_env_key}"
    done < <(compgen -e)
}
stackops_capture_environment > "$STACKOPS_ENV_BEFORE"
trap 'stackops_exit_code=$?; stackops_capture_environment > "$STACKOPS_ENV_AFTER"; exit "$stackops_exit_code"' EXIT
source "$OP_PROGRAM_PATH"
'#
                }
            }
        } finally {
            try {
                if ($before_path | path exists) and ($after_path | path exists) {
                    let before = (read-shell-environment $before_path $powershell)
                    let after = (read-shell-environment $after_path $powershell)
                    let ignored = [PWD SHLVL _ OP_PROGRAM_PATH STACKOPS_ENV_BEFORE STACKOPS_ENV_AFTER]
                    if $after.PWD != $before.PWD {
                        cd $after.PWD
                    }
                    for key in ($before | columns | where {|key| $key not-in ($after | columns) and $key not-in $ignored }) {
                        hide-env $key
                    }
                    for entry in ($after | transpose key value) {
                        if $entry.key not-in $ignored and $entry.value != ($before | get --optional $entry.key) {
                            let conversion = ($env.ENV_CONVERSIONS? | default {} | get --optional $entry.key | get --optional from_string)
                            let value = if $conversion != null {
                                do $conversion $entry.value
                            } else if $entry.key == "PATH" or ($powershell and $entry.key == "Path") {
                                $entry.value | split row (char esep)
                            } else {
                                $entry.value
                            }
                            load-env {($entry.key): $value}
                        }
                    }
                }
            } finally {
                rm --force $before_path $after_path
            }
        }
    }
    $env.LAST_EXIT_CODE = 0
}

def --env --wrapped main [command: string, ...args: string]: nothing -> nothing {
    wrap_in_shell_script $command ...$args
}
