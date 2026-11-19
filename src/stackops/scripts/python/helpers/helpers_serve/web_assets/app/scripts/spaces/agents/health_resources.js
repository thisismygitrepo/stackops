import { h, icon } from "/assets/scripts/dom.js";
import { button, copyChip, highlight, notice, pill } from "../../widgets.js";
import { plural } from "../../words.js";
import { KIND_BY_ID, ORIGINS, STATES, groupBySource, shortPath } from "./health_model.js";

const ROW_STEP = 12;
const MOMENT_LIMIT = 8;

const statePill = (id) => pill(STATES[id].label, STATES[id].tone);
const originTag = (origin) => h("span", { class: `origin ${origin}`, title: ORIGINS[origin].hint, text: ORIGINS[origin].label });
const pathChip = (path) => copyChip(path, shortPath(path));

function serverLine(detail) {
  const cut = detail.indexOf(": ");
  return cut < 0 ? "" : `Runs ${detail.slice(cut + 2)}`;
}

function what(row, kind, term) {
  if (row.command) {
    const extra = row.moments.length - MOMENT_LIMIT;
    return h(
      "div",
      { class: "what" },
      h("code", { class: "command", title: row.name }, highlight(row.name, term)),
      h(
        "div",
        { class: "moments" },
        h("span", { class: "dim", text: row.moments.length === 1 ? "Runs at" : `Runs at ${row.moments.length} moments` }),
        row.moments.slice(0, MOMENT_LIMIT).map((moment) => h("span", { class: "health-tag mono", text: moment })),
        extra > 0 && h("span", { class: "health-tag", title: row.moments.slice(MOMENT_LIMIT).join(", "), text: `+${extra} more` }),
      ),
    );
  }
  const detail = kind === "server" ? serverLine(row.detail) : row.detail;
  return h("div", { class: "what" }, h("strong", {}, highlight(row.name, term), row.holdsServers && h("span", { class: "health-tag", title: "Tool servers can be listed in this file.", text: "Tool servers go here" })), detail && h("p", {}, highlight(detail, term)));
}

function line(row, kind, term, grouped) {
  const states = row.command ? [...row.states] : row.state ? [row.state] : [];
  return h(
    "li",
    { class: `health-item${grouped ? " grouped" : ""}${row.present ? "" : " empty"}` },
    what(row, kind, term),
    !grouped && h("div", { class: "where" }, originTag(row.origin), pathChip(row.path)),
    h("div", { class: "states" }, states.map(statePill)),
  );
}

// One kind of thing for one agent, laid out by where it comes from.
export function renderResources({ agent, kind, items, term, hiddenEmpty, onShowEmpty }) {
  const label = KIND_BY_ID[kind];
  if (items.length === 0) {
    const all = agent.items.filter((item) => item.kind === kind);
    const nonePresent = all.every((item) => !item.present);
    const places = `${agent.name} looks in ${plural(all.length, "place")} and found nothing there.`;
    const body = all.length === 0 ? `Nothing of this kind was found for ${agent.name}.` : nonePresent ? places : "Try clearing the search or the source filter.";
    const reveal = nonePresent && hiddenEmpty > 0 && button({ label: hiddenEmpty === 1 ? "Show that place" : "Show those places", small: true, onclick: onShowEmpty });
    return notice({ glyph: label.glyph, title: nonePresent ? `No ${label.one}s` : "Nothing matches these filters", body, action: reveal });
  }
  const groups = groupBySource(items, kind);
  const total = groups.reduce((sum, group) => sum + group.rows.length, 0);
  const list = h("ul", { class: "health-list" });
  const more = h("button", { class: "btn small ghost health-more", type: "button" });
  let limit = ROW_STEP;

  function paint() {
    let room = limit;
    const nodes = [];
    for (const group of groups) {
      if (room <= 0) break;
      const rows = group.rows.slice(0, room);
      room -= rows.length;
      const shared = group.rows.length > 1;
      if (shared) nodes.push(h("li", { class: "health-source" }, icon("folder", 14), pathChip(group.path), originTag(group.origin), h("span", { class: "dim", text: `${plural(group.rows.length, kind === "hook" ? "command" : label.one)} from this file` })));
      nodes.push(...rows.map((row) => line(row, kind, term, shared)));
    }
    list.replaceChildren(...nodes);
    more.hidden = total <= limit;
    more.textContent = `Show ${Math.min(ROW_STEP, total - limit)} more of ${total}`;
  }

  more.addEventListener("click", () => {
    limit += ROW_STEP;
    paint();
  });
  paint();
  return h("div", { class: "health-resources" }, list, more);
}
