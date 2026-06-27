# agent-browser

Verified: 2026-04-21.

`agent-browser` is the direct CLI path for browser automation. StackOps installs the npm package through the normal installer catalog and adds the Vercel skill with:

```bash
bunx skills@latest add vercel-labs/agent-browser --yes
```

Install it from StackOps:

```bash
stackops agents browser install-tech --which agent-browser
```

Launch a browser with a dedicated CDP profile. By default, StackOps opens the shared `stackops-browser` tmux session and creates a qualified browser endpoint window:

```bash
stackops agents browser launch-browser --browser chrome --port 9331 --profile agent-browser
```

Expose a browser on the LAN when the other computer is trusted and reachable. This adds a qualified relay window in the same tmux session:

```bash
stackops agents browser launch-browser --browser chrome --port 9331 --profile agent-browser --lan
agent-browser connect http://OTHER_COMPUTER_IP:9331
```

Use the background process launch mode only when you deliberately do not want tmux ownership:

```bash
stackops agents browser launch-browser --browser chrome --port 9331 --profile agent-browser --detached
```

Inspect active StackOps browser tmux sessions:

```bash
stackops agents browser status
```

Use the launched browser:

```bash
agent-browser open https://example.com --cdp 9331
agent-browser snapshot -i
agent-browser click @e1
agent-browser fill @e2 "value"
```

Keep CDP on localhost unless the machine is on a trusted network. If `--lan` is used, StackOps keeps Chrome on a localhost-only CDP port and exposes the requested port through a relay on `0.0.0.0`. No SSH tunnel is needed when the agent machine can reach that LAN endpoint. Any host that can reach the exposed port can control the browser.
