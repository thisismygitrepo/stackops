import { h } from "/assets/scripts/dom.js";
import { canPick, isMeasured, isQuiet, quietFold, targetRow } from "./disk_cleanup_rows.js";
import { CATEGORY_ORDER, categoryOf, sizeText } from "./disk_cleanup_words.js";
import { button, glyphTile, notice, skeleton } from "./widgets.js";

const total = (targets) => targets.reduce((sum, target) => sum + target.bytes, 0);
const isWaiting = (target) => target.phase !== "done" && target.phase !== "error";
// Places still being measured stay on top: the slow ones are usually the big ones, so they barely move once their size arrives.
const rankOf = (target) => (isWaiting(target) || target.slow ? 0 : target.phase === "error" ? 2 : 1);

// The places that can be cleaned, grouped by kind. `render` rebuilds the rows; `syncPicks` only updates what a tick changes, so ticking never rebuilds anything.
export function createCleanupList(view) {
  const element = h("div", { class: "cleanup-list" });
  const rows = new Map();
  const groups = [];
  let quietOpen = false;

  function group(category, members) {
    const meta = categoryOf(category);
    const sum = h("strong", { class: "num" });
    const hint = h("span");
    const all = button({ label: "Select all", small: true, tone: "ghost", onclick: () => view.setMany(members.filter(canPick).map((target) => target.key), true) });
    const none = button({ label: "Clear", small: true, tone: "ghost", onclick: () => view.setMany(members.map((target) => target.key), false) });
    const items = [...members]
      .sort((left, right) => rankOf(left) - rankOf(right) || right.bytes - left.bytes)
      .map((target) => {
        const built = targetRow(target, view);
        rows.set(target.key, built);
        return built.row;
      });
    groups.push({ members, sum, hint, all, none });
    return h(
      "section",
      { class: "cleanup-group", "data-category": category },
      h("header", { class: "cleanup-group-head" }, glyphTile(meta.glyph, meta.hue, 40), h("div", { class: "cleanup-group-text" }, h("h2", { text: meta.title }), h("p", { text: meta.blurb })), h("div", { class: "cleanup-group-sum" }, sum, hint), all, none),
      h("ul", { class: "cleanup-rows" }, items),
    );
  }

  function syncPicks() {
    for (const [key, { row, box }] of rows) {
      box.checked = view.picked.has(key);
      row.classList.toggle("picked", box.checked);
    }
    for (const { members, sum, hint, all, none } of groups) {
      const pickable = members.filter(canPick);
      const chosen = pickable.filter((target) => view.picked.has(target.key));
      const waiting = members.filter(isWaiting).length;
      sum.textContent = pickable.length || !waiting ? sizeText(total(members.filter(isMeasured))) : "";
      hint.textContent = chosen.length ? `${chosen.length} of ${pickable.length} ticked · ${sizeText(total(chosen))}` : waiting ? `${waiting} still being measured` : `${pickable.length} place${pickable.length === 1 ? "" : "s"}`;
      all.disabled = view.locked || pickable.length === 0 || chosen.length === pickable.length;
      none.disabled = view.locked || chosen.length === 0;
    }
  }

  function render(targets) {
    const focused = document.activeElement instanceof HTMLElement && element.contains(document.activeElement) ? document.activeElement : null;
    const focusKey = focused?.closest("[data-key]")?.dataset.key;
    const listed = targets.filter((target) => !isQuiet(target));
    const shown = listed.filter(view.matches);
    const quiet = targets.filter(isQuiet);
    view.scale = Math.max(0, ...listed.filter(isMeasured).map((target) => target.bytes));
    rows.clear();
    groups.length = 0;
    const order = [...new Set([...CATEGORY_ORDER, ...shown.map((target) => target.category)])];
    const sections = order.map((category) => [category, shown.filter((target) => target.category === category)]).filter(([, members]) => members.length).map(([category, members]) => group(category, members));
    let empty = null;
    if (view.loading) empty = h("div", { class: "cleanup-loading" }, skeleton(6, "row"));
    else if (listed.length === 0) empty = notice({ glyph: "check", tone: "good", title: "Nothing worth cleaning", body: "Every place that usually collects clutter is already clean." });
    else if (shown.length === 0) empty = notice({ glyph: "search", title: "Nothing matches", body: "No place fits that filter.", action: button({ label: "Show everything", small: true, onclick: view.clearFilters }) });
    element.replaceChildren(...sections, ...(empty ? [empty] : []), ...(quiet.length && !view.loading ? [quietFold(quiet, quietOpen, (open) => (quietOpen = open))] : []));
    syncPicks();
    if (focusKey) element.querySelector(`[data-key="${CSS.escape(focusKey)}"] [data-part="${focused.dataset.part}"]`)?.focus({ preventScroll: true });
  }

  return { element, render, syncPicks };
}
