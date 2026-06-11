# playwright-cli

`playwright-cli` is the direct Playwright command-line interface for coding agents. It is the token-efficient path for agents that prefer shell commands and local artifacts over MCP tool schemas.

StackOps installs the npm package and Playwright agent skills with:

```bash
bun install -g @playwright/cli
playwright-cli install --skills
```

Install through StackOps:

```bash
stackops agents browser install-tech --which playwright-cli
```

Use it when an agent should drive a browser from terminal commands:

```bash
playwright-cli --help
playwright-cli open https://example.com
playwright-cli snapshot
```

Use `playwright-mcp` instead when the agent client should attach through MCP and keep browser automation state inside the MCP server.
