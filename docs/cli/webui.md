# webui

`stackops webui` starts a local web server for StackOps commands, dashboards, and terminals, then opens it in the browser. It is a command of the `stackops` wrapper only (hidden alias `stackops w`); there is no standalone `webui` entrypoint.

---

## Usage

```bash
stackops webui [OPTIONS]
```

---

## Options

| Option | Short | Description |
| --- | --- | --- |
| `--host` | `-H` | Interface to listen on. Defaults to `127.0.0.1`; keep the loopback default unless you trust the network |
| `--port` | `-p` | Port to listen on, `0` to `65535`; `0` picks a free port. Defaults to `8420` when it is free, otherwise a free port |
| `--no-browser` | `-n` | Print the access link without opening it in the browser |

---

## Current launch behavior

- The server runs in a separate `uv run --no-project` process on the current interpreter, with `starlette` and `uvicorn` (plus `pywinpty` on Windows) added through `--with`.
- Commands started from the page run through the `stackops` executable next to that interpreter; the directory `stackops webui` was started in is the page's starting working directory.
- The command prints an access link of the form `http://<host>:<port>/?token=...`. The link carries the session's access token and changes on every start. The first visit stores the token in a cookie and redirects to `/`; a request without it gets an "access link needed" page.
- `/` serves the app view and `/dev` the developer view.
- The browser is opened only from an interactive terminal and without `--no-browser`.
- When `--port` is omitted and `8420` is in use, a free port is used instead. An explicit `--port` that cannot be bound is an error; choose another port or `--port 0`.
- `--host 0.0.0.0` also prints a link for other devices on the network when a LAN address is found. Any non-loopback host prints a warning: anyone who can reach the port and has the link can run commands on this machine, over plain HTTP.
- `Ctrl+C` stops the server and the commands it is running.

---

## Examples

```bash
# Start on 127.0.0.1:8420 and open the browser
stackops webui

# Use the short alias, a free port, and only print the link
stackops w --port 0 --no-browser

# Listen on all interfaces of a trusted network
stackops webui --host 0.0.0.0 --port 8420
```

---

## Getting help

```bash
stackops webui --help
```
