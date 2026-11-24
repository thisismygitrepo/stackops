import { h } from "/assets/scripts/dom.js";
import { rise } from "../../../motion.js";
import { button, notice } from "../../../widgets.js";
import { diskCard, rankedCard, sharesCard } from "./disk_card.js";
import { groupsOf, matcher, ranked, rowsOf } from "./model.js";

// The disks and what is on them, as cards by disk or as one ranked list. `render` rebuilds it from the picture and the page's choices;
// `entering` plays the cards' entrance, which a rebuild after typing or a refresh in place leaves out.
export function createDeviceList(view, handlers) {
  const element = h("div", { class: "devices-list" });

  function render(picture, platform, entering) {
    const groups = groupsOf(picture);
    const every = rowsOf(groups);
    const shown = every.filter(matcher(view));
    const options = { view, platform, handlers, ranked: false };
    const narrowed = view.state !== "all" || view.term.trim() !== "";
    let content;
    if (every.length === 0 && groups.length === 0) {
      content = [notice({ glyph: "database", title: "No disks were found", body: "This system shows no storage to StackOps. Inside a container or a locked-down account that is expected." })];
    } else if (view.order === "disk") {
      content = groups
        .filter((group) => view.place === "all" || group.place === view.place)
        .map((group) => [group, shown.filter((row) => row.group === group)])
        .filter(([, rows]) => rows.length > 0 || !narrowed)
        .map(([group, rows]) => (group.disk ? diskCard(group, rows, options) : sharesCard(group, rows, options)));
    } else {
      content = shown.length ? [rankedCard(ranked(shown, view.order), options)] : [];
    }
    if (content.length === 0) {
      content = [notice({ glyph: "search", title: "Nothing matches", body: "No disk or volume fits what is chosen above.", action: button({ label: "Show everything", small: true, onclick: handlers.clearFilters }) })];
    }
    element.replaceChildren(...content);
    if (entering) rise(element);
  }

  return { element, render };
}
