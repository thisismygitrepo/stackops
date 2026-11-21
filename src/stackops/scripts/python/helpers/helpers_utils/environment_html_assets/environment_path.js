const PATH_STATE_LABELS = { missing: "missing", file: "not a directory", unreadable: "unreadable" };
const PILL_LIMIT = 300;

function pathView(onChange) {
  const firstIndex = new Map();
  report.path_entries.forEach((entry, index) => {
    if (!firstIndex.has(entry.path)) firstIndex.set(entry.path, index);
  });
  const winner = new Map();
  report.path_entries.forEach((entry, index) => {
    if (firstIndex.get(entry.path) !== index) return;
    for (const command of entry.commands) if (!winner.has(command)) winner.set(command, index);
  });
  const entries = report.path_entries.map((entry, index) => {
    const duplicateOf = firstIndex.get(entry.path) === index ? null : firstIndex.get(entry.path);
    const shadowed = new Set(duplicateOf === null ? entry.commands.filter((command) => winner.get(command) !== index) : entry.commands);
    return { ...entry, index, duplicateOf, shadowed, pathText: entry.path.toLowerCase() };
  });
  const expanded = new Set();
  const unusable = entries.filter((entry) => entry.state !== "directory").length;
  const duplicates = entries.filter((entry) => entry.duplicateOf !== null).length;
  const shadowing = entries.filter((entry) => entry.duplicateOf === null && entry.shadowed.size > 0);

  function entryRow(entry, terms) {
    const matching = terms.length > 0 ? entry.commands.filter((command) => terms.every((term) => command.toLowerCase().includes(term))) : [];
    const shown = matching.length > 0 ? matching : expanded.has(entry.index) ? entry.commands : [];
    const directory = el("td");
    const code = el("code", "", homePath(entry.path));
    code.title = entry.path;
    directory.append(code);
    if (shown.length > 0) {
      const pills = el("div", "pills");
      for (const command of shown.slice(0, PILL_LIMIT)) {
        const isShadowed = entry.shadowed.has(command);
        const pill = el("span", isShadowed ? "pill shadowed" : "pill");
        pill.append(mark(isShadowed ? "muted" : "good"), isShadowed ? `${command} → #${winner.get(command) + 1}` : command);
        pill.title = isShadowed ? `Shadowed by entry #${winner.get(command) + 1}: ${report.path_entries[winner.get(command)].path}` : "This entry provides the command";
        pills.append(pill);
      }
      if (shown.length > PILL_LIMIT) pills.append(el("span", "note", `+${(shown.length - PILL_LIMIT).toLocaleString()} more · search to narrow`));
      directory.append(pills);
    }
    const state = el("td", "nowrap");
    if (entry.duplicateOf !== null) state.append(statusLabel("warn", `duplicate of #${entry.duplicateOf + 1}`));
    else if (entry.state === "directory") state.append(statusLabel("good", "ok"));
    else state.append(statusLabel("warn", PATH_STATE_LABELS[entry.state]));
    const shadowedCount = entry.duplicateOf === null ? entry.shadowed.size : 0;
    const commands = el("td", "nowrap", `${entry.commands.length.toLocaleString()}${shadowedCount > 0 ? ` · ${shadowedCount.toLocaleString()} shadowed` : ""}`);
    const tr = el("tr", "expandable");
    tr.append(el("td", "index", `#${entry.index + 1}`), directory, state, commands);
    tr.addEventListener("click", () => {
      if (getSelection().toString() !== "") return;
      if (expanded.has(entry.index)) expanded.delete(entry.index);
      else expanded.add(entry.index);
      onChange();
    });
    return tr;
  }

  return {
    title: "PATH entries",
    placeholder: "Find a command or directory",
    tiles: [
      ["Entries", entries.length], ["Not usable", unusable], ["Duplicates", duplicates], ["Commands on PATH", winner.size],
      ["Shadowed commands", shadowing.reduce((sum, entry) => sum + entry.shadowed.size, 0)],
    ],
    note: "Entries are listed in lookup order: the first entry that holds a command wins. Select a row to list its commands; a search shows which entry provides each match.",
    chips: [
      { key: ":unusable", label: "not usable", count: unusable },
      { key: ":duplicate", label: "duplicates", count: duplicates },
      { key: ":shadowing", label: "has shadowed commands", count: shadowing.length },
    ].filter((chip) => chip.count > 0),
    headers: ["Order", "Directory", "State", "Commands"],
    emptyText: "No PATH entries match these filters",
    total: entries.length,
    rows(terms, active) {
      return entries
        .filter(
          (entry) =>
            (!active.has(":unusable") || entry.state !== "directory") &&
            (!active.has(":duplicate") || entry.duplicateOf !== null) &&
            (!active.has(":shadowing") || (entry.duplicateOf === null && entry.shadowed.size > 0)) &&
            (terms.every((term) => entry.pathText.includes(term)) ||
              entry.commands.some((command) => terms.every((term) => command.toLowerCase().includes(term)))),
        )
        .map((entry) => entryRow(entry, terms));
    },
  };
}
