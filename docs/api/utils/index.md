# Utils API

`machineconfig.utils` is the main shared-library layer of the project. It contains the pieces that downstream repos tend to import directly inside application logic: environment discovery, path and config helpers, schedulers, interactive selection, script generation, SSH helpers, and various operational utilities.

Rather than treating `utils` as one giant bag of functions, the docs below group it by workflow.

---

## Topics in this section

| Topic | Use it when you need to... | Main modules |
| --- | --- | --- |
| [Environment and project wiring](environment-and-projects.md) | Discover project virtualenvs, IPython profiles, and cloud metadata | `machineconfig.utils.ve` |
| [Paths, files, and config](paths-files-config.md) | Read and write JSON/INI/pickle files, manipulate paths, derive repo roots | `machineconfig.utils.io`, `machineconfig.utils.path_extended` |
| [Scheduling and cache](scheduling-and-cache.md) | Run recurring routines and reuse expensive results through memory or disk caches | `machineconfig.utils.scheduler` |
| [Interactive helpers and notifications](interactive-helpers.md) | Generate IDs, split work, show rich output, present interactive choices, send email | `machineconfig.utils.accessories`, `machineconfig.utils.options`, `machineconfig.utils.notifications` |
| [Code generation and command launching](code-generation.md) | Turn callables into runnable scripts, build `uv` commands, launch shell scripts, ensure tools exist | `machineconfig.utils.meta`, `machineconfig.utils.code`, `machineconfig.utils.installer_utils.installer_cli` |

---

## What tends to live outside this section

- Session-layout types and generators are documented under [Cluster](../cluster/index.md), even though they depend on some utils modules.
- `machineconfig.utils.ssh` is documented from the [Remote execution and networking](../cluster/remote.md) page because it is usually part of remote workflows.
- Installer catalog details live under [Jobs](../jobs/index.md), with `install_if_missing` covered from the code-generation utilities page because it often acts as a guard before launching other tools.

---

## Typical import patterns

```python
from machineconfig.utils.accessories import randstr, split_list
from machineconfig.utils.code import run_shell_script
from machineconfig.utils.io import read_json, save_json
from machineconfig.utils.options import choose_from_options
from machineconfig.utils.scheduler import Scheduler, CacheMemory
from machineconfig.utils.ve import get_ve_path_and_ipython_profile
```

!!! note
    `PathExtended` is still common in existing integrations and older code paths. New code can mix it with plain `pathlib.Path`, but if you are reading or extending current downstream usage you will see `PathExtended` often.
