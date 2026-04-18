# Utils API

`stackops.utils` is the shared-library layer that most downstream code imports directly. It contains environment discovery, IO and path helpers, schedulers and caches, interactive selection utilities, notification helpers, and the script-generation functions that feed the cluster and installer layers.

---

## Topics in this section

| Topic | Use it when you need to... | Main modules |
| --- | --- | --- |
| [Environment and project wiring](environment-and-projects.md) | Discover project virtualenvs, optional IPython profiles, and `.ve.yaml` cloud metadata | `stackops.utils.ve` |
| [Paths, files, and config](paths-files-config.md) | Read and write JSON / INI / pickle files, encrypt files with GPG, resolve paths and path references | `stackops.utils.io`, `stackops.utils.path_core`, `stackops.utils.path_helper`, `stackops.utils.path_reference` |
| [Scheduling and cache](scheduling-and-cache.md) | Run recurring routines and reuse expensive results through memory or disk caches | `stackops.utils.scheduler` |
| [Interactive helpers and notifications](interactive-helpers.md) | Generate IDs, split work, present interactive choices, and send email | `stackops.utils.accessories`, `stackops.utils.options`, `stackops.utils.notifications` |
| [Code generation and command launching](code-generation.md) | Turn callables into scripts, build `uv` commands, run shell snippets, and ensure CLIs exist | `stackops.utils.meta`, `stackops.utils.code`, `stackops.utils.installer_utils.installer_cli` |

---

## What tends to live outside this section

- Layout schemas and terminal-session backends are documented under [Cluster](../cluster/index.md), even though they depend on several utils modules.
- `stackops.utils.ssh` is documented from [Remote execution and networking](../cluster/remote.md) because it is usually consumed as part of a remote workflow.
- Installer data and package groups live under [Jobs](../jobs/index.md), while the runtime installer engine lives under `stackops.utils.installer_utils`.

---

## Typical import patterns

```python
from stackops.utils.accessories import randstr, split_list
from stackops.utils.code import run_shell_script
from stackops.utils.io import read_json, save_json
from stackops.utils.options import choose_from_options
from stackops.utils.path_core import collapseuser, tmpfile
from stackops.utils.scheduler import Scheduler, CacheMemory
from stackops.utils.ve import get_ve_path_and_ipython_profile
```

The utilities in this section are intentionally low-level. Higher-level session, cluster, and installer flows mostly build on these primitives rather than replacing them.
