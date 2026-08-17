import base64
import shlex

from rich import box
from rich.console import Console
from rich.panel import Panel

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_keys import PublicKeyRecord
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_remote_connection import (
    ConnectedRemote,
    RemoteCommandResult,
    encode_powershell_command,
    open_remote_connection,
    run_remote_command,
)


console = Console()
WINDOWS_MARKER = "STACKOPS_WINDOWS"
DEPLOYMENT_MARKER = "STACKOPS_KEY_READY"


def deploy_keys_to_remote(remote_target: str, records: list[PublicKeyRecord], password: str | None) -> bool:
    if not records:
        console.print(Panel("No validated public-key records were supplied.", title="[bold red]Error[/bold red]", border_style="red"))
        return False
    console.print(
        Panel(
            f"Deploying {len(records)} public key record(s) to [cyan]{remote_target}[/cyan]",
            title="[bold blue]Remote SSH Key Deployment[/bold blue]",
            border_style="blue",
        )
    )

    try:
        with open_remote_connection(remote_target=remote_target, password=password) as connection:
            remote_system = _detect_remote_system(connection=connection)
            console.print(f"Remote authorization target: [cyan]{remote_system}[/cyan]")
            for index, record in enumerate(records, start=1):
                result = (
                    _deploy_windows_record(connection=connection, record=record)
                    if remote_system == "Windows"
                    else _deploy_posix_record(connection=connection, record=record)
                )
                _require_deployment_success(result=result, record_number=index)
    except Exception as error:
        console.print(Panel(f"Remote key deployment failed: {error}", title="[bold red]Error[/bold red]", border_style="red"))
        return False

    console.print(
        Panel(
            f"Authorized all {len(records)} public key record(s) on [green]{remote_target}[/green]",
            title="[bold green]Success[/bold green]",
            border_style="green",
            box=box.DOUBLE_EDGE,
        )
    )
    return True


def _detect_remote_system(connection: ConnectedRemote) -> str:
    windows_detection = encode_powershell_command(
        script=f"""if ([Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {{ exit 3 }}
Write-Output '{WINDOWS_MARKER}'"""
    )
    windows_result = run_remote_command(connection=connection, command=windows_detection)
    if windows_result.return_code == 0 and windows_result.stdout.strip() == WINDOWS_MARKER:
        return "Windows"

    posix_result = run_remote_command(connection=connection, command="uname -s")
    if posix_result.return_code == 0 and posix_result.stdout.strip() != "":
        return f"POSIX ({posix_result.stdout.strip()})"
    raise RuntimeError(
        f"Unable to detect a native Windows or POSIX remote environment. "
        f"PowerShell error: {windows_result.stderr.strip()!r}; uname error: {posix_result.stderr.strip()!r}"
    )


def _deploy_posix_record(connection: ConnectedRemote, record: PublicKeyRecord) -> RemoteCommandResult:
    quoted_record = shlex.quote(record.text)
    script = f"""set -eu
ssh_directory="$HOME/.ssh"
authorized_keys="$ssh_directory/authorized_keys"
public_key={quoted_record}
umask 077
mkdir -p "$ssh_directory"
chmod 700 "$ssh_directory"
touch "$authorized_keys"
chmod 600 "$authorized_keys"
if [ -s "$authorized_keys" ] && [ -n "$(tail -c 1 "$authorized_keys")" ]; then
    printf '\n' >> "$authorized_keys"
fi
if grep -F -x -q "$public_key" "$authorized_keys"; then
    :
else
    grep_status=$?
    if [ "$grep_status" -ne 1 ]; then
        exit "$grep_status"
    fi
    printf '%s\n' "$public_key" >> "$authorized_keys"
fi
chmod 600 "$authorized_keys"
printf '%s\n' {shlex.quote(DEPLOYMENT_MARKER)}
"""
    return run_remote_command(connection=connection, command=script)


def _deploy_windows_record(connection: ConnectedRemote, record: PublicKeyRecord) -> RemoteCommandResult:
    encoded_record = base64.b64encode(record.text.encode("utf-8")).decode("ascii")
    script = _windows_deployment_script().replace("__PUBLIC_KEY_BASE64__", encoded_record)
    return run_remote_command(connection=connection, command=encode_powershell_command(script=script))


def _windows_deployment_script() -> str:
    return r"""$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$administratorsSid = "S-1-5-32-544"
$systemSid = "S-1-5-18"
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$groupSids = @($identity.Groups | ForEach-Object { $_.Value })
$isAdministrator = $groupSids -contains $administratorsSid
$userSid = $identity.User.Value

if ($isAdministrator) {
    $adminSidObject = [System.Security.Principal.SecurityIdentifier]::new($administratorsSid)
    $principal = [System.Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole($adminSidObject)) {
        throw "Administrator account is not elevated; refusing to write ProgramData SSH authorization."
    }
    $sshDirectory = "C:\ProgramData\ssh"
    $authorizedKeys = Join-Path $sshDirectory "administrators_authorized_keys"
    $fileTrustees = @($administratorsSid, $systemSid)
} else {
    if ([string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        throw "USERPROFILE is unavailable for the standard-user SSH authorization path."
    }
    $sshDirectory = Join-Path $env:USERPROFILE ".ssh"
    $authorizedKeys = Join-Path $sshDirectory "authorized_keys"
    $fileTrustees = @($userSid, $systemSid, $administratorsSid)
}

New-Item -ItemType Directory -Path $sshDirectory -Force | Out-Null
if (-not (Test-Path -LiteralPath $authorizedKeys -PathType Leaf)) {
    New-Item -ItemType File -Path $authorizedKeys -Force | Out-Null
}

function Set-RestrictedAcl {
    param([string]$Path, [string[]]$TrusteeSids, [bool]$Directory)
    $grants = @()
    foreach ($trusteeSid in $TrusteeSids) {
        $permission = if ($Directory) { "(OI)(CI)F" } else { "F" }
        $grants += "*$($trusteeSid):$permission"
    }
    $arguments = @($Path, "/inheritance:r", "/grant:r") + $grants
    $aclOutput = & "$env:SystemRoot\System32\icacls.exe" @arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "icacls failed for $Path`: $($aclOutput -join [Environment]::NewLine)"
    }
}

if (-not $isAdministrator) {
    Set-RestrictedAcl -Path $sshDirectory -TrusteeSids $fileTrustees -Directory $true
}
Set-RestrictedAcl -Path $authorizedKeys -TrusteeSids $fileTrustees -Directory $false

$utf8 = [System.Text.UTF8Encoding]::new($false)
$publicKey = $utf8.GetString([Convert]::FromBase64String("__PUBLIC_KEY_BASE64__"))
$existingLines = @([System.IO.File]::ReadAllLines($authorizedKeys, $utf8))
if ($existingLines -cnotcontains $publicKey) {
    $existingLines += $publicKey
}
$content = ($existingLines -join "`n") + "`n"
[System.IO.File]::WriteAllText($authorizedKeys, $content, $utf8)
Set-RestrictedAcl -Path $authorizedKeys -TrusteeSids $fileTrustees -Directory $false
Write-Output "STACKOPS_KEY_READY"
"""


def _require_deployment_success(result: RemoteCommandResult, record_number: int) -> None:
    if result.return_code == 0 and result.stdout.strip() == DEPLOYMENT_MARKER:
        return
    raise RuntimeError(
        f"public-key record {record_number} failed with exit code {result.return_code}; "
        f"stdout={result.stdout.strip()!r}; stderr={result.stderr.strip()!r}"
    )
