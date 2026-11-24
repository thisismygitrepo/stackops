import { h, icon } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { openPopover } from "../../overlays.js";
import { button, notice } from "../../widgets.js";
import { blurbOf, titleOf } from "../../words.js";

export const VAULT_HASH = "#/vault";

// What another view asks the list of logins to show when the person goes there from it: a search word, or one login by its file and place.
// The Vault page takes it when it is next shown, and empties it.
export const listRequest = { term: null, key: null };
export function showInList(wanted) {
  Object.assign(listRequest, { term: null, key: null }, wanted);
  location.hash = VAULT_HASH;
}

// The head of a page under Vault: the way back, the title, and the page's own buttons.
export function partHead({ title, lede, actions }) {
  return h(
    "header",
    { class: "view-head" },
    h("div", { class: "view-title" }, h("a", { class: "vault-tools-back", href: VAULT_HASH }, icon("back", 14), h("span", { text: "Vault" })), h("h1", { text: title }), h("p", { text: lede })),
    h("div", { class: "view-actions" }, actions),
  );
}

// Every option of the commands behind a view: a button that lists those commands, each opening its own form.
export function optionsButton(tools, paths) {
  const opener = button({
    label: "All options", glyph: "sliders", title: "The commands' own forms, with every option they have",
    onclick: () => {
      const rows = paths.filter((path) => state.nodes.has(path)).map((path) => {
        const node = state.nodes.get(path);
        const pick = () => {
          popover.close();
          tools.open(path, { plain: true });
        };
        return h("button", { class: "vault-tools-menu-row", type: "button", onclick: pick }, h("strong", { text: titleOf(node) }), h("span", { text: blurbOf(node) }));
      });
      const popover = openPopover(opener, h("div", { class: "vault-tools-menu" }, h("h3", { text: "The commands' own forms" }), rows));
    },
  });
  return opener;
}

// A view that could not read what it shows. A route that is not there at all means the page files are newer than the server that is running:
// the server only learns new routes when it starts.
export function loadProblem(error, { retry, tools, path }) {
  const stale = error.status === 404 && !error.payload;
  return notice({
    glyph: "alert", tone: "bad", title: stale ? "Restart the web UI to see this" : "This didn't load",
    body: stale ? "This view is newer than the server that is running. Stop the web UI and start it again. Until then the command's own form works." : error.message,
    action: h(
      "div",
      { class: "dialog-actions" },
      button({ label: "Try again", glyph: "refresh", small: true, onclick: retry }),
      stale && button({ label: "Open the form", small: true, onclick: () => tools.open(path, { plain: true }) }),
    ),
  });
}

// A mark for a state at a glance. `tone` is good, warn, bad, note (worth knowing, nothing wrong), idle (not there yet) or busy (being worked out).
const MARK_GLYPHS = { good: "check", warn: "alert", bad: "close", note: "info", idle: "plus", busy: "refresh" };
export const mark = (tone, size = 14) => h("span", { class: `vault-tools-mark ${tone}` }, icon(MARK_GLYPHS[tone], size));

// A bar filled to `share` (0 to 1) in a tone.
export const meter = (share, tone = "") => h("span", { class: `vault-tools-meter ${tone}`, role: "presentation" }, h("i", { style: `width:${Math.round(Math.max(0, Math.min(1, share)) * 100)}%` }));

// A button that shows it is working while `action` runs, and cannot be pressed twice in that time.
export function busyButton(properties, action) {
  const element = button({
    ...properties,
    onclick: async () => {
      if (element.disabled) return;
      element.disabled = true;
      element.classList.add("vault-tools-busy");
      try {
        await action();
      } finally {
        element.disabled = false;
        element.classList.remove("vault-tools-busy");
      }
    },
  });
  return element;
}
