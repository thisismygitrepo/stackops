# Package Management

The current package installation workflow is centered on `devops install`.

---

## Overview

Machineconfig keeps package installation behind one command surface:

```bash
devops install --help
```

The live help currently describes `devops install [WHICH]` as the supported package entrypoint.

---

## Installation modes

Current help shows three main ways to use `devops install`:

### Install named programs

Pass `WHICH` as a comma-separated list of program names:

```bash
devops install --help
```

### Install a group

Use the `--group` flag when `WHICH` refers to a group name:

```bash
devops install --help
```

### Choose interactively

Use the interactive picker:

```bash
devops install --interactive --help
```

---

## Available groups

Here are the available groups as currently defined by the installer:

<table>
  <thead>
    <tr>
      <th>Group</th>
      <th>AppsBundled</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>sysabc</code></td>
      <td>sysabc</td>
    </tr>
    <tr>
      <td><code>shell</code></td>
      <td>zellij | mprocs | mcfly | atuin | starship | gotty | ttyd | cb</td>
    </tr>
    <tr>
      <td><code>search</code></td>
      <td>nerdfont | fd | fzf | tv | broot | rg | rga | ugrep | ouch | pistol | bat | viu | yazi | tere | lsd | zoxide | diskonaut | dua | dust | cpz | rmz</td>
    </tr>
    <tr>
      <td><code>sys-monitor</code></td>
      <td>btop | btm | ntop | procs | cpufetch | fastfetch</td>
    </tr>
    <tr>
      <td><code>code-analysis</code></td>
      <td>nano | lazygit | onefetch | gitcs | lazydocker | hyperfine | kondo | tokei | navi | tealdeer | gitui | delta | gh | watchexec | jq</td>
    </tr>
    <tr>
      <td><code>termabc</code></td>
      <td>
        nano | lazygit | onefetch | gitcs | lazydocker | hyperfine | kondo | tokei | navi | tealdeer | gitui | delta | gh | watchexec | jq<br>
        btop | btm | ntop | procs | cpufetch | fastfetch<br>
        zellij | mprocs | mcfly | atuin | starship | gotty | ttyd | cb<br>
        nerdfont | fd | fzf | tv | broot | rg | rga | ugrep | ouch | pistol | bat | viu | yazi | tere | lsd | zoxide | diskonaut | dua | dust | cpz | rmz
      </td>
    </tr>
    <tr>
      <td><code>dev</code></td>
      <td>
        alacritty | wezterm | warp | vtm | edex-ui | extraterm | nushell<br>
        brave | bypass-paywalls-chrome | browsh | carbonyl | code | hx<br>
        rainfrog | lazysql | dblab | usql | harlequin | sqlit | duckdb | postgresql-client | sqlite3 | redis-cli | dbgate | dbeaver | sqliteBrowser | pgadmin | pgweb<br>
        ytui-music | youtube-tui | termusic | kronos | OBS Background removal<br>
        ngrok | devtunnel | cloudflared | forward-cli | ffsend | portal | qrcp | termscp | filebrowser | qr | qrscan | sharewifi | share-wifi | easy-sharing | ezshare | restic | syncthing | cloudreve | ots<br>
        devcontainer | rust-analyzer | evcxr | geckodriver | git | m365<br>
        nano | lazygit | onefetch | gitcs | lazydocker | hyperfine | kondo | tokei | navi | tealdeer | gitui | delta | gh | watchexec | jq<br>
        espanso | bitwarden | openpomodoro-cli | rustdesk | mermaid-cli | html2markdown | pandoc | patat | marp | presenterm | glow | gum<br>
        lolcatjs | figlet-cli | boxes | cowsay
      </td>
    </tr>
    <tr>
      <td><code>dev-utils</code></td>
      <td>devcontainer | rust-analyzer | evcxr | geckodriver | git | m365</td>
    </tr>
    <tr>
      <td><code>eye</code></td>
      <td>lolcatjs | figlet-cli | boxes | cowsay</td>
    </tr>
    <tr>
      <td><code>agents</code></td>
      <td>aider | aoe | aichat | copilot | gemini | crush | opencode-ai | chatgpt | mods | q | qwen-code | cursor-cli | droid | kilocode | cline | auggie | agentofempires | agent-deck | agenthand</td>
    </tr>
    <tr>
      <td><code>terminal</code></td>
      <td>alacritty | wezterm | warp | vtm | edex-ui | extraterm | nushell</td>
    </tr>
    <tr>
      <td><code>browsers</code></td>
      <td>brave | bypass-paywalls-chrome | browsh | carbonyl</td>
    </tr>
    <tr>
      <td><code>editors</code></td>
      <td>code | hx</td>
    </tr>
    <tr>
      <td><code>db-all</code></td>
      <td>rainfrog | lazysql | dblab | usql | harlequin | sqlit | duckdb | postgresql-client | sqlite3 | redis-cli | dbgate | dbeaver | sqliteBrowser | pgadmin | pgweb</td>
    </tr>
    <tr>
      <td><code>db-cli</code></td>
      <td>duckdb | postgresql-client | sqlite3 | redis-cli</td>
    </tr>
    <tr>
      <td><code>db-desktop</code></td>
      <td>dbgate | dbeaver | sqliteBrowser</td>
    </tr>
    <tr>
      <td><code>db-web</code></td>
      <td>pgadmin | pgweb</td>
    </tr>
    <tr>
      <td><code>db-tui</code></td>
      <td>rainfrog | lazysql | dblab | usql | harlequin | sqlit</td>
    </tr>
    <tr>
      <td><code>media</code></td>
      <td>ytui-music | youtube-tui | termusic | kronos | OBS Background removal</td>
    </tr>
    <tr>
      <td><code>gui</code></td>
      <td>brave | code | zoomit | wezterm | mouse-without-borders</td>
    </tr>
    <tr>
      <td><code>nw</code></td>
      <td>bandwhich | ipinfo | sniffnet | topgrade | speedtest | rclone</td>
    </tr>
    <tr>
      <td><code>file-sharing</code></td>
      <td>ngrok | devtunnel | cloudflared | forward-cli | ffsend | portal | qrcp | termscp | filebrowser | qr | qrscan | sharewifi | share-wifi | easy-sharing | ezshare | restic | syncthing | cloudreve | ots</td>
    </tr>
    <tr>
      <td><code>productivity</code></td>
      <td>espanso | bitwarden | openpomodoro-cli | rustdesk | mermaid-cli | html2markdown | pandoc | patat | marp | presenterm | glow | gum</td>
    </tr>
  </tbody>
</table>
