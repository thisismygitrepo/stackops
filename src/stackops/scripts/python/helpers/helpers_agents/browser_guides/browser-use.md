# Browser Use

Verified from https://github.com/browser-use/browser-use on 2026-08-21.

Browser Use provides a Python CLI and bundled skill for agent-driven browser automation. StackOps follows the upstream setup contract: install or upgrade the tool with uv on Python 3.12, then register the packaged skill for the selected agent without reinstalling the tool.

```bash
uv tool install --python 3.12 --upgrade --force browser-use
browser-use skill install --target <agent> --no-install
```

Install it through StackOps:

```bash
stackops agents browser install-tech --which browser-use
```

Check the CLI, browser connection, and daemon:

```bash
browser-use --doctor
```

The CLI executes Python from standard input in a persistent browser session:

```bash
browser-use <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

Inspect the installed agent instructions and current helper interface with:

```bash
browser-use skill show
```
