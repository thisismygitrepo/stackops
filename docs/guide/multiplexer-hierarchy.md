# Multiplexer Hierarchies: tmux, herdr, zellij, tuios

Each tool on its own. Versions checked: tmux 3.7b, herdr 0.9.5, zellij 0.44.0, tuios 0.10.1.

## tmux

```text
server                      one per socket (tmux -L name)
└── session                 a named project, what a client attaches to
    └── window              a full-screen page, listed in the status bar
        └── pane            a terminal in a split
```

| Level | Meaning | List it |
|---|---|---|
| server | The background process that survives detach. Holds every session on its socket. | `tmux ls` (per socket) |
| session | A named collection of windows. A client is attached to exactly one session at a time. | `tmux ls` |
| window | One full-screen layout of panes. | `tmux list-windows` |
| pane | One terminal. | `tmux list-panes` |

IDs: `$0` (session), `@3` (window), `%7` (pane).
Attach / detach: `tmux new -As name` / `prefix d`. Default prefix `ctrl+b`.

## herdr

```text
session                     a named persistent server (herdr --session name)
└── workspace               a project, listed in the sidebar
    └── tab                 a full-screen page of panes
        └── pane            a terminal in a split
            └── agent       (optional) a coding agent herdr recognised in the pane
```

| Level | Meaning | List it |
|---|---|---|
| session | A whole independent herdr server with its own socket and state. Sessions share nothing. Plain `herdr` uses `default`. | `herdr session list` |
| workspace | A project. All workspaces of the session show in the sidebar, so you switch between them without detaching. Can be backed by a git worktree. | `herdr workspace list` |
| tab | One full-screen page of panes inside a workspace. | `herdr tab list` |
| pane | One terminal. Exists whether or not an agent runs in it. | `herdr pane list` |
| agent | A coding agent detected in a pane, tracked as `idle`, `working`, `blocked`, `done` or `unknown`. | `herdr agent list` |

IDs: `w1` (workspace), `w1:t1` (tab), `w1:p1` (pane). Opaque, never reused after a close.
Attach / detach: `herdr --session name` / `prefix q`. Default prefix `ctrl+b`.
Extras: a socket API (`herdr workspace|tab|pane|agent ...` returns JSON), git worktree workspaces (`herdr worktree create`).

## zellij

```text
session                     a named session; each one is its own server process
└── tab                     a full-screen page of panes
    └── pane                a terminal in a split
        ├── floating pane   hovers over the tiled layout
        ├── stacked pane    several panes collapsed into one slot
        └── plugin pane     a WASM plugin (status bar, session manager, ...)
```

| Level | Meaning | List it |
|---|---|---|
| session | The persistent unit. Detached sessions keep running and can be resurrected after exit. | `zellij ls` |
| tab | One full-screen page of panes. | `zellij action list-tabs` |
| pane | One terminal, plugin or floating terminal. | `zellij action list-panes` |

IDs: tabs have stable IDs; panes are `terminal_<id>` or `plugin_<id>`.
Attach / detach: `zellij attach -c name` / `ctrl+o d`.
Keys are modal: `ctrl+p` pane, `ctrl+t` tab, `ctrl+o` session, and so on.
Extras: KDL layouts (`zellij --layout`), floating and stacked panes, plugins.

## tuios

```text
daemon                      one per socket (tuios --server name)
└── space                   (optional) a named group of related sessions
    └── session             a named project, what a client attaches to
        └── workspace       a numbered page of windows
            └── window      one terminal; owns exactly one pane
                            (tiled, floating, or a popup)
```

| Level | Meaning | List it |
|---|---|---|
| daemon | The background process holding all sessions on its socket. Started on demand; a named daemon (`--server`) has its own sessions. | `tuios ls` |
| space | A label that groups related sessions together in `tuios ls` and the sidebar. It exists only while a session is filed under it (`tuios set-session-space`). | `tuios ls` |
| session | A named project. Persists when you detach. | `tuios ls` |
| workspace | One numbered page of windows within a session. | `tuios list-workspaces` |
| window | One terminal. Can be tiled, floating or a popup, and can host an agent whose state it reports. | `tuios list-windows` |

IDs: a window takes `-w` as a uuid, an index, an exact name or a unique id prefix.
Attach / detach: `tuios new name` / `tuios attach name`.
Extras: window-manager features (tiling, floating windows, dock), agent states with an Inbox, a control protocol (`send-keys`, `capture-pane`, `wait-for`, `run`).
