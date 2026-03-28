# API Reference

`machineconfig` has a broad package surface, but downstream projects usually consume it as a shared operations layer rather than as a narrow library. The recurring integration points are project wiring, filesystem helpers, schedulers and caches, interactive CLI utilities, generated scripts, session layouts, remote execution, and curated installers.

This reference is organized around those workflows so it is easier to answer questions like "how do I launch a generated tmux layout?" or "which module handles remote job transfer?" without having to memorize the full package tree.

---

## Integration areas

| Area | What it covers | Main modules | Reference |
| --- | --- | --- | --- |
| Environment and project wiring | Virtualenv discovery, IPython profile lookup, cloud sync config metadata | `machineconfig.utils.ve` | [Environment and project wiring](utils/environment-and-projects.md) |
| Paths, files, and config documents | Path mutation helpers, JSON/INI/pickle IO, lightweight encryption, repo-root discovery | `machineconfig.utils.path_extended`, `machineconfig.utils.io` | [Paths, files, and config](utils/paths-files-config.md) |
| Scheduling and cache | Recurring routines, in-memory cache wrappers, disk-backed cache wrappers | `machineconfig.utils.scheduler` | [Scheduling and cache](utils/scheduling-and-cache.md) |
| Interactive helpers and notifications | Random identifiers, list splitting, fuzzy pickers, rich output, email delivery | `machineconfig.utils.accessories`, `machineconfig.utils.options`, `machineconfig.utils.notifications` | [Interactive helpers and notifications](utils/interactive-helpers.md) |
| Code generation and command launching | Convert callables to scripts, build `uv` commands, run shell snippets, hand off commands to another shell | `machineconfig.utils.meta`, `machineconfig.utils.code`, `machineconfig.utils.installer_utils.installer_cli` | [Code generation and command launching](utils/code-generation.md) |
| Session layouts and tmux orchestration | Layout schema, tab generation from functions, tab fan-out controls, tmux managers | `machineconfig.cluster.sessions_managers.*`, `machineconfig.utils.schemas.layouts.layout_types` | [Layouts](cluster/layouts.md), [Sessions](cluster/sessions.md) |
| Remote execution and networking | Remote job configs, script generation, job transfer, firing jobs, SSH, IP helpers | `machineconfig.cluster.remote.*`, `machineconfig.utils.ssh`, `machineconfig.scripts.python.helpers.helpers_network.*` | [Remote execution and networking](cluster/remote.md) |
| Installer and package groups | Installer metadata, curated groups, security checks, per-tool install scripts | `machineconfig.jobs.installer.*` | [Jobs and installer APIs](jobs/index.md) |

---

## Package map

```text
machineconfig/
├── cluster/
│   ├── remote/                    # Remote job configs, transfer, launch, logs
│   └── sessions_managers/         # zellij, tmux, Windows Terminal backends
├── jobs/
│   └── installer/                 # Curated install data and package groups
├── scripts/python/helpers/
│   ├── helpers_devops/            # Operational CLI entrypoints
│   └── helpers_network/           # Address and connectivity helpers
├── utils/
│   ├── code, meta, io, ve         # Script generation, IO, environment wiring
│   ├── scheduler, ssh             # Scheduling, caching, remote access
│   ├── accessories, options       # Interactive helpers and UI glue
│   └── schemas/layouts            # Typed layout definitions
└── settings/                      # Templates and configuration assets
```

---

## Choose a reference track

### Utilities

Start here if you are integrating `machineconfig` into an application or script and need shared helper APIs:

- [Utils overview](utils/index.md)
- [Environment and project wiring](utils/environment-and-projects.md)
- [Paths, files, and config](utils/paths-files-config.md)
- [Scheduling and cache](utils/scheduling-and-cache.md)
- [Interactive helpers and notifications](utils/interactive-helpers.md)
- [Code generation and command launching](utils/code-generation.md)

### Cluster and remote execution

Start here if you are generating layouts, managing terminal sessions, or submitting work to remote machines:

- [Cluster overview](cluster/index.md)
- [Layouts](cluster/layouts.md)
- [Sessions](cluster/sessions.md)
- [Remote execution and networking](cluster/remote.md)

### Jobs and installers

Start here if you want the curated package catalog, package groups, or low-level install flows:

- [Jobs overview](jobs/index.md)
- [Installer reference](jobs/installer.md)

---

## Common import patterns

```python
from machineconfig.cluster.remote.remote_machine import RemoteMachine
from machineconfig.cluster.remote.models import RemoteMachineConfig
from machineconfig.cluster.sessions_managers.utils.maker import make_layout_from_functions
from machineconfig.jobs.installer.package_groups import PACKAGE_GROUP2NAMES
from machineconfig.utils.scheduler import Scheduler, Cache
from machineconfig.utils.code import run_shell_script
from machineconfig.utils.options import choose_from_options
```

If you need CLI entrypoints instead of library APIs, see the [CLI Reference](../cli/index.md).
