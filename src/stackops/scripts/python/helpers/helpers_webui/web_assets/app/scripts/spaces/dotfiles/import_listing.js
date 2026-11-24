import { h, icon } from "/assets/scripts/dom.js";
import { button, callout, highlight, notice, searchInput, segmented } from "../../widgets.js";
import { formatBytes } from "../../words.js";
import { EXPORT_HASH, count, lossOf } from "./words.js";

const ROW_STEP = 150;
// What becomes of a file, in the order the page shows them: what is lost first.
const FATES = [
  { id: "removed", label: "Only here", verb: "will be removed", tone: "bad" },
  { id: "replaced", label: "Differs", verb: "will be replaced", tone: "warn" },
  { id: "new", label: "New", verb: "will be added", tone: "good" },
  { id: "same", label: "The same", verb: "stays as it is", tone: "" },
];
const STEPS = ["Say where the settings come from", "Type the archive's password", "Look inside. Nothing changes until you say so"];

// What the main column shows before an archive was looked into: where this machine stands, and the three steps.
export function idleCard({ machine, looking, problem }) {
  const here = machine.exists && machine.files > 0;
  return h(
    "section",
    { class: "dotfiles-card" },
    callout({
      tone: here ? "warn" : "", title: here ? `This machine has a dotfiles folder with ${count(machine.files, "file", "files")} (${formatBytes(machine.size_bytes)})` : "This machine has no dotfiles yet",
      text: here ? "Bringing settings in replaces the whole folder. Look inside first to see what that changes." : "Nothing here can be lost. What comes in becomes this machine's dotfiles folder.",
    }),
    looking
      ? h("div", { class: "dotfiles-idle" }, h("i", { class: "ring" }), h("h2", { text: "Opening the archive…" }), h("p", { text: "It is opened in a scratch folder and compared with what is here. Nothing is unpacked." }))
      : problem
        ? notice({ glyph: "alert", tone: "bad", title: "The archive could not be opened", body: problem })
        : h(
            "div",
            { class: "dotfiles-idle" },
            h("span", { class: "dotfiles-idle-glyph" }, icon("eye", 26)),
            h("h2", { text: "See what is inside first" }),
            h("ol", { class: "dotfiles-steps" }, STEPS.map((text) => h("li", {}, h("div", {}, h("p", { text }))))),
          ),
  );
}

// What bringing the archive in would change: how many files of each kind as a bar and four tiles that filter, the files themselves, and the
// button that does it. `view` holds the filter, the search text and the order, kept by the page so a fresh look keeps them.
export function listingCard({ listing, source, view, busy, onApply }) {
  const total = FATES.reduce((sum, fate) => sum + listing.counts[fate.id], 0);
  const lost = listing.counts.removed + listing.counts.replaced;
  const holder = h("div", { class: "dotfiles-rows" });
  const moreText = h("span");
  const more = h("button", { class: "btn small ghost", type: "button", onclick: () => ((view.limit += ROW_STEP), paint()) }, moreText);
  const apply = button({ label: listing.folder_exists ? "Replace my dotfiles folder with this" : "Put it in place", glyph: "download", tone: listing.folder_exists && lost > 0 ? "danger" : "primary", onclick: onApply });
  apply.disabled = busy;
  const tiles = FATES.map((fate) =>
    h(
      "button",
      { class: `dotfiles-fate ${fate.id}`, type: "button", disabled: listing.counts[fate.id] === 0, onclick: () => ((view.fate = view.fate === fate.id ? "" : fate.id), (view.limit = ROW_STEP), paint()) },
      h("i", { class: "dotfiles-dot" }), h("strong", { class: "num", text: listing.counts[fate.id].toLocaleString() }), h("span", { text: fate.label }), h("small", { text: `${fate.verb} · ${formatBytes(listing.sizes[fate.id])}` }),
    ),
  );
  const order = segmented([["fate", "By what changes"], ["path", "By name"], ["size", "By size"]], (value) => ((view.order = value), paint()));
  const filter = searchInput({ placeholder: "Search the files", oninput: (value) => ((view.term = value), (view.limit = ROW_STEP), paint()) });
  filter.input.value = view.term;

  function paint() {
    const term = view.term.trim().toLowerCase();
    const matched = listing.rows.filter((row) => (view.fate === "" || row.fate === view.fate) && row.path.toLowerCase().includes(term));
    const ordered = view.order === "fate" ? matched : [...matched].sort(view.order === "size" ? (left, right) => right.size_bytes - left.size_bytes : (left, right) => left.path.localeCompare(right.path));
    tiles.forEach((tile, index) => tile.setAttribute("aria-pressed", String(view.fate === FATES[index].id)));
    order.set(view.order);
    holder.replaceChildren(
      ...(ordered.length > 0
        ? ordered.slice(0, view.limit).map((row) => {
            const fate = FATES.find((candidate) => candidate.id === row.fate);
            return h("div", { class: "dotfiles-row" }, h("span", { class: `pill ${fate.tone}`, text: fate.label }), h("span", { class: "dotfiles-row-path", title: row.path }, highlight(row.path, term)), h("span", { class: "num dim", text: formatBytes(row.size_bytes) }));
          })
        : [h("p", { class: "field-hint", text: term ? "No file matches that search." : "No file of that kind." })]),
    );
    more.hidden = ordered.length <= view.limit;
    moreText.textContent = `Show ${Math.min(ROW_STEP, ordered.length - view.limit)} more of ${ordered.length.toLocaleString()}`;
  }

  paint();
  return h(
    "section",
    { class: "dotfiles-card" },
    h("h3", { class: "dotfiles-step-title" }, "What it would change"),
    h("p", { class: "dotfiles-total" }, h("strong", { text: count(total - listing.counts.removed, "file", "files") }), h("span", { text: ` in the archive · ${source}` })),
    h("div", { class: "dotfiles-bar", role: "img", "aria-label": "How many files are removed, replaced, added and left as they are" }, FATES.filter((fate) => listing.counts[fate.id] > 0).map((fate) => h("i", { class: fate.id, style: `flex-grow:${listing.counts[fate.id]}`, title: `${fate.label}: ${listing.counts[fate.id]}` }))),
    h("div", { class: "dotfiles-fates" }, tiles),
    h(
      "div",
      { class: "dotfiles-remarks" },
      callout({
        tone: lost > 0 ? "warn" : "", title: "There is no merging",
        text: !listing.folder_exists
          ? "This machine has no dotfiles folder, so the archive simply becomes it."
          : lost > 0
            ? `The archive takes the place of the whole folder. ${lossOf(listing.counts)}.`
            : "The archive takes the place of the whole folder, and every file here is in it unchanged.",
        extra: lost > 0 && h("a", { class: "btn small", href: EXPORT_HASH }, icon("lock", 14), h("span", { text: "Make an archive of this machine first" })),
      }),
      !listing.has_list && callout({ tone: "warn", title: "The archive holds no list of managed files", text: "The files arrive, but Apply to this machine will have nothing to go by." }),
    ),
    h("div", { class: "table-bar" }, order.element, filter.element),
    holder,
    more,
    listing.rows_cut > 0 && h("p", { class: "field-hint", text: `${count(listing.rows_cut, "more file that stays the same is", "more files that stay the same are")} not listed.` }),
    h("div", { class: "dotfiles-go" }, apply),
  );
}
