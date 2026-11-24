import { KINDS, MANNERS, SCOPES, whoseWords } from "./words.js";

// Off comes first: an entry that is turned off is not loaded, and saying "not running" about it would hide the reason.
const stateOf = (entry) => (!entry.enabled ? "off" : entry.live === "running" ? "running" : entry.live === "unknown" ? "" : entry.last_exit > 0 ? "trouble" : "resting");

export function buildModel(picture) {
  const entries = picture.entries.map((entry) => ({
    ...entry,
    state: stateOf(entry),
    hay: [entry.title, entry.name, entry.description, entry.source, entry.owner, entry.program, entry.file].join("\n").toLowerCase(),
  }));
  return { platform: picture.platform, notes: picture.notes, entries, readAt: Date.now(), tellsState: entries.some((entry) => entry.state !== "") };
}

// The ways the list can be narrowed, each by one fact about an entry. Several values of one fact widen it, different facts narrow it.
export const FACETS = {
  scopes: (entry) => entry.scope,
  manners: (entry) => entry.manner,
  whose: (entry) => entry.whose,
  kinds: (entry) => entry.category,
  states: (entry) => entry.state,
};

export const emptyPicks = () => Object.fromEntries(Object.keys(FACETS).map((id) => [id, new Set()]));
export const isNarrowed = (view) => view.term.trim() !== "" || Object.values(view.picks).some((picked) => picked.size > 0);

// What the page is about: everything, or everything but the standard parts of the system. The picture at the top counts these.
export const inUniverse = (model, view) => model.entries.filter((entry) => view.system || !entry.stock);

export function matching(model, view) {
  const term = view.term.trim().toLowerCase();
  return inUniverse(model, view).filter((entry) => (!term || entry.hay.includes(term)) && Object.entries(FACETS).every(([id, of]) => view.picks[id].size === 0 || view.picks[id].has(of(entry))));
}

export function tally(entries, of) {
  const counts = new Map();
  for (const entry of entries) counts.set(of(entry), (counts.get(of(entry)) ?? 0) + 1);
  return counts;
}

const byTitle = (left, right) => left.title.localeCompare(right.title, undefined, { sensitivity: "base" }) || left.name.localeCompare(right.name);
const STATE_RANK = { running: 0, trouble: 1, resting: 2, "": 3, off: 4 };
const ORDER = {
  name: byTitle,
  // Entries nobody can be named for go last.
  owner: (left, right) => (left.owner === "") - (right.owner === "") || left.owner.localeCompare(right.owner, undefined, { sensitivity: "base" }) || byTitle(left, right),
  running: (left, right) => STATE_RANK[left.state] - STATE_RANK[right.state] || byTitle(left, right),
};

// The list in sections, by what `view.group` says. A section nothing falls in is left out.
export function groupsOf(entries, view, platform) {
  const whose = whoseWords(platform);
  const plans = {
    when: Object.keys(SCOPES).flatMap((scope) =>
      Object.keys(MANNERS).map((manner) => ({ id: `${scope} ${manner}`, title: `${SCOPES[scope].label}, ${MANNERS[manner].lower}`, hint: MANNERS[manner].hint, glyph: SCOPES[scope].glyph, has: (entry) => entry.scope === scope && entry.manner === manner })),
    ),
    whose: Object.keys(whose).map((id) => ({ id, title: whose[id].label, hint: whose[id].hint, has: (entry) => entry.whose === id })),
    kind: Object.keys(KINDS).map((id) => ({ id, title: KINDS[id].long, hint: "", glyph: KINDS[id].glyph, has: (entry) => entry.category === id })),
    none: [{ id: "all", title: "", hint: "", has: () => true }],
  };
  const sorted = [...entries].sort(ORDER[view.order]);
  return plans[view.group].map((plan) => ({ ...plan, entries: sorted.filter(plan.has) })).filter((group) => group.entries.length > 0);
}
