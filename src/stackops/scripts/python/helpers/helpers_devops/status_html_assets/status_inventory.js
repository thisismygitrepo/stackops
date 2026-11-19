const MANAGED_TONES = { Valid: "good", Missing: "warn", Invalid: "bad", Unreadable: "bad" };

function renderApps(details) {
  const groups = Object.entries(details).map(([name, tools]) => ({
    title: name.replaceAll("-", " "),
    tools: Object.entries(tools).map(([tool, installed]) => ({ tool, installed })),
  }));
  const unique = new Map(groups.flatMap((group) => group.tools.map((item) => [item.tool, item.installed])));
  const installedTotal = [...unique.values()].filter(Boolean).length;
  const state = { filter: "", show: "all" };
  const filter = searchInput("Filter tools or groups");
  const modes = el("div", "segmented");
  const count = el("span", "count");
  const grid = el("div", "groups");
  const refresh = () => {
    const terms = searchTerms(state.filter);
    const shown = new Set();
    grid.replaceChildren();
    for (const group of groups) {
      const groupMatches = terms.length > 0 && terms.every((term) => group.title.toLowerCase().includes(term));
      const tools = group.tools.filter(
        (item) =>
          (state.show === "all" || (state.show === "installed") === item.installed) &&
          (groupMatches || terms.every((term) => item.tool.toLowerCase().includes(term))),
      );
      if (tools.length === 0) continue;
      const installed = group.tools.filter((item) => item.installed).length;
      const meter = el("div", "meter dense");
      const fill = el("span");
      fill.style.width = `${(installed / group.tools.length) * 100}%`;
      meter.append(fill);
      const head = el("div", "group-head");
      head.append(el("span", "group-title", group.title), meter, el("span", "group-count", `${installed}/${group.tools.length}`));
      const pills = el("div", "pills");
      for (const item of tools) {
        shown.add(item.tool);
        const pill = el("span", item.installed ? "pill" : "pill absent");
        pill.title = item.installed ? "Installed" : "Not installed";
        pill.append(mark(item.installed ? "good" : "muted"), item.tool);
        pills.append(pill);
      }
      const card = el("div", "group");
      card.append(head, pills);
      grid.append(card);
    }
    count.textContent = `${shown.size} of ${unique.size} tools`;
    if (shown.size === 0) grid.append(el("p", "lede", "No tools match these filters."));
  };
  for (const [value, label, total] of [["all", "All", unique.size], ["installed", "Installed", installedTotal], ["absent", "Not installed", unique.size - installedTotal]]) {
    const button = el("button", "chip");
    button.type = "button";
    button.setAttribute("aria-pressed", String(state.show === value));
    button.append(el("span", "", label), el("span", "chip-count", String(total)));
    button.addEventListener("click", () => {
      state.show = value;
      for (const sibling of modes.children) sibling.setAttribute("aria-pressed", String(sibling === button));
      refresh();
    });
    modes.append(button);
  }
  filter.addEventListener("input", () => {
    state.filter = filter.value;
    refresh();
  });
  const controls = el("div", "controls");
  controls.append(filter, modes, count);
  refresh();
  return [progress(installedTotal, unique.size, `${installedTotal} of ${unique.size} catalog tools installed`), controls, grid];
}

function presence(present) {
  return present ? statusLabel("good", "present") : statusLabel("muted", "absent");
}

function renderConfigs(details) {
  const managedRows = details.managed_files.map((file) => [
    el("span", "name", file.name),
    statusLabel(MANAGED_TONES[file.state], file.state),
    presence(file.schema_present),
    presence(file.local_schema_present),
    pathCode(file.data_path),
  ]);
  const managed = el("div", "block");
  managed.append(
    el("h3", "", "Managed files"),
    simpleTable(["File", "State", "Schema", "Local schema", "Data path"], managedRows, "No managed files"),
  );
  if (!details.mappings) return [managed];
  const mappings = details.mappings;
  const state = { filter: "", statuses: new Set() };
  const statusCounts = new Map();
  for (const item of mappings.items) statusCounts.set(item.status, (statusCounts.get(item.status) ?? 0) + 1);
  const options = [...statusCounts]
    .sort((left, right) => (right[0] === "Configured") - (left[0] === "Configured") || right[1] - left[1])
    .map(([status, total]) => [status, status, total]);
  const filter = searchInput("Filter mappings");
  const count = el("span", "count");
  const host = el("div");
  const refresh = () => {
    const terms = searchTerms(state.filter);
    const items = mappings.items.filter((item) => {
      const text = `${item.program} ${item.file_name} ${item.method} ${item.status} ${item.default_path} ${item.managed_path}`.toLowerCase();
      return (state.statuses.size === 0 || state.statuses.has(item.status)) && terms.every((term) => text.includes(term));
    });
    count.textContent = `${items.length} of ${mappings.items.length}`;
    const rows = items.map((item) => [
      el("span", "name", item.program),
      item.file_name,
      item.method,
      statusLabel(item.status === "Configured" ? "good" : item.status === "Not configured" ? "muted" : "warn", item.status),
      pathCode(item.default_path),
      pathCode(item.managed_path),
    ]);
    host.replaceChildren(simpleTable(["Program", "File", "Method", "Status", "Default path", "Managed path"], rows, "No mappings match these filters"));
  };
  filter.addEventListener("input", () => {
    state.filter = filter.value;
    refresh();
  });
  const controls = el("div", "controls");
  controls.append(filter, chipGroup(options, state.statuses, refresh), count);
  refresh();
  const mapped = el("div", "block");
  mapped.append(
    el("h3", "", "Configuration mappings"),
    progress(mappings.linked, mappings.count, `${mappings.linked} of ${mappings.count} mappings configured across ${mappings.program_count} programs`),
    controls,
    host,
  );
  return [managed, mapped];
}
