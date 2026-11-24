import { h } from "/assets/scripts/dom.js";
import { button, callout, copyChip, notice } from "../../widgets.js";
import { formatBytes } from "../../words.js";
import { stepTitle } from "./kit.js";
import { COLLECT_PATH, LEFT_OUT, SYNC_PATH, count } from "./words.js";

const PART_HUES = [252, 200, 155, 30, 330, 290, 100];
// The statuses of a listed file whose newest version is on this machine only, so an archive made now would carry an older one or none.
const UNSAVED = ["Copy differs", "Contents differ", "Missing managed path"];

// The folder's parts, largest first, as one bar and a legend under it. Parts beyond the colours there are go into one last row.
function partsPicture(plan) {
  const named = plan.parts.slice(0, PART_HUES.length - 1);
  const rest = plan.parts.slice(named.length);
  const rows = [
    ...named.map((part, index) => ({ ...part, label: part.name || "Loose files at the top", hue: PART_HUES[index] })),
    ...(rest.length > 0 ? [{ label: count(rest.length, "smaller folder", "smaller folders"), files: rest.reduce((total, part) => total + part.files, 0), size_bytes: rest.reduce((total, part) => total + part.size_bytes, 0), hue: PART_HUES.at(-1) }] : []),
  ];
  const share = (row) => (plan.size_bytes > 0 ? (row.size_bytes / plan.size_bytes) * 100 : 100 / rows.length);
  return [
    h("div", { class: "dotfiles-bar", role: "img", "aria-label": "How the folder's size splits over its parts" }, rows.map((row) => h("i", { style: `--hue:${row.hue};flex-grow:${Math.max(share(row), 0.6)}`, title: `${row.label}: ${formatBytes(row.size_bytes)}` }))),
    h(
      "ul",
      { class: "dotfiles-parts" },
      rows.map((row) =>
        h(
          "li",
          {},
          h("i", { class: "dotfiles-dot", style: `--hue:${row.hue}` }),
          h("strong", { text: row.label }),
          h("span", { class: "dim", text: count(row.files, "file", "files") }),
          h("span", { class: "dotfiles-part-meter" }, h("i", { style: `--hue:${row.hue};width:${Math.max(share(row), 1)}%` })),
          h("span", { class: "num", text: formatBytes(row.size_bytes) }),
        ),
      ),
    ),
  ];
}

// What the page has to say about the archive beyond its size: whether the list travels, what stays behind and why, and what on this machine
// is newer than its kept copy. `status` is the answer of the status command, or null while it is on its way or when it could not be read.
function remarks({ plan, status, tools }) {
  const outside = status?.storage?.outside_dotfiles_root?.length ?? 0;
  const unsaved = status?.sync?.user?.filter((entry) => UNSAVED.includes(entry.status)).length ?? 0;
  return [
    plan.list_inside
      ? callout({ tone: "", title: "Your list of managed files goes with it", text: "The other machine learns from it where each file belongs." })
      : callout({ tone: "warn", title: "There is no list of managed files in this folder", text: "The files travel, but the other machine will not know where each one belongs. Collect your settings first to make the list." }),
    ...plan.left_out.map((item) =>
      callout({
        tone: "warn", title: `${count(item.count, LEFT_OUT[item.reason].one, LEFT_OUT[item.reason].many)} left out`, text: LEFT_OUT[item.reason].why,
        extra: h("div", { class: "dotfiles-examples" }, item.examples.map((path) => copyChip(path)), item.count > item.examples.length && h("span", { class: "dim", text: `and ${item.count - item.examples.length} more` })),
      }),
    ),
    outside > 0 && callout({ tone: "warn", title: `${count(outside, "managed file is", "managed files are")} kept outside this folder`, text: "The archive holds this folder only, so those stay behind. The Dotfiles page shows where each is kept." }),
    unsaved > 0 &&
      callout({
        tone: "warn", title: `${count(unsaved, "file is", "files are")} newer on this machine than the kept copy`, text: "The archive is made from the kept copies. Save from this machine first if the newer versions should travel.",
        extra: button({ label: "Save from this machine", glyph: "up", small: true, onclick: () => tools.open(SYNC_PATH, { preset: { direction: "up" } }) }),
      }),
  ];
}

export function contentsCard({ plan, status, tools }) {
  if (!plan.exists || plan.files === 0) {
    return h(
      "section",
      { class: "dotfiles-card" },
      notice({
        glyph: "folder", title: plan.exists ? "The dotfiles folder is empty" : "There is no dotfiles folder on this machine yet",
        body: "There is nothing to move. Collecting your settings fills the folder and writes the list of what is in it.",
        action: button({ label: "Collect my settings", glyph: "plus", small: true, onclick: () => tools.open(COLLECT_PATH) }),
      }),
    );
  }
  return h(
    "section",
    { class: "dotfiles-card" },
    stepTitle(1, "What goes in"),
    h("p", { class: "dotfiles-total" }, h("strong", { text: count(plan.files, "file", "files") }), h("span", { text: ` · ${formatBytes(plan.size_bytes)} before packing · the whole folder, nothing picked out` })),
    partsPicture(plan),
    h("div", { class: "dotfiles-remarks" }, remarks({ plan, status, tools })),
  );
}
