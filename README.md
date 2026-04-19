<div align="center">

<h1>🗜 StackOps</h1>

<strong>Bootstrap and maintain a development machine from one CLI.</strong>

<p>
  <a href="https://thisismygitrepo.github.io/stackops/"><img alt="Docs" src="https://img.shields.io/badge/docs-online-2f6f6f"></a>
  <a href="https://pypi.org/project/stackops/"><img alt="PyPI package" src="https://img.shields.io/pypi/v/stackops?color=2f6f6f"></a>
  <img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776AB">
  <img alt="Installed with uv" src="https://img.shields.io/badge/install-uv-f05d23">
</p>

</div>

StackOps is a cross-platform CLI for bootstrapping and maintaining a development machine. It groups package installation, config syncing, data syncing, session automation, and helper utilities into one install.

See the [online docs](https://thisismygitrepo.github.io/stackops/) for full usage and reference material.

## Install

Choose your platform and run the commands in order.

<p>
  <a href="#install-linux"><kbd>Linux</kbd></a>
  <a href="#install-macos"><kbd>macOS</kbd></a>
  <a href="#install-windows-powershell"><kbd>Windows PowerShell</kbd></a>
</p>

<h3 id="install-linux">Linux</h3>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --upgrade --python 3.14 stackops
stackops --help
```

<h3 id="install-macos">macOS</h3>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --upgrade --python 3.14 stackops
stackops --help
```

<h3 id="install-windows-powershell">Windows PowerShell</h3>

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install --upgrade --python 3.14 stackops
stackops --help
```

If `uv` is not found after installing it, open a new terminal and run the install command again.

## Quick Init

Run these once StackOps is installed:

<p>
  <a href="#quick-init-linux"><kbd>Linux</kbd></a>
  <a href="#quick-init-macos"><kbd>macOS</kbd></a>
  <a href="#quick-init-windows-powershell"><kbd>Windows PowerShell</kbd></a>
</p>

<h3 id="quick-init-linux">Linux</h3>

```bash
devops install --group sysabc
devops config copy-assets all
devops config sync down \
  --sensitivity public \
  --method copy \
  --on-conflict overwrite-default-path \
  --which all
devops config terminal config-shell --which default
devops install --group termabc
```

<h3 id="quick-init-macos">macOS</h3>

```bash
devops install --group sysabc
devops config copy-assets all
devops config sync down \
  --sensitivity public \
  --method copy \
  --on-conflict overwrite-default-path \
  --which all
devops config terminal config-shell --which default
devops install --group termabc
```

<h3 id="quick-init-windows-powershell">Windows PowerShell</h3>

```powershell
devops install --group sysabc
devops config copy-assets all
devops config sync down `
  --sensitivity public `
  --method copy `
  --on-conflict overwrite-default-path `
  --which all
devops config terminal config-shell --which default
devops install --group termabc
```

## CLI Map

<table>
  <thead>
    <tr>
      <th>Command</th>
      <th>Use it for</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>devops</code></td>
      <td>Machine bootstrap, package groups, and config workflows.</td>
    </tr>
    <tr>
      <td><code>stackops</code></td>
      <td>Main StackOps entrypoint and help surface.</td>
    </tr>
    <tr>
      <td><code>cloud</code></td>
      <td>Cloud sync and remote storage helpers.</td>
    </tr>
    <tr>
      <td><code>terminal</code></td>
      <td>Terminal and shell configuration helpers.</td>
    </tr>
    <tr>
      <td><code>agents</code></td>
      <td>Agent setup and automation commands.</td>
    </tr>
  </tbody>
</table>

## Author

Alex Al-Saffar. [email](mailto:programmer@usa.com)

## Contributor

Ruby Chan. [email](mailto:ruby.chan@sa.gov.au)
