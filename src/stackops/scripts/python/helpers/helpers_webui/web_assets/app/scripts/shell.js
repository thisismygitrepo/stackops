import { h, icon, tildify } from "/assets/scripts/dom.js";
import { api, setSetting, state } from "/assets/scripts/state.js";
import { SPACES, VIEW_KEY } from "./catalog.js";
import { createCombo } from "./combo.js";
import { markStale } from "./data.js";
import { createMachineChip } from "./other_machines.js";
import { openPopover } from "./overlays.js";
import { button } from "./widgets.js";

export function createShell({ openSearch, activity }) {
  const { boot } = state;
  const marker = h("i", { class: "rail-marker" });
  const items = new Map(SPACES.map((space) => [space.id, h("a", { class: "rail-item", href: space.hash, title: space.title }, icon(space.glyph, 21), h("span", { text: space.label }))]));
  const switchButton = h(
    "button",
    {
      class: "rail-item rail-switch", type: "button", title: "Switch to the developer view: every command, flag, and terminal",
      onclick: () => {
        localStorage.setItem(VIEW_KEY, "dev");
        location.href = "/dev";
      },
    },
    icon("code", 20),
    h("span", { text: "Dev view" }),
  );
  const rail = h(
    "nav",
    { class: "rail", "aria-label": "Pages" },
    h("a", { class: "rail-brand", href: "#/", title: `StackOps ${boot.version}` }, h("img", { src: "/assets/favicon.svg", alt: "StackOps" })),
    h("div", { class: "rail-items" }, marker, [...items.values()]),
    switchButton,
  );

  const folderLabel = h("span");
  const folderButton = h("button", { class: "folder-chip", type: "button", title: "The folder tasks run in. Click to change." }, icon("folder", 15), folderLabel);
  const showFolder = () => (folderLabel.textContent = `‎${tildify(state.settings.workingDirectory, boot.home)}`);
  folderButton.addEventListener("click", () => {
    let chosen = state.settings.workingDirectory;
    // The server reads the text the way the suggestions do and answers with the folder's full path, which is what gets stored. Text that names no folder is refused: the reason shows as a message and the popover stays open.
    const apply = async () => {
      const { path } = await api.directory(chosen.trim(), state.settings.workingDirectory);
      if (path !== state.settings.workingDirectory) {
        setSetting("workingDirectory", path);
        showFolder();
        markStale();
      }
      popover.close();
    };
    const combo = createCombo({
      value: chosen, label: "Working folder", glyph: "folder", placeholder: "Type a folder", emptyText: "No folders to suggest",
      suggest: async (text) => (await api.paths(text, state.settings.workingDirectory)).entries.filter((entry) => entry.endsWith("/")).map((entry) => ({ value: entry, label: entry, keepOpen: true })),
      onInput: (text) => (chosen = text),
      onPick: (option) => (chosen = option.value),
    });
    combo.input.addEventListener("keydown", (event) => event.key === "Enter" && !event.defaultPrevented && apply());
    const popover = openPopover(
      folderButton,
      // The button sits beside the title, clear of the suggestion list that drops under the box.
      h("div", { class: "tune-panel" }, h("div", { class: "tune-head" }, h("h3", { text: "Working folder" }), button({ label: "Use this folder", tone: "primary", small: true, onclick: apply })), h("p", { class: "dim", text: "Tasks run here, and pages show what belongs to this folder." }), combo.element),
    );
    combo.input.focus();
    combo.input.select();
  });
  showFolder();

  const searchButton = h(
    "button",
    { class: "search-pill", type: "button", onclick: () => openSearch() },
    icon("search", 16),
    h("span", { text: "Search apps, tools, and pages" }),
    h("kbd", { text: navigator.platform.startsWith("Mac") ? "⌘K" : "Ctrl K" }),
  );
  // The machine comes before the folder: the folder is one of that machine's.
  const topbar = h("header", { class: "topbar" }, searchButton, h("span", { class: "spacer" }), createMachineChip(), folderButton, activity.indicator);

  function setActive(spaceId) {
    for (const [id, item] of items) item.setAttribute("aria-current", String(id === spaceId));
    const current = items.get(spaceId);
    marker.style.opacity = current ? "1" : "0";
    if (!current) return;
    marker.style.transform = `translateY(${current.offsetTop}px)`;
    // On a short window the list of pages scrolls, so the page being shown is brought into view.
    current.scrollIntoView({ block: "nearest" });
  }

  return { rail, topbar, setActive };
}
