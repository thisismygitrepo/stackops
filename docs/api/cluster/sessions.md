# Sessions

The session-manager layer takes `LayoutConfig` objects and turns them into running terminal sessions. The shared pieces are:

- session-name conflict planning
- backend-specific layout launchers
- attach, status, and monitoring helpers

---

## Supported Managers

| Manager | Module path | What it manages |
| --- | --- | --- |
| `TmuxLocalManager` | `stackops.cluster.sessions_managers.tmux.tmux_local_manager` | Local tmux sessions generated from `list[LayoutConfig]` |

---

## Conflict Policies

`stackops.cluster.sessions_managers.session_conflict` defines the shared conflict planner.

### Supported Actions

| Action | Meaning |
| --- | --- |
| `error` | Fail if a requested session already exists or if two requested layouts target the same name |
| `restart` | Reuse the requested name and restart an existing session when necessary |
| `rename` | Keep the requested name as a base and allocate `name_1`, `name_2`, and so on |
| `skip` | Keep existing sessions and skip conflicting launches |
| `mergeOverwrite` | Keep the requested tmux session name and overwrite matching windows where supported |
| `mergeSkip` | Keep the requested tmux session name and add only missing windows where supported |

The two merge actions are valid for the `tmux` backend. For tmux, merge behavior is implemented by generating merge commands for an existing session.

---

## tmux Local

`TmuxLocalManager` requires `session_name_prefix` and `exit_mode` constructor arguments. Pass `None` as the prefix to use each layout name directly:

```python
from stackops.cluster.sessions_managers.tmux.tmux_local_manager import TmuxLocalManager

manager = TmuxLocalManager(
    session_layouts=[layout],
    session_name_prefix="ops",
    exit_mode="backToShell",
)

manager.start_all_sessions(on_conflict="rename")
print(manager.attach_to_session(None))
report = manager.check_all_sessions_status()
```

tmux is also the backend where merge conflict actions produce merge commands instead of only rename-or-restart plans.

---

## Monitoring And Reporting Helpers

Representative utility modules include:

- `stackops.cluster.sessions_managers.status_reporting`
- `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_status`

These modules power the status summaries returned by the manager classes rather than replacing them.

---

## See Also

- [Layouts](layouts.md) for `LayoutConfig`, layout serialization, and tab generation
- [Remote execution and networking](remote.md) for remote-job flows that feed these backends
- [CLI Terminal Reference](../../cli/terminal.md) for the end-user command layer

---

## API Reference

## Conflict Planning

::: stackops.cluster.sessions_managers.session_conflict
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Session Exit Mode

::: stackops.cluster.sessions_managers.session_exit_mode
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Status Reporting

::: stackops.cluster.sessions_managers.status_reporting
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Enhanced Command Runner

::: stackops.cluster.sessions_managers.helpers.enhanced_command_runner
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## tmux Local Manager

::: stackops.cluster.sessions_managers.tmux.tmux_local_manager
    options:
      show_root_heading: true
      show_source: false
      members_order: source
