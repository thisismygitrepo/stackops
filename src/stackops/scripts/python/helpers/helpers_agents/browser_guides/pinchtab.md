# PinchTab

Verified from https://github.com/pinchtab/pinchtab and https://pinchtab.com/docs/ on 2026-07-29.

PinchTab is a local browser control server with a CLI and HTTP API. StackOps installs the current release binary from the normal installer catalog and adds the official `pinchtab` agent skill with:

```bash
bunx skills@latest add pinchtab/pinchtab --skill pinchtab --yes
```

Install it from StackOps:

```bash
stackops agents browser install-tech --which pinchtab
```

For normal local use, install the user-level daemon once:

```bash
pinchtab daemon install
pinchtab health
```

Alternatively, run the server in the foreground:

```bash
pinchtab server
```

Use the browser through the CLI:

```bash
pinchtab nav https://example.com --snap
pinchtab snap -i -c
pinchtab click e5
pinchtab fill e3 "value"
pinchtab text
```

PinchTab listens on `127.0.0.1:9867` by default. Keep its dashboard, HTTP API, MCP server, and CLI integrations on loopback unless the deployment has explicit authentication, TLS, and network controls; they are privileged browser-control surfaces.
