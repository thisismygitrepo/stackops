# Cluster API

`stackops.cluster` is the orchestration layer of the library. It combines:

- typed layout definitions
- remote job packaging, transfer, launch, resource locking, and status tracking

Most higher-level automation code in this area moves through those three pieces in that order.

---

## Topics in this section

| Topic | What it covers | Main modules |
| --- | --- | --- |
| [Remote execution and networking](remote.md) | Remote job models, generated scripts, SFTP/cloud transfer, SSH helpers, workload distribution, address helpers | `stackops.cluster.remote.*`, `stackops.utils.ssh_utils.ssh`, `stackops.utils.network.address`, `stackops.scripts.python.helpers.helpers_network.*` |

---

## Architecture

```mermaid
graph TB
    A[LayoutConfig / TabConfig] --> B[maker.py / load_balancer.py]
    B --> C[Local session managers]
    C --> D[tmux]

    G[RemoteStackOpsConfig] --> H[RemoteMachine]
    H --> I[JobParams]
    H --> J[FileManager]
    H --> K[data_transfer.py]
    H --> L[SSH]

    M[distribute.Cluster] --> H
```

---

## Common import patterns

```python
from stackops.cluster.remote.distribute import Cluster
from stackops.cluster.remote.models import RemoteStackOpsConfig
from stackops.cluster.remote.remote_machine import RemoteMachine
from stackops.utils.ssh_utils.ssh import SSH
from stackops.cluster.sessions_managers.tmux.tmux_local_manager import TmuxLocalManager
from stackops.cluster.sessions_managers.utils.maker import make_layout_from_functions
from stackops.utils.schemas.layouts.layout_types import LayoutConfig
```
