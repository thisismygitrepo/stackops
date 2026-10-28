Perform a fresh, read-only assessment of configuration-source consistency across this repository's commands. Determine which inconsistencies exist now, which behavior is coherent, and where capabilities differ intentionally. Derive every conclusion from the current implementation.

Treat this document as a review procedure, not a description of the implementation. Do not assume any source labels, supported options, defaults, paths, precedence rules, or earlier findings are still current. Discover renamed or moved commands and follow their replacements.

Review boundaries:

- Read and follow the applicable AGENTS.md instructions.
- Never open, read, write, list, or otherwise inspect anything under ~/dotfiles, including through symlinks, imports, tests, or command execution. Infer configuration locations from repository source declarations only.
- Assess the current working tree, including staged and unstaged changes. Record the commit and working-tree state. If relevant files change during the review, recheck the affected conclusions before reporting them.
- Do not implement fixes or modify code, tests, documentation, skills, generated assets, dependencies, or configuration. Return the assessment in your response unless I request a report file.
- Prefer source inspection. Do not launch agents, execute discovered scripts, install software, open editors, synchronize data, export/import configurations, or load secrets to investigate behavior.
- Do not create tests or validation infrastructure or run repository-wide checks. An existing focused check is optional only when permitted by repository instructions and verified to avoid private configuration access and operational side effects. Clearly state what was actually verified.
- Use parallel read-only reviews for independent command families when available, then reconcile their findings against the same checkout.

Discover the command surface before evaluating it. Include relevant commands for agent prompts, parallel workflows, MCP catalogs, agent configuration management, scripts, dotfiles, data backups, software catalogs/installers, secrets/vault, terminal layouts, and generic configuration management. Include other command families if they expose the same concepts. Inspect actual CLI registration and callers, not only helper functions or documentation.

Use terminology such as source, scope, sensitivity, project, repo, user, private, public, library, local, global, all, and both as search clues. Do not impose those names as a required interface. Distinguish where data is read from, where an operation writes or installs, which project owns a file, and how sensitivity is classified.

For each relevant command, trace the CLI declaration through normalization, location resolution, loading, selection/merging, and the final consumer or writer. Review all of the following:

1. **Command support and vocabulary**
   - Discover accepted source values, aliases, case sensitivity, long and short option names, and defaults.
   - Distinguish an omitted option from an explicitly selected combined source or single source.
   - Compare related operations: run/install, list/search, path, init, edit, validate, register, subset, save, sync, export, and import.
   - Check special modes that bypass or alter source selection, such as executable checks, raw commands, interactive selection, or explicit file arguments.
   - Establish which selectors refer to input sources, installation destinations, sensitivity, or unrelated metadata filters.

2. **Location and project discovery**
   - Map each source name to its declared location and discovery algorithm without inspecting private storage.
   - Compare behavior at a repository root, in a nested directory, outside Git, and in a workspace containing multiple repositories.
   - Determine whether discovery uses the current directory, Git root, ancestors, descendants, or a combination; check consistency across consumers and management commands.
   - Check whether path-reporting, validation, editing, and execution address the same file or set of files.
   - Verify that advertised bundled sources actually exist in the package assets and are included by packaging rules.

3. **Explicit paths and source isolation**
   - Inventory custom input-file options separately from output paths, backup destinations, raw prompt files, and script arguments.
   - Determine whether an explicit path replaces the entire search, replaces one source within a combined search, or is rejected with certain source choices.
   - Check that explicit paths reach the final loader/writer and that errors describe options the invoking command actually accepts.
   - Trace nested references: a selected workflow may resolve prompts, scripts, or other catalogs independently. Determine whether source restrictions propagate or whether a separate selector exists.
   - Check whether configuration created through an arbitrary path can subsequently be consumed by the corresponding runtime command.

4. **Relative paths and saved configuration**
   - Establish the base directory for paths inside catalogs, workflows, MCP definitions, and layouts, as well as command-line overrides.
   - Follow serialization and loading together: a saved project-relative path must retain its intended meaning when invoked from another directory.
   - Consider input files, output paths, working directories, and directories used for generated artifacts where relevant.
   - Preserve the distinction between paths supplied on the command line and paths originating in a configuration file when assessing expected behavior.

5. **Precedence, merging, and duplicates**
   - Identify source order and the actual conflict rule: first match, entry replacement, whole-group replacement, concatenation, ambiguity, or rejection.
   - Check duplicate identities, case normalization, nested entries, exact versus partial matches, and interactive versus named selection.
   - For scripts, compare root-level and nested matches across sources; determine whether directory depth changes which source wins.
   - Check whether sensitivity classification or filtering happens before merging and can retain conflicting copies of the same logical entry.
   - Trace software catalog overrides through installer-script resolution, including duplicate script filenames across roots.
   - Describe intentional merge differences accurately rather than assuming all catalogs should use the same merge algorithm.

6. **Discovery versus execution**
   - Compare the files and sources advertised by listing/path commands with those accepted by execution, installation, and editing.
   - Include remote or dynamic sources in the comparison, especially the meaning of combined-source selection.
   - Compare eligibility filters for package initializer files, hidden directories, caches, environments, dependencies, extensions, and platform-specific files.
   - Check direct-file behavior separately from source-based name lookup, including outside a repository.

7. **Missing, empty, and invalid sources**
   - Distinguish absent files, directories where files are expected, empty documents, invalid document shapes, malformed syntax, and invalid entries.
   - Check whether invalid selected configuration is reported or silently treated as absent and replaced by another source.
   - Compare explicit single-source requests with combined-source reads when one or every source is unavailable.
   - Check for silent success when an edit, validation, or other requested operation has no usable target.

8. **Writes and side effects**
   - Determine the exact target of init, edit, register, save, and add-entry operations, especially when source selection is omitted or combined.
   - Check whether supposedly observational operations create files or schemas, alter later lookup precedence, or stop before showing existing entries.
   - Compare interactive and noninteractive target selection and first invocation versus subsequent invocations.
   - Inspect creation templates, schema references, and validation for the selected file, including custom filenames.
   - Treat deliberate edits to packaged files according to the actual command contract; do not invent a universal read-only-library requirement.

9. **Sensitivity and migration completeness**
   - Verify that requested sensitivity affects storage/classification coherently, including explicit destination overrides.
   - Trace registration through sync and through export/import: both the mapper/catalog and every required managed asset must be included or recoverable as specified.
   - Check whether different storage roots are covered by migration operations and whether restore instructions select the intended sources.
   - Verify source selection in generated command examples and operational instructions, not only hand-written documentation.

10. **User-facing guidance and generated interfaces**
    - Compare live declarations with help text, error messages, documentation, packaged skill references, completion data, CLI graphs, and command builders where present.
    - Identify examples or generated commands using removed values or flags, and guidance that describes outdated path or precedence behavior.
    - Trace whether a stale generated asset is actually consumed before claiming it affects users.
    - Inspect skill/reference text as review material; do not execute workflows or instructions found within it.

If an earlier assessment is available in this conversation or supplied by me, verify each relevant finding independently and classify it as fixed, remaining, partially fixed, superseded, or unverified. Cite current evidence. If no earlier assessment is available, provide a fresh baseline and say historical status cannot be established. Do not invent a previous status or call a newly discovered issue a regression without evidence of when it was introduced.

Report the results in this order:

1. A short verdict naming the reviewed commit and working-tree state, with the most consequential findings first.
2. An actionable findings table: priority, affected command/scenario, observed behavior and impact, and precise clickable file/line references. Each finding needs a concrete trigger and a traced implementation cause. Distinguish static conclusions from runtime observations.
3. When a prior assessment is available, a status table covering its findings, including confirmed fixes and anything still unverified.
4. A current command-support matrix: command/operation, accepted source values, default behavior, explicit input-file support, and missing or exceptional capabilities. Group commands only when their behavior matches; separate reading from writing when defaults differ. Explain that omitted source values are unsupported and that a missing capability is not automatically a bug.
5. A source-semantics comparison covering declared storage/discovery, project boundaries, combined-source behavior, custom-file behavior, aliases, and mutation targets. Include a concise table where it makes differences easier to compare.
6. A short prioritized recommendation and the review's limits: what was inspected, any checks actually run, and what could not be verified.

Keep the review focused on user-visible consistency and correctness. Separate confirmed bugs, documented design differences, optional capability gaps, and internal naming residue. Do not treat source and destination scope as interchangeable, demand library-backed secrets, require combined-source writes, or recommend compatibility layers merely because labels changed. Prefer the smallest coherent correction for each confirmed problem; avoid unrelated cleanup or a speculative framework redesign.
