# OneDrive API without rclone

This module provides direct OneDrive integration using Microsoft Graph API without requiring rclone. It backs the `cloud onedrive` command group.

## Features

- ✅ Fresh access token for every operation, obtained from the stored refresh token
- ✅ Persistent refresh-token storage in the StackOps secrets file
- ✅ Upload/download files, list and search the drive, move items to the recycle bin
- ✅ Streamed downloads; uploads send the file in a single `PUT` (no chunked upload session)
- ✅ Direct OAuth2 authentication setup (device-code flow)
- ✅ Multiple named accounts

## Quick Start

### Direct OAuth Setup

1. **Set up Azure App Registration:**
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to 'Azure Active Directory' > 'App registrations'
   - Click 'New registration'
   - Name: 'OneDrive API Access'
   - Redirect URI: none needed; sign-in uses the device-code flow as a public client against the `consumers` endpoint
   - Add permissions: `User.Read`, `Files.ReadWrite` and `offline_access`

2. **Register the account with its Application (client) ID:**
   ```bash
   cloud onedrive add-account personal --client-id 'your_client_id_here'
   ```

3. **Run initial setup:**
   ```bash
   cloud onedrive auth personal
   ```
   Open the printed URL and enter the code; the refresh token is then saved for that account.

Existing rclone tokens are not read by this module.

## Usage Examples

```bash
# List a remote folder (defaults to /)
cloud onedrive list /Documents

# Search the drive
cloud onedrive search report

# Upload a file (add --overwrite to replace an existing remote item)
cloud onedrive upload /path/to/local/file.pdf /Documents/file.pdf

# Download a file to a new local path
cloud onedrive download /Documents/file.pdf /path/to/local/downloaded.pdf

# Move an item to the recycle bin
cloud onedrive delete /Documents/file.pdf
```

| Command | Purpose | Options |
| --- | --- | --- |
| `add-account [account_name]` | Add an account; prompts for omitted values | `--client-id/-c`, `--json/-j` |
| `auth [account_name]` | Authenticate with Microsoft | `--json/-j` |
| `status [account_name]` | Show account and storage status | `--json/-j` |
| `accounts` | List defined accounts and whether each is authenticated | `--json/-j` |
| `list [remote_path]` | List a remote folder | `--account/-a`, `--json/-j` |
| `search <query>` | Search the drive | `--account/-a`, `--json/-j` |
| `download <remote_path> <local_path>` | Download a remote file | `--account/-a`, `--json/-j` |
| `upload <local_path> <remote_path>` | Upload a local file | `--overwrite/-o`, `--account/-a` |
| `delete <remote_path>` | Move an item to the recycle bin | `--yes/-y`, `--account/-a` |
| `config-path` | Print the global StackOps secrets path | |

`list`, `search`, `download`, `upload` and `delete` select the account with `--account/-a`; `auth`, `status` and `add-account` take it as a positional argument. Omit it to use the only configured account or enter it interactively. `status` and `upload` always print JSON. `download` refuses to overwrite an existing local file. Without `--yes`, `delete` needs an interactive terminal and asks you to type `DELETE`.

The same operations are available from Python and raise `OneDriveError` on failure:

```python
from pathlib import Path

from stackops.utils.cloud.onedrive.file_ops import download_file, upload_file

# Upload a file
upload_file(account_name="personal", local_path=Path("/path/to/local/file.pdf"), remote_path="/Documents/file.pdf", overwrite=False)

# Download a file
download_file(account_name="personal", remote_path="/Documents/file.pdf", local_path=Path("/path/to/local/downloaded.pdf"), output_json=False)
```

Modules: `cli.py` (Typer app), `accounts.py` (account entries in the secrets file), `credentials.py`, `auth.py` (device-code sign-in, token refresh, Graph requests), `items.py` (`show_status`, `list_items`, `search_items`), `file_ops.py` (`download_file`, `upload_file`, `delete_item`), `constants.py`, `errors.py` and `output.py`.

## Token Management

### Automatic Token Refresh

The system automatically handles token refresh:

```python
from stackops.utils.cloud.onedrive.auth import refresh_access_token

# Exchanges the stored refresh token for a new access token
token = refresh_access_token(account_name="personal")
```

### Manual Token Operations

```python
from stackops.utils.cloud.onedrive.auth import authenticate
from stackops.utils.cloud.onedrive.credentials import load_credentials, save_refresh_token

# Run the device-code sign-in and save the refresh token
authenticate(account_name="personal", output_json=False)

# Load the stored client ID and refresh token
credentials = load_credentials(account_name="personal", require_refresh_token=True)

# Save a refresh token to the account's secrets entry
save_refresh_token(account_name="personal", client_id=credentials["client_id"], refresh_token=new_refresh_token)
```

## How Token Renewal Works

1. **Every Operation**: `status`, `list`, `search`, `download`, `upload` and `delete` each request a new access token before calling Graph; access tokens are never stored
2. **Refresh**: The stored refresh token is exchanged at the Microsoft token endpoint
3. **Persistent Storage**: The refresh token Microsoft returns (or the current one, when none is returned) is written back to the account's entry in the StackOps secrets file
4. **Failure**: A missing refresh token names the `cloud onedrive auth <account>` command to run; a rejected refresh reports Microsoft's error message

## No rclone Required

This implementation eliminates the need for rclone by:

- Using Microsoft Graph API directly
- Implementing OAuth2 flow natively
- Managing token lifecycle automatically
- Providing persistent token storage

## Error Handling

Failures raise `OneDriveError`; the CLI prints `Error: <message>` and exits with code 1:

- Missing refresh token → The `cloud onedrive auth <account>` command to run
- Network errors → `Network request failed: <details>`
- Unknown account → The `cloud onedrive add-account` command and the expected secrets entry
- Graph or token endpoint errors → Microsoft's error message

## Files Created

- No token file of its own: each account is one entry in the global StackOps secrets file (`cloud onedrive config-path` prints its path), with login name `onedrive`, tag `onedrive-stackops-cli` and a secret named `oauth` holding `ONEDRIVE_CLIENT_ID` and, after `auth`, `ONEDRIVE_REFRESH_TOKEN`
- `add-account` creates that file when it is missing
- Credentials are read when a command runs, not on import

## Security

- A secrets file created by `add-account` gets restrictive permissions (600); later updates keep the file's existing mode
- No client secret is used (public client mode)
- Access tokens stay in memory; refresh tokens are written through an atomic file replace
- No command prints access or refresh tokens

## Troubleshooting

### Token Refresh Failed
```bash
# Check which accounts are authenticated
cloud onedrive accounts

# Or re-run OAuth setup
cloud onedrive auth personal
```

### Permission Errors
Make sure your Azure app has the correct permissions:
- `User.Read` (Delegated)
- `Files.ReadWrite` (Delegated)
- `offline_access` (Delegated)

### Network Issues
Check your firewall allows connections to:
- `https://login.microsoftonline.com`
- `https://graph.microsoft.com`
