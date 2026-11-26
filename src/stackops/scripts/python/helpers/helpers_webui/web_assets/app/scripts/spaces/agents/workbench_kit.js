import { h, icon, tildify } from "/assets/scripts/dom.js";
import { on, state } from "/assets/scripts/state.js";
import { rise } from "../../motion.js";
import { toolButton } from "../../space_kit.js";
import { emojiTile, sectionHead, stat } from "../../widgets.js";
import { friendlyText, titleOf } from "../../words.js";

const INSTALL_TOOL = "devops software install";
const SAVED_PROFILES_FOLDER = "browsers-profiles";
const START_SETTLE_MILLISECONDS = 3000;

export const isRunning = (activity, path) => activity.runs().some((run) => run.exit_code === null && run.arguments.join(" ").startsWith(path));

// A tool that keeps serving (desktop control, a model server) never ends, so the refresh signal that follows a finished run never comes for it.
// The panel that says whether it is up therefore looks again a few seconds after a run of that tool starts, on show or not.
// A design choice: one look and no polling. A tool slower to come up than that still reads as off until the refresh button is pressed.
export function reloadAfterStart(activity, path, panel) {
  let alive = false;
  on("runs", () => {
    const now = isRunning(activity, path);
    if (now && !alive) setTimeout(() => panel.load(true), START_SETTLE_MILLISECONDS);
    alive = now;
  });
}

// `ask` is the area's "Ask an agent" button, which stands first.
export function areaHead({ title, lede, actions = [], ask }) {
  return h("header", { class: "wb-head" }, h("div", { class: "wb-head-text" }, h("h2", { text: title }), h("p", { text: lede })), h("div", { class: "view-actions" }, ask, actions));
}

// A tool card with its own plain wording and starting values. `caution` marks tools that delete things: they still only open the sheet.
function actionCard(tools, { path, title, blurb, preset = {}, caution = "" }) {
  const node = state.nodes.get(path);
  return (
    node &&
    h(
      "button",
      { class: "tool-card lit", type: "button", onclick: () => tools.open(path, { preset }) },
      emojiTile(node.icon || "✨", path, 40),
      h("span", { class: "tool-card-text" }, h("strong", { text: title ?? titleOf(node) }), h("span", { text: blurb ?? friendlyText(node.summary) }), caution && h("em", {}, icon("alert", 12), caution)),
      icon("arrow", 14),
    )
  );
}

export function actionBlock(tools, title, items) {
  return h("section", { class: "block" }, sectionHead(title), h("div", { class: "tool-grid" }, items.map((item) => actionCard(tools, item))));
}

export function installButton(tools, name, label) {
  return toolButton(tools, INSTALL_TOOL, { label, glyph: "download", tone: "primary", preset: { which: name } });
}

// One thing that is on, off or in trouble: a toned badge, what that means, and what to do about it.
export function stateCard({ tone = "", glyph, title, body, children = [], actions = [] }) {
  return h(
    "div",
    { class: `wb-state ${tone}` },
    h("span", { class: "wb-state-glyph" }, icon(glyph, 22)),
    h("div", { class: "wb-state-text" }, h("h3", { text: title }), body && h("p", { text: body }), children),
    actions.length > 0 && h("div", { class: "wb-state-actions" }, actions),
  );
}

// A path that wraps at its slashes instead of in the middle of a name, and still copies as plain text.
export function pathText(path) {
  const parts = tildify(String(path), state.boot.home).split("/");
  return h("code", { class: "path wb-path", title: String(path) }, parts.flatMap((part, index) => (index < parts.length - 1 ? [`${part}/`, h("wbr")] : [part])));
}

// The top of a .wb-card: a tile, a name with one dim line under it, and a pill where the card has a state.
export function cardHead(tile, title, sub, pill) {
  return h("header", {}, tile, h("div", {}, h("h3", { text: title }), h("span", { class: "dim", text: sub })), pill);
}

// The name of a profile saved for agents: the last part of a path inside the saved-profiles folder. Any other profile has none.
export function savedProfileName(path) {
  const parts = String(path).split(/[\\/]/);
  return parts.includes(SAVED_PROFILES_FOLDER) ? parts.at(-1) : null;
}

export function statusPill(label, tone, glyph) {
  return h("span", { class: `pill ${tone}` }, glyph && icon(glyph, 12), h("span", { text: label }));
}

// A row of figures, each { glyph, hue, label, value, note }. They count up once the row is on the page.
export function statRow(tiles) {
  const made = tiles.map((tile) => stat(tile));
  requestAnimationFrame(() => made.forEach((item, index) => item.set(tiles[index].value, tiles[index].note)));
  return rise(h("div", { class: "stats" }, made.map((item) => item.element)));
}

// The first rows in view, the rest behind "and N more".
export function previewList(rows, limit, line) {
  return [
    h("ul", {}, rows.slice(0, limit).map(line)),
    rows.length > limit && h("details", { class: "wb-more" }, h("summary", { text: `and ${rows.length - limit} more` }), h("ul", {}, rows.slice(limit).map(line))),
  ];
}

// Rows of name, bar and figure on one shared scale, longest first.
export function barList(rows) {
  const top = Math.max(...rows.map((row) => row.value), 1);
  return h(
    "ul",
    { class: "wb-bars" },
    rows.map((row, index) =>
      h(
        "li",
        { title: `${row.label}: ${row.value.toLocaleString()}` },
        h("span", { class: "wb-bar-name", text: row.label }),
        h("span", { class: "wb-bar-track" }, h("i", { style: `--share:${row.value / top};--i:${index}` })),
        h("span", { class: "wb-bar-value num", text: row.value.toLocaleString() }),
      ),
    ),
  );
}

export function tally(items, keyOf) {
  const counts = new Map();
  for (const item of items) counts.set(keyOf(item), (counts.get(keyOf(item)) ?? 0) + 1);
  return [...counts].map(([label, value]) => ({ label, value })).sort((first, second) => second.value - first.value);
}

export const compact = (value) => new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(value);
