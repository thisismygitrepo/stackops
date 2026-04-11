# PathExtended Usage Report

External Python call sites for public methods defined on `src/machineconfig/utils/path_extended.py`.

Methodology:
- Excluded calls inside `src/machineconfig/utils/path_extended.py`.
- Scanned repo Python files that reference `PathExtended` or `machineconfig.utils.path_extended`.
- Found candidate calls with AST, then used Jedi static inference to confirm the call resolves to the method definition in `path_extended.py`.

Summary:
- Confirmed external call sites: `122`
- Public methods with at least one external use: `13 / 25`

| Rank | Method | Uses | Files |
| ---: | --- | ---: | ---: |
| 1 | `delete` | 43 | 10 |
| 2 | `move` | 18 | 5 |
| 3 | `resolve` | 14 | 2 |
| 4 | `collapseuser` | 11 | 6 |
| 5 | `copy` | 10 | 5 |
| 6 | `with_name` | 6 | 3 |
| 7 | `unzip` | 5 | 4 |
| 8 | `decompress` | 4 | 2 |
| 9 | `download` | 3 | 3 |
| 10 | `zip` | 3 | 3 |
| 11 | `symlink_to` | 2 | 1 |
| 12 | `tmpdir` | 2 | 2 |
| 13 | `unbz` | 1 | 1 |
| 14 | `append` | 0 | 0 |
| 15 | `rel2home` | 0 | 0 |
| 16 | `split` | 0 | 0 |
| 17 | `size` | 0 | 0 |
| 18 | `clickable` | 0 | 0 |
| 19 | `as_url_str` | 0 | 0 |
| 20 | `as_zip_path` | 0 | 0 |
| 21 | `tmpfile` | 0 | 0 |
| 22 | `tmp` | 0 | 0 |
| 23 | `untar` | 0 | 0 |
| 24 | `ungz` | 0 | 0 |
| 25 | `unxz` | 0 | 0 |
