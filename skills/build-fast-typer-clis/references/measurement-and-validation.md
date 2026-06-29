# Measurement and Validation

## Contents

1. Reproducible baseline
2. Import profiling
3. Runner overhead
4. Behavior checks
5. Import regression test
6. Completion report

## 1. Reproducible Baseline

Run from the repository root and benchmark the exact command the user experiences:

```bash
hyperfine --warmup 2 --runs 10 \
  'uv run --no-dev my-cli group --help'
```

Record peak resident memory:

```bash
/usr/bin/time -f 'elapsed=%e max_rss_kb=%M' \
  uv run --no-dev my-cli group --help >/dev/null
```

Measure at least:

- root help;
- the affected group help;
- one lightweight leaf help path;
- each leaf previously responsible for a large eager import.

Use the same command, environment, warmup, and run count after the refactor.

## 2. Import Profiling

Rank modules by cumulative import time:

```bash
PYTHONPROFILEIMPORTTIME=1 uv run --no-dev my-cli group --help 2>&1 \
  | rg '^import time:' \
  | sort -t '|' -k 2 -nr \
  | sed -n '1,80p'
```

Interpret the second timing column as cumulative time. Follow the first application module above each heavy dependency to find the eager edge.

Typical indicators:

- `ccxt`, HTTP, or exchange modules: stream/API planning imported during registration;
- `sqlalchemy` or database drivers: connection types imported for help;
- `numpy`, `polars`, `pandas`, `numba`, plotting, or ML modules: implementation or default constants imported by a callback signature;
- configuration/network modules: machine layout types coupled to unrelated commands.

## 3. Runner Overhead

After application imports are small, compare the project runner with the generated console script:

```bash
hyperfine --warmup 2 --runs 10 \
  'uv run --no-dev my-cli --help' \
  '.venv/bin/my-cli --help'
```

Do not redesign the application to remove a small runner cost. Report it separately. For installed user workflows, prefer the direct console script.

Typer, Click, Rich, Python startup, and terminal rendering form the residual floor. Stop when import profiling shows no application leaf modules and the remaining cost is framework/runner overhead.

## 4. Behavior Checks

Exercise these paths after routing changes:

```bash
uv run --no-dev my-cli --help
uv run --no-dev my-cli group --help
uv run --no-dev my-cli group canonical-command --help
uv run --no-dev my-cli group hidden-alias --help
```

Also verify:

- required arguments still fail at the selected leaf;
- commands intended to execute with no arguments still execute;
- commands intended to show help with no arguments still show help;
- usage paths include the selected nested command;
- exceptions and exit codes are not swallowed;
- parent help lists the same canonical commands and descriptions.

Never invoke a side-effecting command merely to time startup.

## 5. Import Regression Test

Use a fresh subprocess because test collection may already have imported implementation modules:

```python
import subprocess
import sys


def test_group_help_does_not_import_leaf_modules() -> None:
    script = """
import sys

from typer.testing import CliRunner

from project.cli.group_router import get_app

result = CliRunner().invoke(get_app(), ["--help"])
assert result.exit_code == 0, result.output

leaf_modules = {
    "project.cli.database",
    "project.cli.machine_learning",
    "project.cli.streaming",
}
imported_leaf_modules = leaf_modules.intersection(sys.modules)
assert imported_leaf_modules == set(), sorted(imported_leaf_modules)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
```

Keep this test architectural: assert that implementation modules are absent rather than asserting a fragile millisecond threshold.

Add focused `CliRunner` tests for routing behavior when no-argument handling, aliases, or option forwarding changed.

## 6. Completion Report

Report:

- the eager import roots removed;
- the lazy boundary introduced;
- before/after mean startup time;
- before/after peak RSS;
- representative leaf-help results;
- focused tests, linter, and type-checker outcomes;
- any residual framework or runner overhead.

Do not combine unrelated concurrent worktree changes into the report.
