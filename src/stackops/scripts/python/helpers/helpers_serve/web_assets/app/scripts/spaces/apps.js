import { h, icon, toast } from "/assets/scripts/dom.js";
import { on } from "/assets/scripts/state.js";
import { createCombo } from "../combo.js";
import { software } from "../data.js";
import { replay, rise } from "../motion.js";
import { openSheet } from "../overlays.js";
import { avatar, button, keyValue, notice, pill, searchInput, skeleton } from "../widgets.js";
import { plainText, plural, relativeTime } from "../words.js";

const SUGGESTION_LIMIT = 8;
const CHIP_EDGE = 26;

export function createAppsSpace({ activity }) {
  const picked = new Set();
  let catalog = null;
  let term = "";
  let filter = "all";
  let tagTerm = "";
  let shownTags = [];
  let update = false;
  let stale = true;

  const grid = h("div", { class: "app-grid" }, skeleton(12, "card"));
  const chips = h("div", { class: "filter-row" });
  const summary = h("p", { class: "result-count" });
  const trayFaces = h("div", { class: "tray-faces" });
  const trayText = h("strong");
  const installButton = button({ label: "Install", glyph: "download", tone: "primary", onclick: () => install([...picked], update) });
  const updateToggle = h("button", { class: "mini-toggle", type: "button", role: "switch", "aria-checked": "false" }, h("i", { class: "switch" }), h("span", { text: "Also update ones already installed" }));
  const tray = h("div", { class: "tray", hidden: true }, trayFaces, trayText, updateToggle, h("span", { class: "spacer" }), button({ label: "Clear", tone: "ghost", onclick: () => setPicked([]) }), installButton);
  updateToggle.addEventListener("click", () => {
    update = !update;
    updateToggle.setAttribute("aria-checked", String(update));
  });

  const matches = (text) => {
    const terms = text.toLowerCase().split(/\s+/).filter(Boolean);
    const rank = (app) => (terms.length === 0 ? 0 : app.name.toLowerCase().startsWith(terms[0]) ? 0 : app.name.toLowerCase().includes(terms[0]) ? 1 : 2);
    return catalog.apps.filter((app) => terms.every((word) => app.haystack.includes(word))).sort((left, right) => rank(left) - rank(right));
  };

  const combo = createCombo({
    large: true, glyph: "search", label: "Search apps", placeholder: "Search apps — try “git”, “browser”, or “terminal”", emptyText: "No app matches that. Try another word.",
    suggest: (text) =>
      catalog === null || text.trim() === ""
        ? []
        : matches(text).slice(0, SUGGESTION_LIMIT).map((app) => ({
            value: app.name, label: app.name, hint: plainText(app.summary), lead: avatar(app.name, 34), fill: false,
            trail: picked.has(app.name) ? pill("Selected", "accent") : app.installed ? pill("Installed", "good") : h("span", { class: "combo-add" }, icon("plus", 14)),
          })),
    onInput: (text) => {
      term = text;
      paintGrid();
    },
    onPick: (option) => {
      toggle(option.value);
      combo.setValue("");
      term = "";
      paintGrid();
    },
  });

  const pickTag = (value) => {
    filter = value === filter ? "all" : value;
    paintChips();
    paintGrid();
  };
  const tagSearch = searchInput({
    placeholder: "Search categories",
    oninput: (value) => {
      tagTerm = value.trim().toLowerCase();
      if (catalog) paintChips();
    },
  });
  tagSearch.input.addEventListener("keydown", (event) => {
    const first = shownTags.find(([value]) => value !== filter);
    if (event.key === "Enter" && tagTerm && first) pickTag(first[0]);
  });

  async function install(names, withUpdate) {
    if (names.length === 0) return;
    try {
      await activity.start({
        title: names.length === 1 ? `Install ${names[0]}` : `Install ${names.length} apps`, emoji: "📦",
        arguments: ["devops", "software", "install", names.join(","), ...(withUpdate ? ["--update"] : [])], interactive: true, reveal: true,
      });
      setPicked([]);
    } catch (error) {
      toast(error.message);
    }
  }

  function paintTray() {
    const names = [...picked];
    tray.hidden = names.length === 0;
    trayFaces.replaceChildren(...names.slice(0, 5).map((name) => avatar(name, 30)), ...(names.length > 5 ? [h("span", { class: "tray-more", text: `+${names.length - 5}` })] : []));
    trayText.textContent = `${plural(names.length, "app")} selected`;
    installButton.querySelector("span").textContent = `Install ${plural(names.length, "app")}`;
  }

  function setPicked(names) {
    picked.clear();
    for (const name of names) picked.add(name);
    paintTray();
    for (const card of grid.querySelectorAll(".app-card")) card.classList.toggle("picked", picked.has(card.dataset.name));
  }

  function toggle(name) {
    if (!picked.delete(name)) picked.add(name);
    paintTray();
    replay(tray, "bump");
    grid.querySelector(`.app-card[data-name="${CSS.escape(name)}"]`)?.classList.toggle("picked", picked.has(name));
  }

  function openDetail(app) {
    const sheet = openSheet({ label: app.name });
    const titles = app.categories.map((label) => catalog.categories.find((category) => category.label === label)?.title ?? label);
    sheet.body.append(
      h("header", { class: "app-detail-head" }, avatar(app.name, 72), h("div", {}, h("h1", { text: app.name }), h("p", { text: plainText(app.summary) }), app.installed && pill("Installed on this machine", "good"))),
      keyValue([
        ["Category", titles.join(", ")],
        ["License", app.license],
        ["Website", app.homepage && h("a", { class: "link", href: app.homepage, target: "_blank", rel: "noopener noreferrer", text: app.homepage.replace(/^https?:\/\/(www\.)?/, "") })],
        ["Last updated", app.updated_at && relativeTime(app.updated_at)],
      ]),
    );
    sheet.foot.hidden = false;
    sheet.foot.append(
      h("span", { class: "spacer" }),
      button({
        label: picked.has(app.name) ? "Remove from selection" : "Add to selection", glyph: picked.has(app.name) ? "close" : "plus",
        onclick: () => {
          toggle(app.name);
          sheet.close();
        },
      }),
      button({
        label: app.installed ? "Update now" : "Install now", glyph: "download", tone: "primary",
        onclick: () => {
          sheet.close();
          install([app.name], app.installed);
        },
      }),
    );
  }

  function card(app) {
    const add = h("button", { class: "app-add", type: "button", title: "Select to install", "aria-label": `Select ${app.name}` }, icon("plus", 15), icon("check", 15));
    const element = h(
      "article",
      { class: `app-card lit${picked.has(app.name) ? " picked" : ""}`, "data-name": app.name, tabindex: "0" },
      avatar(app.name, 46),
      h("div", { class: "app-text" }, h("h3", {}, app.name, app.installed && h("i", { class: "installed-dot", title: "Installed" })), h("p", { text: plainText(app.summary) })),
      add,
    );
    element.addEventListener("click", (event) => (add.contains(event.target) ? toggle(app.name) : openDetail(app)));
    element.addEventListener("keydown", (event) => event.key === "Enter" && openDetail(app));
    return element;
  }

  function paintGrid() {
    const found = matches(term).filter((app) => filter === "all" || (filter === "installed" ? app.installed : filter === "new" ? !app.installed : app.categories.includes(filter)));
    summary.textContent = term || filter !== "all" ? `${plural(found.length, "app")} found` : `${plural(found.length, "app")} ready to install`;
    grid.replaceChildren(...(found.length ? found.map(card) : [notice({ glyph: "search", title: "No apps match", body: "Try a different word, or clear the filter." })]));
    rise(grid);
  }

  function paintChips() {
    const counts = new Map();
    for (const app of catalog.apps) for (const label of app.categories) counts.set(label, (counts.get(label) ?? 0) + 1);
    const installed = catalog.apps.filter((app) => app.installed).length;
    const options = [
      ["all", "Everything", catalog.apps.length], ["installed", "Installed", installed], ["new", "Not installed", catalog.apps.length - installed],
      ...catalog.categories.map((category) => [category.label, category.title, counts.get(category.label) ?? 0]).sort((left, right) => right[2] - left[2]),
    ];
    shownTags = options.filter(([value, label]) => value === filter || label.toLowerCase().includes(tagTerm));
    const pressed = (value) => value === filter;
    chips.replaceChildren(
      ...shownTags.map(([value, label, count]) =>
        h(
          "button",
          { class: "chip-button", type: "button", "aria-pressed": String(pressed(value)), title: pressed(value) && value !== "all" && "Click again to show everything", onclick: () => pickTag(value) },
          h("span", { text: label }),
          h("b", { text: String(count) }),
        ),
      ),
      ...(shownTags.some(([, label]) => label.toLowerCase().includes(tagTerm)) ? [] : [h("span", { class: "filter-none", text: "No category matches that." })]),
    );
    const row = chips.getBoundingClientRect();
    const box = chips.querySelector(`[aria-pressed="true"]`).getBoundingClientRect();
    if (box.left < row.left + CHIP_EDGE || box.right > row.right - CHIP_EDGE) chips.scrollLeft += box.left - row.left - CHIP_EDGE;
  }

  async function load(route) {
    stale = false;
    try {
      catalog = await software(true);
    } catch (error) {
      grid.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The app catalog didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => load([]) }) }));
      return;
    }
    for (const app of catalog.apps) app.haystack = `${app.name} ${app.summary} ${app.categories.join(" ")}`.toLowerCase();
    paintChips();
    paintGrid();
    openRoute(route);
  }

  function openRoute(route) {
    const app = route[0] && catalog?.apps.find((candidate) => candidate.name === route[0]);
    if (!app) return;
    history.replaceState(null, "", "#/apps");
    openDetail(app);
  }

  const element = h(
    "section",
    { class: "view apps", hidden: true },
    h("header", { class: "store-hero" }, h("h1", { text: "Apps" }), h("p", { text: "Find something, select it, install it. Pick as many as you like." }), h("div", { class: "store-search" }, combo.element, tagSearch.element)),
    chips,
    summary,
    grid,
    tray,
  );
  on("data-stale", () => {
    stale = true;
    if (!element.hidden) load([]);
  });
  return { element, show: (route) => (stale ? load(route) : openRoute(route)) };
}
