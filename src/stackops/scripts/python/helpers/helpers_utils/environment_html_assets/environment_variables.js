function variableRow(variable) {
  const value = el("span", "value");
  if (variable.value === null) {
    value.append(statusLabel("muted", "left out · looks like a secret"));
  } else if (variable.value === "") {
    value.append(el("span", "note", "empty"));
  } else if (variable.parts) {
    const list = el("ol", "parts");
    for (const part of variable.parts) {
      const item = el("li");
      const code = el("code", "", homePath(part));
      code.title = part;
      item.append(code);
      list.append(item);
    }
    value.append(list);
    if (variable.parts.length > 4) value.append(el("span", "note more", `+${variable.parts.length - 4} more · click the row to expand`));
  } else {
    value.append(el("code", "clamp", variable.value));
  }
  if (variable.value && navigator.clipboard) value.append(copyButton(variable.value));
  const valueCell = el("td");
  valueCell.append(value);
  const tr = el("tr", "expandable");
  tr.append(el("td", "name", variable.name), valueCell);
  tr.addEventListener("click", (event) => {
    if (!event.target.closest("button") && getSelection().toString() === "") tr.classList.toggle("expanded");
  });
  return tr;
}

function variablesView() {
  const variables = report.variables.map((variable) => {
    const parts = variable.value === null ? [] : variable.value.split(report.path_separator).filter(Boolean);
    const isList = parts.length >= 2 && parts.every((part) => /^(\/|~|\.|[A-Za-z]:[\\/])/.test(part));
    return {
      ...variable,
      parts: isList ? parts : null,
      prefix: variable.name.includes("_") && !variable.name.startsWith("_") ? `${variable.name.split("_")[0]}_` : "",
      text: `${variable.name} ${variable.value ?? ""}`.toLowerCase(),
    };
  });
  const prefixCounts = new Map();
  for (const variable of variables) {
    if (variable.prefix) prefixCounts.set(variable.prefix, (prefixCounts.get(variable.prefix) ?? 0) + 1);
  }
  const prefixes = [...prefixCounts].filter(([, count]) => count >= 3).sort((left, right) => right[1] - left[1]).slice(0, 10);
  const leftOut = variables.filter((variable) => variable.value === null).length;
  const lists = variables.filter((variable) => variable.parts).length;
  return {
    title: "Environment variables",
    placeholder: "Filter names and values",
    tiles: [["Variables", variables.length], ["Path lists", lists], ["Values left out", leftOut]],
    note: leftOut > 0
      ? "Values are left out of this file when the variable's name or value looks like a secret. Use the terminal navigator to read them."
      : "",
    chips: [
      ...prefixes.map(([prefix, count]) => ({ key: prefix, label: `${prefix}*`, count })),
      { key: ":lists", label: "path lists", count: lists },
      { key: ":left-out", label: "left out", count: leftOut },
    ].filter((chip) => chip.count > 0),
    headers: ["Name", "Value"],
    emptyText: "No variables match these filters",
    total: variables.length,
    rows(terms, active) {
      const prefixFilters = [...active].filter((key) => !key.startsWith(":"));
      return variables
        .filter(
          (variable) =>
            terms.every((term) => variable.text.includes(term)) &&
            (prefixFilters.length === 0 || prefixFilters.includes(variable.prefix)) &&
            (!active.has(":lists") || variable.parts !== null) &&
            (!active.has(":left-out") || variable.value === null),
        )
        .map(variableRow);
    },
  };
}
