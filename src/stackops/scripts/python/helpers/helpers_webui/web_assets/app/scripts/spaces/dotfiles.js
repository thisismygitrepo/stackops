import { h, icon, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { agentButton } from "../agent_ask.js";
import { filePlace, PLACES } from "../agent_places.js";
import { partLoaders } from "../features.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { confirmAction } from "../overlays.js";
import { createParts, editButton, toolButton, viewHead } from "../space_kit.js";
import { emojiTile, notice, searchInput, segmented, stat } from "../widgets.js";
import { formatBytes, plural } from "../words.js";
import { COLLECT_WORDS, foundGroups, managedGroups } from "./dotfiles_groups.js";

const IN_SYNC = "Configured";
// On neither side: not on this machine and not in the dotfiles folder. A file for something that is not used here, so it stays out of the way unless it is asked for.
const UNUSED = "Missing both paths";
const MY_LIST = { title: "your dotfiles list", kind: "dotfiles" };

// The cards at the foot of the page. Each opens a view of its own (feature_lists/dotfiles.js): two pages under this one and a side sheet.
const MORE_TOOLS = [
  { path: "devops config dotfiles export", title: "Move to a new machine", blurb: "Pack the whole folder into one protected archive to carry, share or send." },
  { path: "devops config dotfiles import", title: "Bring settings from another machine", blurb: "See what an archive from the other machine would change here, then put it in place." },
  { path: "devops config dotfiles register", title: "Add one file", blurb: "Keep one more settings file in your dotfiles folder and on your list." },
];

// Views that swap in place: the overview at #/dotfiles and the ones features.js lists for this page.
export function createDotfilesSpace(context) {
  const { activity, tools } = context;
  // What the person chose is kept here, outside the panel's render, so it survives a refresh: the panel reloads when a sync ends, which is
  // exactly when the group that was open is the one to look at.
  let scope = "user";
  let typed = "";
  let showUnused = false;
  const opened = { user: new Set(), library: new Set(), found: new Set() };

  async function collect(group) {
    const sure = await confirmAction({ title: `Collect “${group}”?`, body: "Its files are moved into your dotfiles folder, linked back to where they were, and added to your list.", confirm: "Collect" });
    if (sure) activity.start({ title: `Collect ${group}`, emoji: "🧺", arguments: ["devops", "config", "dotfiles", "collect", "--which", group], interactive: true, reveal: true }).catch((error) => toast(error.message));
  }

  const panel = createLivePanel({
    // No Options: the command's switches pick which sections the answer holds and the page needs all of them, and its group choice is what the search box here does.
    title: "What is managed", path: "devops config dotfiles status", extra: ["--json"], tunable: false,
    actions: [agentButton(activity, filePlace(MY_LIST, { ideas: PLACES.dotfiles.ideas }), { small: true }), editButton(activity, MY_LIST, { label: "Edit my list", small: true })],
    render: (data, { setCount }) => {
      const everything = [...data.sync.user, ...data.sync.library];
      const synced = everything.filter((entry) => entry.status === IN_SYNC).length;
      const unused = everything.filter((entry) => entry.status === UNUSED).length;
      const found = data.radar.filter((plan) => Object.hasOwn(COLLECT_WORDS, plan.verdict));
      const listed = (entries) => (showUnused ? entries : entries.filter((entry) => entry.status !== UNUSED));
      const inSync = stat({ glyph: "check", hue: 155, label: "In sync" });
      const attention = stat({ glyph: "alert", hue: 30, label: "Need attention" });
      const collectable = stat({ glyph: "plus", hue: 252, label: "Ready to collect" });
      const stored = stat({ glyph: "folder", hue: 200, label: "Stored" });
      const holder = h("div", { class: "session-list" });
      const paint = () => {
        unusedSwitch.hidden = scope === "found";
        const term = typed.trim().toLowerCase();
        const matches = (...words) => words.join(" ").toLowerCase().includes(term);
        const matched = scope === "found" ? found.filter((plan) => matches(plan.group, plan.name)) : data.sync[scope].filter((entry) => matches(entry.program, entry.file_name, entry.status));
        const groups =
          scope === "found"
            ? foundGroups(matched, collect, opened.found)
            : managedGroups(listed(matched), (direction, group) => tools.open("devops config dotfiles sync", { preset: { direction, which: group, source: scope } }), opened[scope]);
        if (groups.length) return holder.replaceChildren(...groups);
        const body = matched.length
          ? `${plural(matched.length, "file")} here ${matched.length === 1 ? "is" : "are"} neither on this machine nor in your dotfiles folder. Turn on Show unused to see ${matched.length === 1 ? "it" : "them"}.`
          : term
            ? "No group, file, or status matches that search."
            : scope === "found"
              ? "Every settings file StackOps recognises on this machine is already on a list."
              : "No files of this kind are managed.";
        holder.replaceChildren(notice({ glyph: "folder", title: "Nothing here", body }));
      };
      const picker = segmented([["user", ""], ["library", ""], ["found", ""]], (value) => {
        scope = value;
        picker.set(scope);
        paint();
      });
      const unusedSwitch = h(
        "button",
        {
          class: "mini-toggle", type: "button", role: "switch", title: "Also list files that are neither on this machine nor in your dotfiles folder",
          onclick: () => {
            showUnused = !showUnused;
            count();
            paint();
          },
        },
        h("i", { class: "switch" }),
        h("span", { text: `Show unused · ${unused}` }),
      );
      // The numbers describe what is listed, so a file on neither side is counted only while it is shown, and never as one that needs attention.
      const count = () => {
        const total = everything.length - (showUnused ? 0 : unused);
        setCount(`${plural(total, "file")} · ${synced} in sync`);
        picker.label([`Yours · ${listed(data.sync.user).length}`, `Built in · ${listed(data.sync.library).length}`, `Found here · ${found.length}`]);
        unusedSwitch.setAttribute("aria-checked", String(showUnused));
        requestAnimationFrame(() => {
          inSync.set(synced, `of ${total} managed files`);
          attention.set(everything.length - unused - synced, unused === 0 ? "differ or are missing" : showUnused ? `${unused} more are not used here` : `${unused} not used here are hidden`);
        });
      };
      const filter = searchInput({
        placeholder: "Search groups and files",
        oninput: (value) => {
          typed = value;
          paint();
        },
      });
      filter.input.value = typed;
      picker.set(scope);
      count();
      paint();
      const footprint = data.storage.dotfiles_root_footprint;
      requestAnimationFrame(() => {
        collectable.set(found.length, "listed under Found here");
        stored.set(formatBytes(footprint?.size_bytes ?? 0), `${(footprint?.files ?? 0).toLocaleString()} files kept safe`);
      });
      // The first card says how much there is to move, once that is known.
      if (footprint?.size_bytes > 0) moreBlurbs.get("devops config dotfiles export")?.replaceChildren(`${formatBytes(footprint.size_bytes)} in one protected archive to carry, share or send.`);
      return h(
        "div",
        { class: "stack" },
        rise(h("div", { class: "stats" }, [inSync, attention, collectable, stored].map((tile) => tile.element))),
        h("div", { class: "table-bar" }, picker.element, filter.element, h("span", { class: "spacer" }), unused > 0 && unusedSwitch),
        holder,
      );
    },
  });

  const offered = MORE_TOOLS.filter(({ path }) => state.nodes.has(path));
  const moreBlurbs = new Map(offered.map(({ path, blurb }) => [path, h("span", { text: blurb })]));
  const moreCards = offered.map(({ path, title }) =>
    h("button", { class: "tool-card lit", type: "button", onclick: () => tools.open(path) }, emojiTile(state.nodes.get(path).icon || "✨", path, 40), h("span", { class: "tool-card-text" }, h("strong", { text: title }), moreBlurbs.get(path)), icon("arrow", 14)),
  );
  const overview = h(
    "div",
    {},
    viewHead({
      title: "Dotfiles", lede: "Your settings files, kept in one safe place and applied wherever you work.",
      actions: [
        agentButton(activity, PLACES.dotfiles),
        toolButton(tools, "devops config dotfiles collect", { label: "Collect", glyph: "plus" }),
        toolButton(tools, "devops config dotfiles sync", { label: "Save from this machine", glyph: "up", preset: { direction: "up" } }),
        toolButton(tools, "devops config dotfiles sync", { label: "Apply to this machine", glyph: "download", tone: "primary", preset: { direction: "down" } }),
      ],
    }),
    panel.element,
    h("div", { class: "tool-grid" }, moreCards),
  );
  const element = h("section", { class: "view", hidden: true }, overview);
  return { element, show: createParts({ element, built: { "": { element: overview, show: () => panel.ensure() } }, loaders: partLoaders("dotfiles"), context }) };

}
