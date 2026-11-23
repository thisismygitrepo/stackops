import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { RISKS, actionText, adminText, categoryOf, codeNodes, estimateText, firstSentence, plainNote, qualifierNoteOf, qualifierOf, quietReason, sizeText } from "./disk_cleanup_words.js";
import { button, keyValue } from "./widgets.js";
import { plural } from "./words.js";

const LIST_PREVIEW = 6;
const LIST_LIMIT = 200;

export const isMeasured = (target) => target.phase === "done" && target.status === "ready";
// A place that took too long to measure can still be cleaned: the cleanup measures it again, without a time limit.
export const canPick = (target) => isMeasured(target) || (target.phase === "error" && target.slow);
export const isQuiet = (target) => target.phase === "done" && target.status !== "ready";
// A place that failed to measure keeps the size it had before, so only measured places count.
export const total = (targets) => targets.reduce((sum, target) => sum + (isMeasured(target) ? target.bytes : 0), 0);

// A list inside a place's details: the biggest few entries, then up to `LIST_LIMIT` on request. `view.open` holds, for each place whose details
// are open, how many entries each of its lists shows, so both survive the rows being rebuilt.
function foldedList(target, view, { part, heading, entries, count, line, together }) {
  const shown = view.open.get(target.key);
  const list = h("ul", { class: "cleanup-paths" });
  const more = h("button", { class: "link", type: "button", text: count > LIST_LIMIT ? `Show the first ${LIST_LIMIT}` : `Show all ${count}` });
  const paint = () => {
    const limit = shown[part] ?? LIST_PREVIEW;
    const hidden = count - Math.min(limit, count);
    list.replaceChildren(...entries.slice(0, limit).map(line), ...(hidden > 0 && limit === LIST_LIMIT ? [h("li", { class: "dim", text: `…and ${hidden.toLocaleString()} more` })] : []));
    more.hidden = limit === LIST_LIMIT || hidden === 0;
  };
  more.addEventListener("click", () => {
    shown[part] = LIST_LIMIT;
    paint();
  });
  paint();
  return h("div", { class: "cleanup-inside" }, h("h4", { text: heading }), list, more, together && h("p", { class: "dim", text: "These are removed together: ticking this place removes all of them." }));
}

const pathList = (target, view) =>
  foldedList(target, view, {
    part: "paths", heading: target.paths.length > LIST_PREVIEW ? "Biggest items inside" : "What is removed", entries: target.paths, count: target.paths.length,
    line: (entry) => h("li", {}, h("code", { class: "path", text: tildify(entry.path, state.boot.home) }), h("b", { class: "num", text: sizeText(entry.bytes) })),
    together: target.paths.length > 1 && target.commands.length === 0,
  });

// What a place is made of, as the scan reports it for that kind of place: Docker's images or volumes, what Homebrew removes, the biggest things in a folder.
const itemList = (target, view) =>
  foldedList(target, view, {
    part: "items", heading: target.details.title, entries: target.details.items, count: target.details.count,
    line: (item) =>
      h("li", {}, h("span", { class: "cleanup-item" }, h("code", { class: "path", text: tildify(item.name, state.boot.home) }), item.note && h("small", { text: item.note })), h("b", { class: "num", text: item.bytes === null ? "Size unknown" : sizeText(item.bytes) })),
    together: target.details.count > 1 && target.paths.length === 0,
  });

function detail(target, view, restored) {
  const measured = isMeasured(target);
  return h(
    "div",
    { class: `cleanup-detail${restored ? " restored" : ""}` },
    h("p", { class: "cleanup-note" }, codeNodes(plainNote(target.note))),
    keyValue([
      ["What happens", measured && actionText(target)],
      ["How much", measured && target.sized && qualifierOf(target) && `${estimateText(target)}. ${qualifierNoteOf(target)}`],
      ["How risky", `${RISKS[target.risk].label}. ${RISKS[target.risk].hint}`],
      ["Permission", target.requires_root && adminText(state.boot.platform)],
    ].filter(([, value]) => value)),
    measured && target.paths.length > 0 && pathList(target, view),
    measured && target.details && itemList(target, view),
  );
}

function sizeCell(target, view) {
  if (target.phase === "error") {
    return h("div", { class: "cleanup-size" }, h("span", { class: "dim", text: target.slow ? "Took too long to measure" : "Not measured" }), button({ label: "Try again", glyph: "refresh", small: true, onclick: () => view.retry(target.key) }));
  }
  if (target.phase !== "done") return h("div", { class: "cleanup-size pending" }, target.phase === "measuring" && h("i", { class: "ring" }), h("span", { text: target.phase === "measuring" ? "Measuring" : "In line" }));
  if (!target.sized) return h("div", { class: "cleanup-size" }, h("span", { class: "dim", text: "Size unknown" }));
  return h(
    "div",
    { class: "cleanup-size" },
    h("span", { class: "cleanup-amount" }, qualifierOf(target) && h("small", { text: qualifierOf(target) }), h("strong", { class: "num", text: sizeText(target.bytes) })),
    h("i", { class: "cleanup-weight", style: `--share:${view.scale ? Math.max(target.bytes / view.scale, 0.012) : 0}` }),
  );
}

export function targetRow(target, view) {
  const risk = RISKS[target.risk];
  const pickable = canPick(target);
  const key = target.key;
  const box = h("input", { class: "cleanup-check", type: "checkbox", "data-part": "check", "aria-label": `Remove ${target.title}`, disabled: !pickable || view.locked });
  box.checked = view.picked.has(key);
  box.addEventListener("change", () => view.toggle(key, box.checked));
  const more = h("button", { class: "icon-btn cleanup-more", type: "button", "data-part": "more", "aria-expanded": "false", title: "What this is and what is inside", "aria-label": `Details for ${target.title}` }, icon("down", 16));
  const slowText = `${target.action_kind === "projects" ? "The search for projects took too long: pick a project folder under Options. " : ""}It can still be removed; its size shows up afterwards.`;
  const summary = target.phase === "error" ? [target.slow ? slowText : target.problem] : codeNodes(firstSentence(target.note));
  const main = h(
    "div",
    { class: "cleanup-main" },
    box,
    h("div", { class: "cleanup-text" }, h("strong", { text: target.title }), h("span", {}, view.order === "size" && h("em", { class: "cleanup-kind", text: categoryOf(target.category).title }), summary)),
    target.requires_root && h("span", { class: "pill cleanup-admin", title: adminText(state.boot.platform) }, icon("lock", 12), "Needs admin"),
    h("span", { class: `pill ${risk.tone}`, title: risk.hint, text: risk.label }),
    sizeCell(target, view),
    more,
  );
  const row = h("li", { class: `cleanup-row${box.checked ? " picked" : ""}${pickable ? "" : " unpickable"}${target.phase === "error" && !target.slow ? " failed" : ""}`, "data-key": key }, main);
  // Details that were open before the rows were rebuilt come back in place, without sliding in again.
  const setOpen = (open, restored) => {
    more.setAttribute("aria-expanded", String(open));
    row.querySelector(".cleanup-detail")?.remove();
    if (open) row.append(detail(target, view, restored));
  };
  more.addEventListener("click", () => {
    const open = !view.open.has(key);
    if (open) view.open.set(key, {});
    else view.open.delete(key);
    setOpen(open, false);
  });
  main.addEventListener("click", (event) => {
    if (event.target.closest("button, input") || !pickable || view.locked) return;
    box.checked = !box.checked;
    view.toggle(key, box.checked);
  });
  setOpen(view.open.has(key), true);
  return { row, box };
}

export function quietFold(targets, open, onToggle) {
  const fold = h(
    "details",
    { class: "fold cleanup-quiet", open },
    h("summary", {}, icon("chevron", 14), h("span", { text: `Nothing to free in ${plural(targets.length, "other place")}` })),
    h(
      "ul",
      {},
      targets.map((target) => {
        const reason = quietReason(target);
        return h("li", {}, h("strong", { text: target.title }), h("span", { class: "dim", text: reason.label }), reason.detail && h("small", { class: "dim", title: reason.detail, text: reason.detail }));
      }),
    ),
  );
  fold.addEventListener("toggle", () => onToggle(fold.open));
  return fold;
}
