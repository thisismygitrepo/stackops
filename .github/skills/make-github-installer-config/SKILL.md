---
name: make-github-installer-config
description: Add, edit, or remove GitHub binary installer entries in StackOps software catalogs. Use when changing a bundled or user installer definition, or deriving a new definition from GitHub release assets.
---

Change the requested entry in the selected catalog's `installers` array, using the live `InstallerData` schema.

Mandatory execution rule:

- Run all helper scripts with `uv run ...`.
- Never run these helpers with plain `python`.

## Select the Catalog and Operation

- Resolve the StackOps checkout before using the helper paths below; run them from that checkout. Discover current commands with `uv run devops software --help`.
- Run `uv run devops software path --source all` to locate the user and bundled catalogs and schemas. For an explicit custom catalog, use `uv run devops software path --source user --custom-path '<catalog-path>'`.
- Use the user catalog for personal definitions and overrides. Edit the bundled catalog only when the request concerns StackOps's shared definitions, using `src/stackops/utils/schemas/installer/installer_data.yaml` in the verified checkout rather than an installed package copy. Carry the chosen absolute catalog path through every edit and validation command.
- Respect repository and session path restrictions before reading or writing a resolved path. Initialize a missing permitted user catalog with `uv run devops software init --custom-path '<catalog-path>'` only when adding an entry.
- Locate an existing entry by `appName` and `repoURL` before choosing add, edit, or remove. Runtime names are case-insensitive; user entries replace bundled entries with the same name when `--source all` is used.

## Edit or Remove an Existing Entry

- Edit the selected row in place, changing only the requested fields and preserving optional metadata and all other entries. For a personal override of a bundled entry, copy that complete entry into the user catalog and apply the requested changes there.
- Scan releases only when the requested edit requires new asset patterns or repository information. Do not rebuild an entire entry for a description, category, or other isolated field change.
- For removal, delete the exact requested row from the selected catalog. Do not scan releases, invoke the upsert helper, or uninstall software. Removing a user override reveals the bundled definition again under `--source all`; removing a bundled definition requires a change to the shared catalog.
- Validate the selected file with `uv run devops software validate --custom-path '<catalog-path>'`. This checks its schema and runtime catalog rules. Report the target path and the resulting catalog behavior.

## Add a GitHub Release Installer

Use this process for a new definition; if the target already exists, use the edit workflow above.

1. Read target `repoURL`, `appName`, and `doc` from the user request.
2. Resolve `license`:

- If the user explicitly supplied a license string, pass it to the builder with `--license`.
- Otherwise let the builder infer the license from GitHub repository metadata, then verify that inferred value before writing.

3. Scan releases and classify candidate binaries:

```bash
uv run .github/skills/make-github-installer-config/scripts/scan_github_releases.py \
  --repo-url "https://github.com/OWNER/REPO" \
  --limit 8 \
  --output ./.ai/tmp_scripts/make-github-installer-config/scan.json
```

4. Build inferred config and run latest-release presence checks:

```bash
uv run .github/skills/make-github-installer-config/scripts/build_installer_config.py \
  --repo-url "https://github.com/OWNER/REPO" \
  --app-name "appname" \
  --doc "short description" \
  --limit 8 \
  --output ./.ai/tmp_scripts/make-github-installer-config/entry.json
```

Optional license override:

```bash
uv run .github/skills/make-github-installer-config/scripts/build_installer_config.py \
  --repo-url "https://github.com/OWNER/REPO" \
  --app-name "appname" \
  --doc "short description" \
  --license "MIT License" \
  --limit 8 \
  --output ./.ai/tmp_scripts/make-github-installer-config/entry.json
```

5. Verify checks from `entry.json` before writing:

- If `checks.latestPatternChecks` is non-empty, treat as warning and explain why.
- If `checks.licenseWarning` is non-null, treat as warning and explain why.
- Do not silently ignore failed checks.

6. Perform a dry-run upsert first:

```bash
uv run .github/skills/make-github-installer-config/scripts/upsert_installer_data.py \
  --installer-data '<catalog-path>' \
  --entry-json ./.ai/tmp_scripts/make-github-installer-config/entry.json \
  --dry-run
```

7. If dry-run output is correct, run actual upsert:

```bash
uv run .github/skills/make-github-installer-config/scripts/upsert_installer_data.py \
  --installer-data '<catalog-path>' \
  --entry-json ./.ai/tmp_scripts/make-github-installer-config/entry.json
```

8. Validate the selected catalog:

```bash
uv run devops software validate --custom-path '<catalog-path>'
```

Output JSON entry must use this exact shape:

```json
{
  "appName": "...",
  "license": "...",
  "repoURL": "https://github.com/OWNER/REPO",
  "doc": "...",
  "categoryLabels": ["..."],
  "fileNamePattern": {
    "amd64": {
      "linux": "... or null",
      "darwin": "... or null",
      "windows": "... or null"
    },
    "arm64": {
      "linux": "... or null",
      "darwin": "... or null",
      "windows": "... or null"
    }
  }
}
```

Requirements:

- `categoryLabels` is required and must be non-empty. Pick from the `InstallerCategory` enum in `src/stackops/utils/schemas/installer/installer_data.schema.json`. `build_installer_config.py` does not emit it, so add it to `entry.json` before upserting.
- `lastCommitDate` and `lastCommitDateCheckDate` are optional; the commit-date refresh keeps them up to date.
- `comment` is an optional maintainer note. Put notes there, never in YAML `#` comments: the catalog writers rewrite the whole file and drop them.
- Quote YAML values that would otherwise parse as dates, numbers or booleans; the catalog loader rejects non-string values.
- `license` is required. Prefer the GitHub repo license metadata unless the user explicitly overrides it.
- If GitHub does not declare a license, use `"No license asserted"` and call that out explicitly.
- If binaries are unavailable for a platform/architecture, set that value to `null`.
- Prefer Linux `musl` artifacts over `gnu` when both are available.
- Use stable, recurring filename patterns from recent releases.
- Keep `appName` lowercase and concise.
- Keep `doc` short and descriptive.
- Keep `license` short and literal; do not invent SPDX identifiers that upstream does not declare.
- Ensure selected non-null patterns match at least one asset in the latest inspected release.
- When the user requests an entry object only, return that JSON without surrounding prose. After a requested file change, report the catalog path, changed entry, and validation result.

Safety and idempotency rules:

- Always check whether an entry with the same case-insensitive `appName` or `repoURL` already exists. Distinct installers may share a repository (or the `CMD` marker); never merge them for that reason.
- The upsert helper validates the entry with the runtime catalog rules, then replaces the whole row with the same case-insensitive `appName` or appends a new row. It never matches on `repoURL`.
- Perform the helper's dry-run before an upsert. For direct edits or removals, inspect the exact selected row and intended change before writing.
- Never mutate unrelated installer entries.

Helper scripts available in this skill:

- `.github/skills/make-github-installer-config/scripts/scan_github_releases.py`
- `.github/skills/make-github-installer-config/scripts/build_installer_config.py`
- `.github/skills/make-github-installer-config/scripts/upsert_installer_data.py`
