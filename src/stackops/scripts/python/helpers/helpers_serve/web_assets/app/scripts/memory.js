const OPTIONS_KEY = "stackops-serve-options";
const RECENT_KEY = "stackops-serve-recent";
const RECENT_LIMIT = 6;
// A bearer token or password typed into a read-only view stays out of the browser's storage.
const SECRET_NAME = /key|token|password|pwd|secret/i;

const readOptions = () => JSON.parse(localStorage.getItem(OPTIONS_KEY) ?? "{}");

// What a read-only view was last set to, by parameter name. Design choice: tools that change things never call this, so no destructive form opens pre-filled.
export const recall = (id) => new Map(Object.entries(readOptions()[id] ?? {}));

export function remember(id, values) {
  const options = readOptions();
  const kept = [...values].filter(([name]) => !SECRET_NAME.test(name));
  if (kept.length > 0) options[id] = Object.fromEntries(kept);
  else delete options[id];
  localStorage.setItem(OPTIONS_KEY, JSON.stringify(options));
}

// The last few tools opened, newest first; ⌘K lists them.
export function noteOpened(path) {
  const earlier = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
  localStorage.setItem(RECENT_KEY, JSON.stringify([path, ...earlier.filter((item) => item !== path)].slice(0, RECENT_LIMIT)));
}
