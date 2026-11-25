// What the server sends, made ready for the page: which values are lists of folders, which name prefixes are common enough to filter by, and on
// the search path which folder is listed twice and which programs are never reached because an earlier folder holds the same name.
export function prepare({ variables, path_entries: listed, path_separator: separator }) {
  const prepared = variables.map((variable) => {
    const parts = variable.value === null ? [] : variable.value.split(separator).filter(Boolean);
    const isList = parts.length >= 2 && parts.every((part) => /^(\/|~|\.|[A-Za-z]:[\\/])/.test(part));
    return {
      ...variable,
      parts: isList ? parts : null,
      prefix: variable.name.includes("_") && !variable.name.startsWith("_") ? `${variable.name.split("_")[0]}_` : "",
      text: `${variable.name} ${variable.value ?? ""}`.toLowerCase(),
    };
  });
  const prefixCounts = new Map();
  for (const { prefix } of prepared) if (prefix) prefixCounts.set(prefix, (prefixCounts.get(prefix) ?? 0) + 1);
  const prefixes = [...prefixCounts].filter(([, count]) => count >= 3).sort((left, right) => right[1] - left[1]).slice(0, 8);

  // The first folder that holds a program wins it. A folder listed a second time wins nothing: its first listing already did.
  const firstIndex = new Map();
  listed.forEach((entry, index) => !firstIndex.has(entry.path) && firstIndex.set(entry.path, index));
  const winner = new Map();
  listed.forEach((entry, index) => {
    if (firstIndex.get(entry.path) !== index) return;
    for (const command of entry.commands) if (!winner.has(command)) winner.set(command, index);
  });
  const entries = listed.map((entry, index) => {
    const duplicateOf = firstIndex.get(entry.path) === index ? null : firstIndex.get(entry.path);
    const shadowed = new Set(duplicateOf === null ? entry.commands.filter((command) => winner.get(command) !== index) : entry.commands);
    return { ...entry, index, duplicateOf, shadowed, pathText: entry.path.toLowerCase() };
  });
  return { variables: prepared, prefixes, entries, winner };
}
