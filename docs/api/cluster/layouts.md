# Layouts

The layout APIs turn Python intent into terminal structure. They describe tabs, generate commands, split oversized layouts, and hand the result to tmux or other session backends.

This is the API surface behind many "fan out these jobs into tabs" workflows.

---

## Layout schema

The foundation is the typed schema in `machineconfig.utils.schemas.layouts.layout_types`.

### Core types

| Type | Fields |
| --- | --- |
| `TabConfig` | `tabName`, `startDir`, `command`, optional `tabWeight` |
| `LayoutConfig` | `layoutName`, `layoutTabs` |
| `LayoutsFile` | `version`, `layouts` |

Two utility helpers round out the schema:

- `serialize_layouts_to_file()` writes layout collections to JSON and replaces layouts by name when needed.
- `substitute_home()` expands `~` and `$HOME` and also rewrites shorthand command prefixes for `fire` and `sessions`.

!!! note
    Current layout configs use `layoutTabs`, not the older `tabs` key. If you are migrating old examples, that is the first field to update.

---

## Building layouts from Python functions

`machineconfig.cluster.sessions_managers.utils.maker` is the bridge between Python callables and layout tabs.

### Key helpers

| Helper | Purpose |
| --- | --- |
| `get_fire_tab_using_uv()` | Build a tab that runs a generated Python script through `uv` |
| `get_fire_tab_using_fire()` | Build a tab that launches a callable through the `fire` command path |
| `make_layout_from_functions()` | Convert a list of functions plus extra tab configs into a full `LayoutConfig` |

### Example

```python
from machineconfig.cluster.sessions_managers.tmux.tmux_local import run_tmux_layout
from machineconfig.cluster.sessions_managers.utils.maker import make_layout_from_functions


def ingest() -> None:
    print("ingest")


def train() -> None:
    print("train")


layout = make_layout_from_functions(
    functions=[ingest, train],
    functions_weights=[1, 2],
    import_module=True,
    tab_configs=[],
    layout_name="ml-workflow",
    method="script",
    uv_with=["machineconfig"],
    uv_project_dir=None,
    start_dir="~/code/my-project",
)

run_tmux_layout(layout, on_conflict="rename")
```

---

## Controlling layout size

Large job sets often need to be split before they become usable in a terminal multiplexer. `machineconfig.cluster.sessions_managers.utils.load_balancer` provides that control.

### Main entrypoints

| Helper | Purpose |
| --- | --- |
| `limit_tab_num()` | Restrict a layout by number of tabs or by total weight |
| `limit_tab_weight()` | Split a single heavy tab into multiple tabs through a provided command splitter |

`limit_tab_num()` supports two threshold modes:

- `"number"` for raw tab count
- `"weight"` for summed `tabWeight`

and two breaking strategies:

- `"moreLayouts"` to create additional layouts
- `"combineTabs"` to merge work differently inside fewer layouts

---

## tmux orchestration

The tmux-specific APIs live in:

- `machineconfig.cluster.sessions_managers.tmux.tmux_local`
- `machineconfig.cluster.sessions_managers.tmux.tmux_local_manager`

These modules handle:

- generating a runnable tmux shell script from a `LayoutConfig`
- starting one layout or many layouts
- inspecting session status
- printing a monitoring summary

If you want backend-neutral session behavior such as conflict policies and manager differences, see [Sessions](sessions.md).

---

## API reference

## tmux layout helpers

::: machineconfig.cluster.sessions_managers.tmux.tmux_local
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## tmux layout manager

::: machineconfig.cluster.sessions_managers.tmux.tmux_local_manager
    options:
      show_root_heading: true
      show_source: false
      members_order: source
