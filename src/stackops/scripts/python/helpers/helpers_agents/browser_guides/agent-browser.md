# agent-browser

Verified: 2026-04-21.

`agent-browser` is the direct CLI path for browser automation. StackOps installs the npm package through the normal installer catalog and adds the Vercel skill with:

```bash
bunx skills@latest add vercel-labs/agent-browser
```

Install it from StackOps:

```bash
stackops agents browser install-tech --which agent-browser
```

Launch a browser with a dedicated CDP profile:

```bash
stackops agents browser launch-browser --browser chrome --port 9331 --profile agent-browser
```

Use the launched browser:

```bash
agent-browser open https://example.com --cdp 9331
agent-browser snapshot -i
agent-browser click @e1
agent-browser fill @e2 "value"
```

Keep CDP on localhost unless the machine is on a trusted network. If `--lan` is used, any host that can reach the port can control the browser.
