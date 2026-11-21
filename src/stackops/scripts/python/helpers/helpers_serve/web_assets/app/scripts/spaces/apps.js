import { h, icon, toast } from "/assets/scripts/dom.js";
import { on } from "/assets/scripts/state.js";
import { createCombo } from "../combo.js";
import { software } from "../data.js";
import { replay, rise } from "../motion.js";
import { confirmAction } from "../overlays.js";
import { editButton } from "../space_kit.js";
import { avatar, button, glyphTile, notice, pill, segmented, skeleton } from "../widgets.js";
import { plainText, plural } from "../words.js";
import { openAppDetail } from "./app_detail.js";
import { createAppFilters } from "./app_filters.js";
import { createAppUpdates } from "./app_updates.js";

const SUGGESTION_LIMIT = 8;
// Not strictly complete: the installer splits its argument on commas, so a link containing one is not offered.
const LINK_PATTERN = /^https?:\/\/[^\s,]+$/;
const MY_CATALOG = { title: "my app catalog", kind: "software" };
const LEDES = {
  browse: "Find something, select it, install it. Pick as many as you like.",
  updates: "The apps on this machine that come from a GitHub repository: the version you have, and the latest one released.",
};

export function createAppsSpace({ activity }) {
  const picked = new Set();
  let catalog = null;
  let term = "";
  let found = [];
  let update = false;
  let stale = true;

  const grid = h("div", { class: "app-grid" }, skeleton(12, "card"));
  const filters = createAppFilters({ onChange: () => paintGrid() });
  const summary = h("p", { class: "result-count" });
  const selectAll = button({ label: "Select all", small: true, tone: "ghost", onclick: () => pickAllFound() });
  const bundleButton = button({ label: "Install bundle", glyph: "download", small: true, tone: "primary", title: "Installs the apps of this bundle that are not here yet, several at a time.", onclick: () => installBundle() });
  selectAll.hidden = bundleButton.hidden = true;
  const trayFaces = h("div", { class: "tray-faces" });
  const trayText = h("strong");
  const installButton = button({ label: "Install", glyph: "download", tone: "primary", onclick: () => install([...picked], update) });
  const updateToggle = h("button", { class: "mini-toggle", type: "button", role: "switch", "aria-checked": "false", onclick: () => setUpdate(!update) }, h("i", { class: "switch" }), h("span", { text: "Also update ones already installed" }));
  const tray = h("div", { class: "tray", hidden: true }, trayFaces, trayText, updateToggle, h("span", { class: "spacer" }), button({ label: "Clear", tone: "ghost", onclick: () => setPicked([]) }), installButton);

  function setUpdate(value) {
    update = value;
    updateToggle.setAttribute("aria-checked", String(update));
  }

  const matches = (text) => {
    const terms = text.toLowerCase().split(/\s+/).filter(Boolean);
    const rank = (app) => (terms.length === 0 ? 0 : app.name.toLowerCase().startsWith(terms[0]) ? 0 : app.name.toLowerCase().includes(terms[0]) ? 1 : 2);
    return catalog.apps.filter((app) => terms.every((word) => app.haystack.includes(word))).sort((left, right) => rank(left) - rank(right));
  };

  const combo = createCombo({
    large: true, glyph: "search", label: "Search apps", placeholder: "Search apps — try “git”, “browser”, or “terminal”", emptyText: "No app matches that. Try another word.",
    suggest: (text) =>
      LINK_PATTERN.test(text.trim())
        ? [{ value: text.trim(), label: "Install from this link", hint: text.trim(), lead: glyphTile("download", 252, 34), fill: false, link: true }]
        : catalog === null || text.trim() === ""
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
      if (option.link) installLink(option.value);
      else toggle(option.value);
      combo.setValue("");
      term = "";
      paintGrid();
    },
  });

  // A link installs whatever it points at, so it asks first; apps from the catalog do not.
  async function installLink(link) {
    const sure = await confirmAction({ title: "Install from this link?", body: `${link} is downloaded and installed on this machine. Only do this for a source you trust.`, confirm: "Install" });
    if (sure) start("Install from a link", [link]).catch((error) => toast(error.message));
  }

  const start = (title, installArguments) => activity.start({ title, emoji: "📦", arguments: ["devops", "software", "install", ...installArguments], interactive: true, reveal: true });

  const updates = createAppUpdates({
    onUpdate: (names) => start(names.length === 1 ? `Update ${names[0]}` : `Update ${names.length} apps`, [names.join(","), "--update"]).catch((error) => toast(error.message)),
  });

  async function install(names, withUpdate) {
    if (names.length === 0) return;
    try {
      await start(names.length === 1 ? `Install ${names[0]}` : `Install ${names.length} apps`, [names.join(","), ...(withUpdate ? ["--update"] : [])]);
      setPicked([]);
    } catch (error) {
      toast(error.message);
    }
  }

  // A bundle goes to the installer by name, which installs its apps several at a time; a list of names would install them one by one.
  function installBundle() {
    const { bundle, label } = filters.active();
    start(`Install ${label}`, [bundle, "--group"]).catch((error) => toast(error.message));
  }

  // Selecting only installed apps can only mean updating them, and without the switch the installer would skip every one.
  function pickAllFound() {
    if (found.every((app) => app.installed)) setUpdate(true);
    setPicked([...picked, ...found.map((app) => app.name)]);
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

  const openDetail = (app) =>
    openAppDetail({ app, categories: catalog.categories, picked: picked.has(app.name), onToggle: () => toggle(app.name), onInstall: () => install([app.name], app.installed) });

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

  // A design choice: cards rise once per load. Rising on every keystroke restarted the animation on every card, most of them off screen.
  function paintGrid() {
    if (!catalog) return;
    const active = filters.active();
    const narrowed = term.trim() !== "" || active.value !== "all";
    const missing = active.bundle ? catalog.apps.filter((app) => active.accepts(app) && !app.installed).length : 0;
    found = matches(term).filter(active.accepts);
    summary.textContent = narrowed ? `${plural(found.length, "app")} found` : `${plural(found.length, "app")} ready to install`;
    selectAll.hidden = !narrowed || found.length === 0;
    selectAll.querySelector("span").textContent = `Select all ${found.length}`;
    bundleButton.hidden = missing === 0;
    bundleButton.querySelector("span").textContent = `Install bundle · ${missing} missing`;
    grid.replaceChildren(...(found.length ? found.map(card) : [notice({ glyph: "search", title: "No apps match", body: "Try a different word, or clear the filter." })]));
  }

  async function load(route) {
    stale = false;
    try {
      catalog = await software();
    } catch (error) {
      catalog = null;
      summary.textContent = "";
      selectAll.hidden = bundleButton.hidden = true;
      const actions = h("div", { class: "dialog-actions" }, button({ label: "Try again", glyph: "refresh", small: true, onclick: () => load([]) }), editButton(activity, MY_CATALOG, { label: "Edit my catalog", small: true }));
      grid.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The app catalog didn't load", body: error.message, action: actions }));
      return;
    }
    for (const app of catalog.apps) app.haystack = `${app.name} ${app.summary} ${app.categories.join(" ")}`.toLowerCase();
    filters.load(catalog);
    paintGrid();
    rise(grid);
    openRoute(route);
  }

  function openRoute(route) {
    const app = route[0] && catalog?.apps.find((candidate) => candidate.name === route[0]);
    if (!app) return;
    history.replaceState(null, "", "#/apps");
    openDetail(app);
  }

  // The address is #/apps for browsing and #/apps/updates for versions; #/apps/<name> opens that app over the browsing section.
  const picker = segmented([["browse", "Browse"], ["updates", "Updates"]], (id) => (location.hash = id === "browse" ? "#/apps" : "#/apps/updates"));
  const lede = h("p");
  const searchRow = h("div", { class: "store-search" }, combo.element, filters.search);
  const browse = h("div", {}, filters.element, h("div", { class: "result-row" }, summary, selectAll, bundleButton), grid, tray);
  const element = h(
    "section",
    { class: "view apps", hidden: true },
    h("header", { class: "store-hero" }, h("div", { class: "store-top" }, h("h1", { text: "Apps" }), editButton(activity, MY_CATALOG, { label: "Edit my catalog" })), lede, h("div", { class: "section-bar" }, picker.element), searchRow),
    browse,
    updates.element,
  );
  on("data-stale", () => {
    stale = true;
    if (!element.hidden && !browse.hidden) load([]);
  });
  return {
    element,
    show(route) {
      const section = route[0] === "updates" ? "updates" : "browse";
      picker.set(section);
      lede.textContent = LEDES[section];
      searchRow.hidden = browse.hidden = section !== "browse";
      updates.element.hidden = section !== "updates";
      if (section === "updates") updates.show();
      else if (stale) load(route);
      else openRoute(route);
    },
  };
}
