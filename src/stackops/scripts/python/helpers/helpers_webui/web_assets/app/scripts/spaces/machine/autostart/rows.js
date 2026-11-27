import { h, icon } from "/assets/scripts/dom.js";
import { glyphTile, highlight } from "../../../widgets.js";
import { KINDS, lockText, stateWords, whenText } from "./words.js";

const ROW_STEP = 40;

// What can be done to an entry straight from its row: a switch for what starts for the person's own account, a way off the list for a
// login item, and for everything else a padlock that says why not.
function control(entry, { platform, busy, handlers }) {
  if (busy) return h("span", { class: "autostart-busy" }, h("i", { class: "ring" }));
  if (entry.actions.includes("turn_off") || entry.actions.includes("turn_on")) {
    return h("button", { class: "autostart-switch", type: "button", role: "switch", "aria-checked": String(entry.enabled), "aria-label": `${entry.title} starts on its own`, title: entry.enabled ? "Turn it off" : "Turn it back on", onclick: () => handlers.toggle(entry, platform) }, h("i", { class: "switch" }));
  }
  if (entry.actions.includes("remove")) return h("button", { class: "icon-btn danger", type: "button", title: "Stop opening it when you sign in", "aria-label": `Stop opening ${entry.title} when you sign in`, onclick: () => handlers.remove(entry) }, icon("close", 15));
  return h("span", { class: "autostart-lock", title: lockText(entry, platform) }, icon("lock", 14));
}

function entryRow(entry, context) {
  const kind = KINDS[entry.category];
  const state = stateWords(entry);
  return h(
    "li",
    { class: `autostart-row${entry.enabled ? "" : " off"}` },
    h(
      "button",
      { class: "autostart-row-main", type: "button", title: "Show everything about it", onclick: () => context.handlers.open(entry) },
      glyphTile(kind.glyph, kind.hue, 36),
      h(
        "span",
        { class: "autostart-row-text" },
        h("span", { class: "autostart-row-title" }, h("strong", {}, highlight(entry.title, context.term)), entry.kind === "login_item" ? h("em", { text: "Login item" }) : entry.owner && entry.owner !== entry.title && h("em", {}, highlight(entry.owner, context.term))),
        h("span", { class: "autostart-row-line" }, h("span", {}, (entry.kind === "listed" || entry.kind === "systemd") && entry.description ? highlight(entry.description, context.term) : whenText(entry)), entry.name !== entry.title && h("code", {}, highlight(entry.name, context.term))),
      ),
    ),
    state && h("span", { class: "autostart-state", "data-tone": state.tone, title: state.text }, h("i"), h("span", { text: state.short })),
    control(entry, { platform: context.platform, busy: context.busy.has(entry.id), handlers: context.handlers }),
  );
}

// The list in its sections. A long section shows its first rows and a button for the rest, so the standard parts of the system, which run
// to hundreds, do not cost anything until they are asked for.
export function createList({ view, handlers }) {
  const element = h("div", { class: "autostart-list" });

  function render(groups, { platform, entering }) {
    const term = view.term.trim();
    element.replaceChildren(
      ...groups.map((group, index) => {
        const limit = view.shown.get(group.id) ?? ROW_STEP;
        const rest = group.entries.length - limit;
        return h(
          "section",
          { class: `autostart-group${entering ? " rise" : ""}`, style: `--i:${Math.min(index, 8)}` },
          group.title && h("h3", { title: group.hint }, group.glyph && icon(group.glyph, 14), h("span", { text: group.title }), h("b", { text: group.entries.length.toLocaleString() })),
          h("ol", { class: "autostart-rows" }, group.entries.slice(0, limit).map((entry) => entryRow(entry, { term, platform, busy: view.busy, handlers }))),
          rest > 0 &&
            h("button", { class: "autostart-more", type: "button", text: `Show ${Math.min(rest, ROW_STEP * 5).toLocaleString()} more of ${group.entries.length.toLocaleString()}`, onclick: () => handlers.more(group.id, limit + ROW_STEP * 5) }),
        );
      }),
    );
  }

  return { element, render };
}
