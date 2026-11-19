import { h, icon, tildify } from "/assets/scripts/dom.js";
import { on, state } from "/assets/scripts/state.js";
import { toolButton } from "../../space_kit.js";
import { button, emojiTile, iconButton, notice, sectionHead, skeleton } from "../../widgets.js";
import { friendlyText, titleOf } from "../../words.js";

const INSTALL_TOOL = "devops software install";

// Like createLivePanel, for views that join several read-only commands or must turn a failed command into a "not set up yet" explanation.
// It never offers an Options popover, so nothing a person toggles here can change what the commands do.
export function createStatePanel({ title, load, render, explain = () => null, actions = [], skeletonShape = "row" }) {
  const body = h("div", { class: "panel-body" }, skeleton(3, skeletonShape));
  const count = h("span", { class: "count" });
  const element = h(
    "section",
    { class: "panel" },
    h("header", { class: "panel-head" }, h("h2", { text: title }), count, h("span", { class: "spacer" }), actions, iconButton("refresh", `Refresh ${title.toLowerCase()}`, () => run(true))),
    body,
  );
  let ticket = 0;
  let settled = false;
  let stale = false;

  async function run(fresh = false) {
    const mine = (ticket += 1);
    const hooks = { setCount: (text) => (count.textContent = text), reload: () => run(true) };
    stale = false;
    element.classList.add("loading");
    try {
      const data = await load(fresh);
      if (mine !== ticket) return;
      body.replaceChildren(render(data, hooks));
      settled = true;
    } catch (error) {
      if (mine !== ticket) return;
      const explained = explain(error, hooks);
      count.textContent = "";
      settled = Boolean(explained);
      body.replaceChildren(
        explained ?? notice({ glyph: "alert", tone: "bad", title: "This didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => run(true) }) }),
      );
    }
    element.classList.remove("loading");
  }

  on("data-stale", () => {
    stale = true;
    if (element.isConnected && !element.closest("[hidden]")) run(true);
  });

  return {
    element,
    reload: () => run(true),
    ensure() {
      if (!settled || stale) run(stale);
    },
  };
}

export function areaHead({ title, lede, actions = [] }) {
  return h("header", { class: "wb-head" }, h("div", { class: "wb-head-text" }, h("h2", { text: title }), h("p", { text: lede })), h("div", { class: "view-actions" }, actions));
}

// A tool card with its own plain wording and starting values. `caution` marks tools that delete things: they still only open the sheet.
export function actionCard(tools, { path, title, blurb, preset = {}, caution = "" }) {
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

export function statusPill(label, tone, glyph) {
  return h("span", { class: `pill ${tone}` }, glyph && icon(glyph, 12), h("span", { text: label }));
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
