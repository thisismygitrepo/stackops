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

`stackops.cluster.sessions_managers.session_conflict` defines the shared conflict planner. `build_session_launch_plan(requested_session_names, backend, on_conflict)` returns one `SessionLaunchPlan` per requested name; `backend` is `tmux`, `herdr`, `tuios`, or `zellij`.

### Supported Actions

| Action | Meaning |
| --- | --- |
| `error` | Fail if a requested session already exists or if two requested layouts target the same name |
| `restart` | Reuse the requested name and restart an existing session when necessary; two requested layouts with the same name still fail |
| `rename` | Keep the requested name as a base and allocate `name_1`, `name_2`, and so on |
| `skip` | Keep existing sessions and skip conflicting launches |
| `mergeOverwrite` | Keep the requested session name and overwrite matching tabs where supported |
| `mergeSkip` | Keep the requested session name and add only missing tabs where supported |

The failing cases raise `SessionConflictError`, a `ValueError` subclass.

The two merge actions are valid for the `tmux`, `tuios`, and `zellij` backends; requesting them for `herdr` raises `SessionConflictError`. For tmux, merge behavior is implemented by generating merge commands for an existing session.

---

## tmux Local

`TmuxLocalManager` requires `session_name_prefix` and `exit_mode` constructor arguments. Pass `None` as the prefix to use each layout name directly; otherwise the session is named `{prefix}_{layoutName}`. Spaces in the layout name become underscores either way.

`exit_mode` is a `SessionExitMode`: `backToShell` leaves an interactive shell open after the command ends, `terminate` waits when the command ends and offers to rerun it or close the pane, and `killWindow` closes the pane as soon as the command ends.

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

`check_all_sessions_status()` returns one report per session with the keys `session_status`, `commands_status`, and `summary`. Only the session itself is checked: `session_status` says whether tmux is running and whether the session exists. The commands are not inspected, so every entry of `commands_status` has `status: "unknown"` and `running: False`, `summary["running_commands"]` is always `0`, and `summary["session_healthy"]` repeats `session_exists`. `get_global_summary()` and `print_status_report()` add up the same numbers, and `TmuxLayoutGenerator.get_status_report()` behaves the same way for one layout.

tmux is also the backend where merge conflict actions produce merge commands instead of only rename-or-restart plans.

---

## Monitoring And Reporting Helpers

Representative utility modules include:

- `stackops.cluster.sessions_managers.status_reporting`
- `stackops.cluster.sessions_managers.monitoring_types`
- `stackops.cluster.sessions_managers.session_launch_table`
- `stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_status`

These modules power the status summaries and launch tables produced by the manager classes rather than replacing them. The summaries tell whether each session exists; `CommandStatus` has per-command fields (`status`, `running`, `processes`), but the tmux manager fills them with the fixed placeholder values described under tmux Local above.

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

## Monitoring Types

::: stackops.cluster.sessions_managers.monitoring_types
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Session Launch Table

::: stackops.cluster.sessions_managers.session_launch_table
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
