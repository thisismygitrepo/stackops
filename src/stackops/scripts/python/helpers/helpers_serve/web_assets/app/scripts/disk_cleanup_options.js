import { h, icon, tildify } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { createCombo } from "./combo.js";
import { CATEGORY_ORDER, categoryOf } from "./disk_cleanup_words.js";
import { openPopover } from "./overlays.js";
import { button, segmented } from "./widgets.js";

const LEVELS = [["safe", "Safe only"], ["caution", "Also “check first”"], ["danger", "Everything"]];
const LEVEL_HINTS = {
  safe: "Only things that come back by themselves are ticked for you.",
  caution: "Also ticks things you may have to reinstall, rebuild, or lose. Read them before cleaning.",
  danger: "Ticks everything that was found, including data that cannot be recovered.",
};

export const defaultOptions = () => ({ categories: new Set(CATEGORY_ORDER), level: "safe", admin: false, roots: [] });
export const changedOptions = (options) => Number(options.categories.size !== CATEGORY_ORDER.length) + Number(options.level !== "safe") + Number(options.admin) + Number(options.roots.length > 0);

function absolute(text) {
  const { home } = state.boot;
  const cleaned = text.trim().replace(/(.)[\\/]+$/, "$1");
  if (cleaned === "") return "";
  if (cleaned === "~") return home;
  if (cleaned.startsWith("~/")) return `${home}${cleaned.slice(1)}`;
  return /^(\/|[A-Za-z]:[\\/])/.test(cleaned) ? cleaned : `${home}/${cleaned}`;
}

// What the scan looks at and what it ticks for you. `onChange` gets "categories", "picks" or "roots", so only the affected part is done again.
export function openCleanupOptions(anchor, { options, onChange }) {
  const chips = CATEGORY_ORDER.map((id) =>
    h("button", {
      class: "chip-button", type: "button", text: categoryOf(id).title,
      onclick: () => {
        if (!options.categories.delete(id)) options.categories.add(id);
        if (options.categories.size === 0) options.categories.add(id);
        paint();
        onChange("categories");
      },
    }),
  );
  const levelHint = h("p", { class: "field-hint" });
  const level = segmented(LEVELS, (value) => {
    options.level = value;
    paint();
    onChange("picks");
  });
  const adminToggle = h(
    "button",
    {
      class: "field toggle-row", type: "button", role: "switch",
      onclick: () => {
        options.admin = !options.admin;
        paint();
        onChange("picks");
      },
    },
    h("div", {}, h("div", { class: "field-label" }, h("span", { text: "Places that need an administrator" })), h("p", { class: "field-hint", text: "Tick those for me too. You are asked for the password when cleaning." })),
    h("i", { class: "switch" }),
  );
  const rootList = h("div", { class: "cleanup-roots" });
  let typed = "";
  const add = () => {
    const folder = absolute(typed);
    if (folder === "" || options.roots.includes(folder)) return;
    options.roots.push(folder);
    typed = "";
    combo.setValue("");
    paint();
    onChange("roots");
  };
  const combo = createCombo({
    label: "Add a folder", glyph: "folder", placeholder: "Add a folder, such as ~/code", emptyText: "No such folder",
    suggest: async (text) => (await api.paths(text || "~/", state.boot.home)).entries.filter((entry) => entry.endsWith("/")).map((entry) => ({ value: entry, label: entry, keepOpen: true })),
    onInput: (text) => (typed = text),
    onPick: (option) => (typed = option.value),
  });
  combo.input.addEventListener("keydown", (event) => event.key === "Enter" && !event.defaultPrevented && add());

  function paint() {
    chips.forEach((chip, index) => chip.setAttribute("aria-pressed", String(options.categories.has(CATEGORY_ORDER[index]))));
    level.set(options.level);
    levelHint.textContent = LEVEL_HINTS[options.level];
    adminToggle.setAttribute("aria-checked", String(options.admin));
    reset.hidden = changedOptions(options) === 0;
    rootList.replaceChildren(
      ...(options.roots.length
        ? options.roots.map((folder) =>
            h(
              "div",
              { class: "cleanup-root" },
              icon("folder", 14),
              h("span", { text: tildify(folder, state.boot.home) }),
              h("button", { class: "icon-btn", type: "button", title: "Stop looking here", "aria-label": `Stop looking in ${folder}`, onclick: () => {
                options.roots.splice(options.roots.indexOf(folder), 1);
                paint();
                onChange("roots");
              } }, icon("close", 13)),
            ),
          )
        : [h("div", { class: "cleanup-root everywhere" }, icon("home", 14), h("span", { text: "Your whole home folder" }))]),
    );
  }

  const reset = button({
    label: "Reset", small: true, tone: "ghost",
    onclick: () => {
      const before = { categories: options.categories.size, roots: options.roots.length };
      Object.assign(options, defaultOptions());
      paint();
      if (before.categories !== CATEGORY_ORDER.length) onChange("categories");
      if (before.roots > 0) onChange("roots");
      onChange("picks");
    },
  });
  const field = (label, ...content) => h("div", { class: "field" }, h("div", { class: "field-label" }, h("span", { text: label })), ...content);
  const popover = openPopover(
    anchor,
    h(
      "div",
      { class: "tune-panel cleanup-options" },
      h("div", { class: "tune-head" }, h("h3", { text: "Scan options" }), reset),
      field("Look at", h("div", { class: "chip-row" }, chips)),
      field("Tick for me", level.element, levelHint),
      adminToggle,
      field("Search for project folders in", rootList, h("div", { class: "cleanup-add" }, combo.element, button({ label: "Add", small: true, onclick: add })), h("p", { class: "field-hint", text: "One project folder is much quicker to search than the whole home folder." })),
    ),
  );
  paint();
  return popover;
}
