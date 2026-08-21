# omp (Oh My Pi)

Verified from https://github.com/can1357/oh-my-pi on 2026-08-21.

`omp` is a terminal coding agent built on the pi coding-agent harness. Unlike the other entries here it is an agent, not a browser CLI: its Puppeteer `browser` tool ships built in and enabled by default, but it must be pointed at a browser before it can drive one.

StackOps installs it from the normal installer catalog:

```bash
stackops agents browser install-tech --which omp
```

The install writes `omp-browser-cdp.yml` into this directory, a config overlay that attaches the omp browser tool to a StackOps CDP endpoint instead of launching its own browser.

Launch the endpoint with a dedicated profile:

```bash
stackops agents browser launch-browser --browser chrome --port 9331 --profile omp
```

Start omp with the overlay:

```bash
omp --config {home}/code/agents/browser/omp/omp-browser-cdp.yml
```

To make the attach permanent across sessions, set it once:

```bash
omp config set browser.cdpUrl http://127.0.0.1:9331
```

Expose the endpoint on the LAN when the other computer is trusted and reachable; point the remote omp at the relay instead:

```bash
stackops agents browser launch-browser --browser chrome --port 9331 --profile omp --lan
omp config set browser.cdpUrl http://OTHER_COMPUTER_IP:9331
```

To drive your own Chrome tabs rather than a StackOps profile, install the relay extension once and enable relay mode (relay takes precedence over the CDP URL):

```bash
omp browser-relay install
omp config set browser.relay true
```
