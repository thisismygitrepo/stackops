// How much of a window lies on a screen, as an area.
const overlap = (frame, screen) =>
  Math.max(0, Math.min(frame.x + frame.width, screen.x + screen.width) - Math.max(frame.x, screen.x)) * Math.max(0, Math.min(frame.y + frame.height, screen.y + screen.height) - Math.max(frame.y, screen.y));

// Windows keep their place in the list for as long as they are open: the system numbers them as they open, and nothing done to one changes its number.
const byId = (left, right) => left.id.localeCompare(right.id, undefined, { numeric: true });

// The system gives a display no name the page could read cheaply, so each is called by what it is, and numbered when there are two of a kind.
function nameScreens(screens) {
  const kinds = screens.map((screen) => (screen.built_in ? "Built-in display" : "External display"));
  return kinds.map((kind, index) => (kinds.filter((other) => other === kind).length > 1 ? `${kind} ${kinds.slice(0, index + 1).filter((other) => other === kind).length}` : kind));
}

// The server's answer with what the page works out from it. A window is on the screen that holds most of it. `showing` is a window that is
// neither minimized nor hidden with its app; `stray` is one that is showing and yet lies outside every screen, as after a display is unplugged.
// `located` says whether this machine tells where its windows are at all.
export function buildModel(payload) {
  const names = nameScreens(payload.screens);
  const screens = payload.screens.map((screen, index) => ({ ...screen, index, name: names[index] }));
  const windows = payload.windows
    .map((entry) => {
      const area = entry.frame ? entry.frame.width * entry.frame.height : 0;
      const best = entry.frame ? screens.map((screen) => [overlap(entry.frame, screen), screen.index]).sort((left, right) => right[0] - left[0])[0] : null;
      const screen = best && best[0] > 0 ? best[1] : null;
      const showing = !entry.minimized && !entry.hidden;
      return { ...entry, area, screen, showing, stray: showing && area > 0 && screens.length > 0 && screen === null };
    })
    .sort(byId);
  return { windows, screens, blocked: payload.blocked, located: screens.length > 0 };
}

// The choices in the filter row, each with how many windows it holds. One screen, or none the system tells of, gives "On screen"; two or more
// give one choice each. Hidden is only offered while something is hidden.
export function filterChoices(model) {
  const showing = model.windows.filter((entry) => entry.showing);
  const hidden = model.windows.filter((entry) => entry.hidden && !entry.minimized).length;
  const places = model.screens.length > 1 ? model.screens.map((screen) => ({ id: `screen:${screen.index}`, label: screen.name, count: showing.filter((entry) => entry.screen === screen.index).length })) : [{ id: "showing", label: "On screen", count: showing.length }];
  return [
    { id: "all", label: "Everything", count: model.windows.length },
    ...places,
    { id: "minimized", label: "Minimized", count: model.windows.filter((entry) => entry.minimized).length },
    ...(hidden > 0 ? [{ id: "hidden", label: "Hidden", count: hidden }] : []),
  ];
}

// `term` is already in lower case.
export function matches(entry, { filter, app, term }) {
  if (app && entry.app !== app) return false;
  if (term && !`${entry.title} ${entry.app}`.toLowerCase().includes(term)) return false;
  if (filter === "all") return true;
  if (filter === "minimized") return entry.minimized;
  if (filter === "hidden") return entry.hidden && !entry.minimized;
  if (filter === "showing") return entry.showing;
  return entry.showing && `screen:${entry.screen}` === filter;
}

// The list's sections: one per app in alphabetical order, or a single one with the biggest window first, where `app` is empty.
export function arrange(windows, order) {
  if (order === "size") return windows.length ? [{ app: "", members: [...windows].sort((left, right) => right.area - left.area) }] : [];
  const groups = new Map();
  for (const entry of windows) groups.set(entry.app, [...(groups.get(entry.app) ?? []), entry]);
  return [...groups].sort(([left], [right]) => left.localeCompare(right, undefined, { sensitivity: "base" })).map(([app, members]) => ({ app, members }));
}

export function appCounts(model) {
  return arrange(model.windows, "app").map(({ app, members }) => [app, members.length]);
}
