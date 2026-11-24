import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { markStale } from "../../data.js";
import { replay, rise } from "../../motion.js";
import { confirmAction, openPopover } from "../../overlays.js";
import { button, notice, pathChip, searchInput, sectionHead, segmented, skeleton, stat } from "../../widgets.js";
import { openExample } from "./example_sheet.js";
import { fileCard } from "./files/card.js";
import { createFile, files, reasonOf, recheck } from "./model.js";
import { FILES, FILES_HASH, FILE_ACTIONS, FILE_TOOLS, HASH, needsAttention, standingOf } from "./words.js";

const FILTERS = [["all", "All"], ["here", "On this machine"], ["missing", "Not created"], ["attention", "Need attention"]];
const PASSES = {
  all: () => true,
  here: (standing) => !["missing", "unavailable"].includes(standing.id),
  missing: (standing) => standing.id === "missing",
  attention: needsAttention,
};
// The file whoever opened the tool asked for, and the button its command stands for, until the page shows them.
let arrival = { kind: "", action: "" };

// Five commands share this view: where a file is, creating it, checking it, editing it and exporting its example. Each lands on the file it
// was given, with the keyboard on the button that does what the command does. Nothing is created, edited or exported unasked.
export function open(_context, { preset, action }) {
  arrival = { kind: Object.hasOwn(FILES, preset?.which ?? "") ? preset.which : "", action: FILE_ACTIONS[action] ?? "" };
  const address = arrival.kind ? `${FILES_HASH}/${arrival.kind}` : FILES_HASH;
  if (location.hash === address) window.dispatchEvent(new HashChangeEvent("hashchange"));
  else location.hash = address;
}

// Settings › Settings files, at #/settings/files: every file the CLI manages, as a card that says where it is, whether it is there and whether
// it passes its check, with the one-click ways to create, edit, check and export. A page and not a sheet: nine cards to compare and filter.
export function createPart({ activity, tools }) {
  let filter = "all";
  let typed = "";
  let spot = "";
  const busy = new Set();
  const cards = new Map();

  const tiles = {
    here: stat({ glyph: "folder", hue: 252, label: "On this machine" }),
    valid: stat({ glyph: "check", hue: 155, label: "Pass their check" }),
    attention: stat({ glyph: "alert", hue: 20, label: "Need attention" }),
  };
  const picker = segmented(FILTERS, (value) => {
    filter = value;
    paint(files.reading);
  });
  const search = searchInput({
    placeholder: "Search settings files",
    oninput: (value) => {
      typed = value;
      paint(files.reading);
    },
  });
  const yours = h("div", { class: "settings-files-grid" }, skeleton(4, "card"));
  const projects = h("div", { class: "settings-files-grid" });
  const projectNote = h("span", { class: "count" });
  const yoursBlock = h("section", { class: "block" }, sectionHead("Yours, on every project"), yours);
  const projectBlock = h("section", { class: "block" }, sectionHead("This project's", projectNote), projects);
  const lead = h("div");
  const body = h("div", { class: "settings-files-body" }, rise(h("div", { class: "stats" }, Object.values(tiles).map((tile) => tile.element))), h("div", { class: "table-bar settings-files-bar" }, picker.element, search.element), lead, yoursBlock, projectBlock);
  picker.set(filter);

  async function create(file, told) {
    busy.add(file.kind);
    paint(files.reading);
    try {
      await createFile(file.kind);
      toast(told, "info");
    } catch (error) {
      toast(error.message);
    }
    busy.delete(file.kind);
    // Other pages read these files too, so they are all told. That also reads this page's list again.
    markStale();
  }

  const handlers = {
    onCreate: (file) => create(file, `Created ${FILES[file.kind].title.toLowerCase()} from the example StackOps ships.`),
    async onSchema(file) {
      const sure = await confirmAction({
        title: file.schema === "missing" ? "Put the schema beside the file?" : "Bring the schema up to date?",
        body: `StackOps writes the schema it ships next to ${tildify(file.path, state.boot.home)} and makes sure the file names it, so an editor can check the file as you type. The rest of the file stays as it is.`,
        confirm: file.schema === "missing" ? "Put it there" : "Update it",
      });
      if (sure) create(file, "The schema beside the file is the current one now.");
    },
    async onCheck(file) {
      const check = await recheck(file.kind);
      if (check.ok) toast(`${FILES[file.kind].title} passes its check.`, "info");
    },
    onExample: (file) => openExample({ activity, tools, file, onCreate: handlers.onCreate }),
  };

  function paint({ value, failure }) {
    element.classList.toggle("loading", files.reading.loading);
    if (!value) {
      lead.replaceChildren(...(failure ? [notice({ glyph: "alert", tone: "bad", title: "The settings files could not be read", body: reasonOf(failure), action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => files.reload() }) })] : []));
      yoursBlock.hidden = projectBlock.hidden = Boolean(failure);
      return;
    }
    const standings = new Map(value.files.map((file) => [file.kind, standingOf(file, value.checks.get(file.kind))]));
    const count = (test) => [...standings.values()].filter(test).length;
    const waiting = count((standing) => standing.id === "checking");
    tiles.here.set(count(PASSES.here), `of ${value.files.length} settings files`);
    tiles.valid.set(count((standing) => standing.id === "valid"), waiting ? `${waiting} still being checked` : "the check every command runs first");
    tiles.attention.set(count(needsAttention), count(needsAttention) ? "see the cards marked in red" : "nothing to fix");
    picker.label(FILTERS.map(([id, label]) => `${label} · ${count(PASSES[id])}`));
    const term = typed.trim().toLowerCase();
    let shown = 0;
    for (const file of value.files) {
      if (!cards.has(file.kind)) cards.set(file.kind, fileCard(file.kind, { activity, handlers }));
      const card = cards.get(file.kind);
      card.paint(file, value.checks.get(file.kind), busy.has(file.kind));
      const words = FILES[file.kind];
      card.element.hidden = !PASSES[filter](standings.get(file.kind)) || !`${words.title} ${words.about} ${file.kind} ${file.path} ${standings.get(file.kind).label}`.toLowerCase().includes(term);
      shown += card.element.hidden ? 0 : 1;
    }
    const cardsOf = (scope) => value.files.filter((file) => file.scope === scope).map((file) => cards.get(file.kind).element);
    if (yours.childElementCount !== cardsOf("home").length || yours.firstElementChild?.classList.contains("skeleton")) {
      yours.replaceChildren(...cardsOf("home"));
      projects.replaceChildren(...cardsOf("folder"));
      rise(yours);
    }
    projectNote.replaceChildren(...(value.project ? [pathChip(value.project)] : ["the working folder is not part of one"]));
    yoursBlock.hidden = cardsOf("home").every((card) => card.hidden);
    projectBlock.hidden = cardsOf("folder").every((card) => card.hidden);
    const reset = () => {
      filter = "all";
      typed = search.input.value = "";
      picker.set(filter);
      paint(files.reading);
    };
    lead.replaceChildren(...(shown === 0 ? [notice({ glyph: "search", title: "No settings file matches", body: "Nothing fits this filter and search.", action: button({ label: "Show all nine", small: true, onclick: reset }) })] : []));
    if (spot && cards.has(spot)) land();
  }

  // The file the address names: brought into view and marked once, with the keyboard on the button the command that led here stands for.
  function land() {
    const card = cards.get(spot).element;
    const action = arrival.kind === spot ? arrival.action : "";
    spot = "";
    arrival = { kind: "", action: "" };
    if (card.hidden) return;
    card.scrollIntoView({ block: "center" });
    replay(card, "settings-spot");
    (card.querySelector(`[data-action="${action}"]:enabled`) ?? card).focus({ preventScroll: true });
  }

  const options = button({
    label: "All options", glyph: "sliders", title: "The commands behind this page as plain forms",
    onclick: () => {
      const popover = openPopover(
        options,
        h(
          "div",
          { class: "settings-files-tools" },
          h("h3", { text: "The commands behind this page" }),
          FILE_TOOLS.map(([path, title, blurb]) =>
            h(
              "button",
              {
                type: "button",
                onclick: () => {
                  popover.close();
                  tools.open(path, { plain: true });
                },
              },
              h("strong", { text: title }),
              h("span", { text: blurb }),
            ),
          ),
        ),
      );
    },
  });
  const again = button({ label: "Check again", glyph: "refresh", title: "Read the files again and check each one", onclick: () => files.reload() });
  again.classList.add("settings-again");
  const element = h(
    "div",
    { class: "settings-files", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("a", { class: "part-back", href: HASH }, icon("back", 14), h("span", { text: "Settings" })), h("h1", { text: "Settings files" }), h("p", { text: "Every file StackOps reads its settings from: where it is, whether it is there, and whether it passes its check." })),
      h("div", { class: "view-actions" }, options, again),
    ),
    body,
  );
  files.watch(element, paint);

  return {
    element,
    show(rest) {
      spot = Object.hasOwn(FILES, rest[0] ?? "") ? rest[0] : "";
      // A file asked for by name is shown whatever the filter and search were left on.
      if (spot) {
        filter = "all";
        typed = search.input.value = "";
        picker.set(filter);
      }
      if (files.reading.value) paint(files.reading);
      files.sync();
    },
  };
}
