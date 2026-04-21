# Playwright MCP

Verified from https://github.com/microsoft/playwright-mcp and https://github.com/microsoft/playwright-mcp/tree/main/packages/extension on 2026-04-21.

Playwright MCP exposes browser automation through MCP. It supports accessibility snapshots, input, navigation, tabs, optional vision/PDF/devtools capabilities, and profile modes for persistent, isolated, extension-backed, or CDP-backed browser control.

StackOps catalog entries:

```bash
stackops agents add-mcp playwright --agent codex --scope local
stackops agents add-mcp playwright-extension --agent codex --scope local
stackops agents add-mcp playwright-cdp --agent codex --scope local
```

The standard config is in `playwright-mcp.mcp.json`. When StackOps writes this file, `{home}` is replaced with your home directory.

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "-y",
        "@playwright/mcp@latest",
        "--user-data-dir",
        "{home}/data/browsers-profiles/mcp/playwright"
      ]
    }
  }
}
```

Profile modes:

- Persistent profile: StackOps uses `--user-data-dir` explicitly, under `{home}/data/browsers-profiles/mcp/playwright`.
- Browser extension: use `--extension` to attach to existing Chrome, Edge, or Chromium tabs. Install the Playwright Extension from the Chrome Web Store into a StackOps-launched custom profile, then use `playwright-mcp-extension.mcp.json`. The extension UI can provide `PLAYWRIGHT_MCP_EXTENSION_TOKEN` for automatic approval.
- Dedicated browser profile: use `playwright-mcp-user-data-dir.mcp.json` and edit the profile and executable paths. For Brave or another Chromium browser, set `--executable-path` explicitly.
- CDP endpoint: launch a browser with remote debugging through StackOps, then use `playwright-mcp-cdp.mcp.json`. StackOps passes `--user-data-dir` when launching the browser.
- Isolated state: use `playwright-mcp-storage-state.mcp.json` with `--isolated` and a storage state JSON file.

Start a browser for the CDP mode:

```bash
stackops agents browser launch-browser --browser chrome --port 9222 --profile playwright-mcp
```

Edit the CDP config if you choose a different port:

```json
{
  "mcpServers": {
    "playwright-cdp": {
      "command": "npx",
      "args": [
        "-y",
        "@playwright/mcp@latest",
        "--cdp-endpoint",
        "http://127.0.0.1:9222"
      ]
    }
  }
}
```

Operational notes:

- Use extension mode only with a browser session you deliberately opened from a StackOps custom profile.
- Prefer a dedicated `--user-data-dir` profile when you want persistent state without granting access to your normal profile.
- Do not point automation at a profile that is already open in a normal browser process.
- Remote debugging exposes browser control on the selected host and port. Keep it on `127.0.0.1` unless you deliberately need LAN access.
