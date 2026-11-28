# Utils API

`stackops.utils` is the shared-library layer that most downstream code imports directly. It contains IO and path helpers, cloud defaults, interactive selection utilities, installer runtime helpers, and the script-generation functions that feed the cluster and remote layers. This section also documents two modules that live outside `stackops.utils`: the scheduler and caches in `stackops.cluster.scheduler`, and the virtualenv discovery helpers in `stackops.scripts.python.helpers.helpers_utils.python_env`.

---

## Topics in this section

| Topic | Use it when you need to... | Main modules |
| --- | --- | --- |
| [Environment and project wiring](environment-and-projects.md) | Discover project virtualenvs and load default cloud settings | `stackops.scripts.python.helpers.helpers_utils.python_env`, `stackops.utils.cloud.defaults` |
| [Paths, files, and config](paths-files-config.md) | Read and write JSON / INI / pickle files, encrypt files with GPG, resolve paths and path references | `stackops.utils.io`, `stackops.utils.files.read`, `stackops.utils.path_core`, `stackops.utils.path_reference` |
| [Scheduling and cache](scheduling-and-cache.md) | Run recurring routines and reuse expensive results through memory or disk caches | `stackops.cluster.scheduler` |
| [Interactive helpers](interactive-helpers.md) | Generate IDs, split work, and present interactive choices | `stackops.utils.accessories`, `stackops.utils.options_utils.options` |
| [Code generation and command launching](code-generation.md) | Turn callables into scripts, build `uv` commands, run shell snippets, hand off shell work, and ensure CLIs exist | `stackops.utils.meta`, `stackops.utils.code`, `stackops.utils.installer_utils.installer_cli` |

---

## What tends to live outside this section

- Layout schemas and terminal-session backends are documented under [Cluster](../cluster/index.md), even though they depend on several utils modules.
- `stackops.utils.ssh_utils` is documented from [Remote execution and networking](../cluster/remote.md) because it is usually consumed as part of a remote workflow.
- Installer data and package groups (`stackops.utils.schemas.installer`) and the runtime installer engine (`stackops.utils.installer_utils`) are documented under [Jobs](../jobs/index.md).

---

## Typical import patterns

```python
from stackops.utils.accessories import randstr, split_list
from stackops.utils.code import run_shell_script
from stackops.utils.files.read import read_json
from stackops.utils.io import save_json
from stackops.utils.options_utils.options import choose_from_options
from stackops.utils.path_core import collapseuser, tmpfile
from stackops.cluster.scheduler import Scheduler, CacheMemory
```

The utilities in this section are intentionally low-level. Higher-level session, cluster, and installer flows mostly build on these primitives rather than replacing them.
