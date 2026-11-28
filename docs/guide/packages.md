# Package Management

The current package installation workflow is centered on `devops software install`.

---

## Overview

StackOps keeps package installation behind one command surface:

```bash
devops software install --help
```

The live help currently describes `devops software install [which]` as the supported package entrypoint. The same `devops software` group also has `check`, `explore`, `list`, and `uninstall`.

---

## Installation modes

Current help shows three main ways to use `devops software install`:

### Install named programs

Pass `which` as a comma-separated list of program names:

```bash
devops software install --help
```

### Install a group

Use the `--group` flag when `which` holds group names (comma-separated):

```bash
devops software install --help
```

### Choose interactively

Use the interactive picker:

```bash
devops software install --interactive --help
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
      <td>nerdfont | tuios | mcfly | starship</td>
    </tr>
    <tr>
      <td><code>search</code></td>
      <td>yazi | fd | fzf | tv | rg | rga | ugrep | ouch | pistol | bat | viu | superfile | tere | lsd | zoxide | diskonaut | dua | dust | pdu | cpz | rmz</td>
    </tr>
    <tr>
      <td><code>sys-monitor</code></td>
      <td>btop | btm | ntop | procs | cpufetch | fastfetch | pstop</td>
    </tr>
    <tr>
      <td><code>code-analysis</code></td>
      <td>nano | agent-git | lazygit | onefetch | gitcs | lazydocker | hyperfine | kondo | tokei | navi | tealdeer | gitui | delta | gh | watchexec | jq</td>
    </tr>
    <tr>
      <td><code>termabc</code></td>
      <td>
        yazi | fd | fzf | tv | rg | rga | ugrep | ouch | pistol | bat | viu | superfile | tere | lsd | zoxide | diskonaut | dua | dust | pdu | cpz | rmz<br>
        nerdfont | tuios | mcfly | starship<br>
        nano | agent-git | lazygit | onefetch | gitcs | lazydocker | hyperfine | kondo | tokei | navi | tealdeer | gitui | delta | gh | watchexec | jq<br>
        btop | btm | ntop | procs | cpufetch | fastfetch | pstop
      </td>
    </tr>
    <tr>
      <td><code>dev</code></td>
      <td>
        alacritty | ghostty | wezterm | warp-terminal | vtm | edex-ui | extraterm | nu<br>
        brave | bypass-paywalls-chrome | browsh | carbonyl<br>
        code | hx | zed<br>
        rainfrog | lazysql | dblab | usql | harlequin | sqlit | dolt | duckdb | postgresql-client | sqlite3 | redis-cli | dbgate | dbeaver | sqliteBrowser | pgweb<br>
        ytui-music | youtube-tui | termusic | rmpc | kronos | OBS Background removal<br>
        ngrok | devtunnel | cloudflared | forward-cli | ffsend | portal | qrcp | termscp | filebrowser | qr | qrscan | sharewifi | easy-sharing | ezshare | restic | syncthing | cloudreve | ots<br>
        devcontainer | rust-analyzer | evcxr | geckodriver | git | m365<br>
        nano | agent-git | lazygit | onefetch | gitcs | lazydocker | hyperfine | kondo | tokei | navi | tealdeer | gitui | delta | gh | watchexec | jq<br>
        espanso | bw | openpomodoro-cli | rustdesk | mermaid-cli | html2markdown | pandoc | patat | marp | presenterm | glow | gum<br>
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
      <td>aider | agent-git | aoe | aichat | copilot | cortex | antigravity | minimax-code | deepseek-harness | crush | opencode | deer-flow | forge | headroom | hermes | mods | oz | q | qodercli | qwen-code | cursor-cli | droid | maki | muse | prime-agent | dmux | pi | omp | orca | kilocode | cline | auggie | agent-deck | beads | beads_viewer | gastown</td>
    </tr>
    <tr>
      <td><code>terminal</code></td>
      <td>alacritty | ghostty | wezterm | warp-terminal | vtm | edex-ui | extraterm | nu</td>
    </tr>
    <tr>
      <td><code>browsers</code></td>
      <td>brave | bypass-paywalls-chrome | browsh | carbonyl</td>
    </tr>
    <tr>
      <td><code>editors</code></td>
      <td>code | hx | zed</td>
    </tr>
    <tr>
      <td><code>db-all</code></td>
      <td>rainfrog | lazysql | dblab | usql | harlequin | sqlit | dolt | duckdb | postgresql-client | sqlite3 | redis-cli | dbgate | dbeaver | sqliteBrowser | pgweb</td>
    </tr>
    <tr>
      <td><code>db-cli</code></td>
      <td>dolt | duckdb | postgresql-client | sqlite3 | redis-cli</td>
    </tr>
    <tr>
      <td><code>db-desktop</code></td>
      <td>dbgate | dbeaver | sqliteBrowser</td>
    </tr>
    <tr>
      <td><code>db-web</code></td>
      <td>pgweb</td>
    </tr>
    <tr>
      <td><code>db-tui</code></td>
      <td>rainfrog | lazysql | dblab | usql | harlequin | sqlit</td>
    </tr>
    <tr>
      <td><code>media</code></td>
      <td>ytui-music | youtube-tui | termusic | rmpc | kronos | OBS Background removal</td>
    </tr>
    <tr>
      <td><code>gui</code></td>
      <td>brave | chatgpt | wezterm</td>
    </tr>
    <tr>
      <td><code>nw</code></td>
      <td>bandwhich | psnet | ipinfo | sniffnet | topgrade | speedtest | rclone</td>
    </tr>
    <tr>
      <td><code>file-sharing</code></td>
      <td>ngrok | devtunnel | cloudflared | forward-cli | ffsend | portal | qrcp | termscp | filebrowser | qr | qrscan | sharewifi | easy-sharing | ezshare | restic | syncthing | cloudreve | ots</td>
    </tr>
    <tr>
      <td><code>productivity</code></td>
      <td>espanso | bw | openpomodoro-cli | rustdesk | mermaid-cli | html2markdown | pandoc | patat | marp | presenterm | glow | gum</td>
    </tr>
  </tbody>
</table>
