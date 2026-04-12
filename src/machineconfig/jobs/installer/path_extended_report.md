# PathExtended Usage Report

External Python call sites for public methods defined on `src/machineconfig/utils/path_extended.py`.

Methodology:
- Excluded calls inside `src/machineconfig/utils/path_extended.py`.
- Scanned production Python files under `src/` that reference `PathExtended` or `machineconfig.utils.path_extended`.
- Found candidate calls with AST, then used Jedi static inference to confirm the call resolves to the method definition in `path_extended.py`.

Summary:
- Confirmed external call sites: `18`
- Public methods with at least one external use: `7 / 25`
- Table below omits public methods with zero confirmed external uses.

| Rank | Method | Uses | Files |
| ---: | --- | ---: | ---: |
| 1 | `unzip` | 4 | 3 |
| 2 | `decompress` | 3 | 1 |
| 3 | `download` | 3 | 3 |
| 4 | `zip` | 3 | 3 |
| 5 | `symlink_to` | 2 | 1 |
| 6 | `tmpdir` | 2 | 2 |
| 7 | `with_name` | 1 | 1 |
