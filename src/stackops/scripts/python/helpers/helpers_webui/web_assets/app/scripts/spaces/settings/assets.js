import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { rise } from "../../motion.js";
import { confirmAction } from "../../overlays.js";
import { button, emojiTile, notice, pathChip, searchInput, sectionHead, segmented, skeleton } from "../../widgets.js";
import { plural } from "../../words.js";
import { PARTS, countsLine, differsBy, folderRow, standingBar, totalOf } from "./assets/rows.js";
import { assets, reasonOf } from "./model.js";
import { ASSETS_HASH, ASSET_SETS, HASH } from "./words.js";

const TOOL_PATH = "devops config copy-assets";
const FILTERS = [["all", "All folders"], ["changed", "Changed here"], ["missing", "Not copied"], ["extra", "Only here"]];
const SORTS = [["name", "By name"], ["most", "Most different first"]];

// Every opening of the tool lands on the comparison. Nothing is copied unasked, whichever set was named.
export function open() {
  location.hash = ASSETS_HASH;
}

// Settings › Packaged files, at #/settings/assets: what `devops config copy-assets` would copy, held against the copies on this machine, so
// what a copy overwrites or removes is on the page before it runs. A page and not a sheet: thirty-odd folders to filter and open.
export function createPart({ activity, tools }) {
  let filter = "all";
  let sort = "name";
  let typed = "";
  let risen = false;
  const opened = new Set();
  const sets = h("div", { class: "settings-assets-sets" }, skeleton(2, "card"));
  const lead = h("div");
  const list = h("div", { class: "settings-assets-list" });
  const count = h("span", { class: "count" });
  const picker = segmented(FILTERS, (value) => {
    filter = value;
    paint(assets.reading);
  });
  const sorter = segmented(SORTS, (value) => {
    sort = value;
    paint(assets.reading);
  });
  const search = searchInput({
    placeholder: "Search folders",
    oninput: (value) => {
      typed = value;
      paint(assets.reading);
    },
  });
  const folders = h("section", { class: "block" }, sectionHead("Settings, folder by folder", count), h("div", { class: "table-bar settings-assets-barrow" }, picker.element, search.element, h("span", { class: "spacer" }), sorter.element), list);
  picker.set(filter);
  sorter.set(sort);

  // What a copy does to this machine, said before it starts. The scripts are copied over files of the same name; the settings folder is
  // removed and written anew, so what was changed or added there is lost.
  async function copy(set, value) {
    const words = ASSET_SETS[set.id];
    const total = (key) => totalOf(set.groups, key);
    const place = tildify(set.target, state.boot.home);
    const lost = total("changed") + total("extra");
    const profiles = value.old_profile_lines.map((path) => tildify(path, state.boot.home)).join(" and ");
    const body = set.replaces
      ? [
          set.on_machine ? `StackOps removes ${place} and puts its ${plural(total("offered"), "packaged file")} there.` : `StackOps creates ${place} and puts its ${plural(total("offered"), "packaged file")} there.`,
          total("changed") > 0 && `${plural(total("changed"), "file")} changed on this machine ${total("changed") === 1 ? "goes" : "go"} back to the packaged version.`,
          total("extra") > 0 && `${plural(total("extra"), "file")} that ${total("extra") === 1 ? "is" : "are"} only on this machine ${total("extra") === 1 ? "is" : "are"} deleted.`,
          lost > 0 ? "There is no undo." : set.on_machine && "Nothing in that folder differs from what StackOps ships, so nothing is lost.",
          profiles && `It also swaps the old StackOps line in ${profiles} for the current one, and keeps a copy of the file beside it.`,
        ]
      : [
          `StackOps copies ${plural(total("offered"), "file")} into ${place}, over the ones of the same name, and marks every file in that folder as runnable.`,
          total("changed") > 0 && `${plural(total("changed"), "file")} changed on this machine ${total("changed") === 1 ? "goes" : "go"} back to the packaged version.`,
          "Your own scripts in that folder stay.",
        ];
    const sure = await confirmAction({ title: `Copy the packaged ${words.title.toLowerCase()}?`, body: body.filter(Boolean).join(" "), confirm: lost > 0 && set.replaces ? "Replace the folder" : "Copy", tone: lost > 0 ? "danger" : "primary" });
    // The run's end tells every page its data is stale, which reads this comparison again.
    if (sure) activity.start({ title: `Copy the packaged ${words.title.toLowerCase()}`, emoji: "📋", arguments: [...TOOL_PATH.split(" "), words.which], interactive: false, reveal: true }).catch((error) => toast(error.message));
  }

  function setCard(set, value) {
    const words = ASSET_SETS[set.id];
    const counts = Object.fromEntries(PARTS.map(([key]) => [key, totalOf(set.groups, key)]));
    const differs = counts.changed + counts.missing + counts.extra;
    const offered = totalOf(set.groups, "offered");
    const line = !set.on_machine ? "Not on this machine yet." : differs === 0 ? `All ${plural(offered, "file")} here match what StackOps ships.` : `${plural(offered, "packaged file")} · ${countsLine(counts)}`;
    return h(
      "article",
      { class: `settings-assets-set ${differs === 0 ? "same" : "differs"}` },
      h("header", {}, emojiTile(words.emoji, `${TOOL_PATH} ${set.id}`, 46), h("div", {}, h("h3", { text: words.title }), h("p", { text: words.about }))),
      standingBar(counts),
      h("p", { class: "settings-assets-line", text: line }),
      h("footer", {}, pathChip(set.target), h("span", { class: "spacer" }), button({ label: differs === 0 ? "Copy again" : `Copy ${words.title.toLowerCase()}`, glyph: "download", small: true, tone: differs === 0 ? "plain" : "primary", title: "Says what it will change and asks first", onclick: () => copy(set, value) })),
    );
  }

  function paint({ value, failure }) {
    element.classList.toggle("loading", assets.reading.loading);
    if (!value || !value.supported) {
      lead.replaceChildren(
        ...(failure ? [notice({ glyph: "alert", tone: "bad", title: "The packaged files could not be compared", body: reasonOf(failure), action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => assets.reload() }) })] : []),
        ...(value ? [notice({ glyph: "cube", title: "Nothing is packaged for this system", body: "StackOps ships these files for macOS, Linux and Windows." })] : []),
      );
      sets.hidden = folders.hidden = Boolean(failure || value);
      return;
    }
    sets.hidden = folders.hidden = false;
    sets.replaceChildren(...value.sets.map((set) => setCard(set, value)));
    if (!risen) rise(sets);
    risen = true;
    const groups = value.sets.find((set) => set.id === "settings").groups;
    const term = typed.trim().toLowerCase();
    const passes = (group) => (filter === "all" || group[filter] > 0) && `${group.name || "top level"} ${group.changed_names.join(" ")} ${group.missing_names.join(" ")} ${group.extra_names.join(" ")}`.toLowerCase().includes(term);
    const shown = groups.filter(passes).sort((left, right) => (sort === "most" ? differsBy(right) - differsBy(left) : 0) || left.name.localeCompare(right.name));
    picker.label(FILTERS.map(([id, label]) => `${label} · ${id === "all" ? groups.length : groups.filter((group) => group[id] > 0).length}`));
    count.textContent = `${plural(groups.length, "folder")} · ${groups.filter((group) => differsBy(group) === 0).length} match`;
    const reset = () => {
      filter = "all";
      typed = search.input.value = "";
      picker.set(filter);
      paint(assets.reading);
    };
    lead.replaceChildren();
    list.replaceChildren(
      ...(shown.length > 0
        ? shown.map((group) => folderRow(group, opened))
        : [
            notice(
              filter !== "all" && term === ""
                ? { glyph: "check", tone: "good", title: "No folder is in this state", body: "Nothing here fits this filter.", action: button({ label: "Show all folders", small: true, onclick: reset }) }
                : { glyph: "search", title: "No folder matches", body: "Try a different word, or show every folder.", action: button({ label: "Show all folders", small: true, onclick: reset }) },
            ),
          ]),
    );
  }

  const again = button({ label: "Check again", glyph: "refresh", title: "Compare the packaged files with this machine again", onclick: () => assets.reload() });
  again.classList.add("settings-again");
  const element = h(
    "div",
    { class: "settings-assets", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("a", { class: "part-back", href: HASH }, icon("back", 14), h("span", { text: "Settings" })), h("h1", { text: "Packaged files" }), h("p", { text: "The scripts and ready-made settings StackOps ships, held against the copies on this machine. See what a copy would change before you make one." })),
      h("div", { class: "view-actions" }, button({ label: "All options", glyph: "sliders", title: "The command's own form, which can also copy both at once", onclick: () => tools.open(TOOL_PATH, { plain: true }) }), again),
    ),
    lead,
    sets,
    folders,
  );
  assets.watch(element, paint);

  return { element, show: () => assets.sync() };
}
