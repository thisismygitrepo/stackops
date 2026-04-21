# Chrome DevTools MCP

Verified from https://github.com/ChromeDevTools/chrome-devtools-mcp on 2026-04-21.

Chrome DevTools MCP lets an MCP client control and inspect a live Chrome browser with DevTools-level tools for navigation, input, console messages, screenshots, snapshots, network inspection, performance traces, Lighthouse, and memory snapshots.

Requirements from the upstream project:

- Node.js v20.19 or newer
- Current stable Google Chrome or newer
- npm

StackOps catalog entries:

```bash
stackops agents add-mcp chrome-devtools --agent codex --scope local
stackops agents add-mcp chrome-devtools-browser-url --agent codex --scope local
```

The standard MCP config is in `chrome-devtools-mcp.mcp.json`. It lets the MCP server start Chrome on demand with an explicit StackOps profile. When StackOps writes this file, `{home}` is replaced with your home directory.

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "bunx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--user-data-dir={home}/data/browsers-profiles/mcp/chrome-devtools"
      ]
    }
  }
}
```

For a running browser, use `chrome-devtools-mcp-browser-url.mcp.json` after starting Chrome through StackOps with a custom profile. StackOps passes `--user-data-dir` when launching the browser:

```bash
stackops agents browser launch-browser --browser chrome --port 9222 --profile chrome-devtools-mcp
```

The MCP args must point at the same port:

```json
{
  "mcpServers": {
    "chrome-devtools-browser-url": {
      "command": "bunx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--browser-url=http://127.0.0.1:9222"
      ]
    }
  }
}
```

Chrome 144 and newer also support `--autoConnect` after remote debugging is enabled from `chrome://inspect/#remote-debugging`. Use that only when the Chrome instance was started from an isolated StackOps profile.

Operational notes:

- Chrome DevTools MCP officially supports Google Chrome and Chrome for Testing. Other Chromium browsers may work, but they are not the support target.
- StackOps catalog installation uses an explicit profile under `{home}/data/browsers-profiles/mcp/chrome-devtools`.
- StackOps attach installation expects the browser endpoint to come from `stackops agents browser launch-browser`, which always passes a custom `--user-data-dir`.
- The MCP server can inspect and modify browser content. Do not run it against sensitive browsing sessions.
- Remote debugging exposes browser control on the selected host and port. Keep it on `127.0.0.1` unless you deliberately need LAN access.
- Usage statistics are enabled by default upstream. Use `--no-usage-statistics` or `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS` if that is not acceptable.
- On Windows, Codex may need `command = "cmd"`, args starting with `"/c"`, and environment values for `SystemRoot` and `PROGRAMFILES`.
