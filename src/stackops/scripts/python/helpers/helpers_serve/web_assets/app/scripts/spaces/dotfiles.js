import { h, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { confirmAction } from "../overlays.js";
import { createView, editButton, toolButton, toolCard } from "../space_kit.js";
import { notice, searchInput, segmented, stat } from "../widgets.js";
import { formatBytes, plural } from "../words.js";
import { COLLECT_WORDS, foundGroups, managedGroups } from "./dotfiles_groups.js";

const IN_SYNC = "Configured";

export function createDotfilesSpace({ activity, tools }) {
  let scope = "user";

  async function collect(group) {
    const sure = await confirmAction({ title: `Collect “${group}”?`, body: "Its files are moved into your dotfiles folder, linked back to where they were, and added to your list.", confirm: "Collect" });
    if (sure) activity.start({ title: `Collect ${group}`, emoji: "🧺", arguments: ["devops", "config", "dotfiles", "collect", "--which", group], interactive: true, reveal: true }).catch((error) => toast(error.message));
  }

  const panel = createLivePanel({
    // The switches left out pick which sections the answer holds; the page needs all of them, so each one alone showed a false empty state.
    title: "What is managed", path: "devops config dotfiles status", extra: ["--json"], locked: ["mappers", "sync", "radar", "storage", "expand"],
    actions: [editButton(activity, { title: "your dotfiles list", kind: "dotfiles" }, { label: "Edit my list", small: true })],
    render: (data, { setCount }) => {
      const everything = [...data.sync.user, ...data.sync.library];
      const synced = everything.filter((entry) => entry.status === IN_SYNC).length;
      const found = data.radar.filter((plan) => Object.hasOwn(COLLECT_WORDS, plan.verdict));
      setCount(`${plural(everything.length, "file")} · ${synced} in sync`);
      const tiles = [
        [stat({ glyph: "check", hue: 155, label: "In sync" }), synced, `of ${everything.length} managed files`],
        [stat({ glyph: "alert", hue: 30, label: "Need attention" }), everything.length - synced, "differ or are missing"],
        [stat({ glyph: "plus", hue: 252, label: "Ready to collect" }), found.length, "listed under Found here"],
        [stat({ glyph: "folder", hue: 200, label: "Stored" }), formatBytes(data.storage.dotfiles_root_footprint?.size_bytes ?? 0), `${(data.storage.dotfiles_root_footprint?.files ?? 0).toLocaleString()} files kept safe`],
      ];
      const holder = h("div", { class: "session-list" });
      let term = "";
      const paint = () => {
        const matches = (...words) => words.join(" ").toLowerCase().includes(term);
        const groups =
          scope === "found"
            ? foundGroups(found.filter((plan) => matches(plan.group, plan.name)), collect)
            : managedGroups(data.sync[scope].filter((entry) => matches(entry.program, entry.file_name, entry.status)), (direction, group) => tools.open("devops config dotfiles sync", { preset: { direction, which: group, source: scope } }));
        if (groups.length) return holder.replaceChildren(...groups);
        const body = term ? "No group, file, or status matches that filter." : scope === "found" ? "Every settings file StackOps recognises on this machine is already on a list." : "No files of this kind are managed.";
        holder.replaceChildren(notice({ glyph: "folder", title: "Nothing here", body }));
      };
      const picker = segmented([["user", `Yours · ${data.sync.user.length}`], ["library", `Built in · ${data.sync.library.length}`], ["found", `Found here · ${found.length}`]], (value) => {
        scope = value;
        picker.set(scope);
        paint();
      });
      const filter = searchInput({
        placeholder: "Filter groups",
        oninput: (value) => {
          term = value.trim().toLowerCase();
          paint();
        },
      });
      picker.set(scope);
      paint();
      requestAnimationFrame(() => tiles.forEach(([tile, value, note]) => tile.set(value, note)));
      return h("div", { class: "stack" }, rise(h("div", { class: "stats" }, tiles.map(([tile]) => tile.element))), h("div", { class: "table-bar" }, picker.element, filter.element), holder);
    },
  });

  const element = createView(
    {
      title: "Dotfiles", lede: "Your settings files, kept in one safe place and applied wherever you work.",
      actions: [
        toolButton(tools, "devops config dotfiles collect", { label: "Collect", glyph: "plus" }),
        toolButton(tools, "devops config dotfiles sync", { label: "Save from this machine", glyph: "up", preset: { direction: "up" } }),
        toolButton(tools, "devops config dotfiles sync", { label: "Apply to this machine", glyph: "download", tone: "primary", preset: { direction: "down" } }),
      ],
    },
    panel.element,
    h(
      "div",
      { class: "tool-grid" },
      [["devops config dotfiles export", "Move to a new machine"], ["devops config dotfiles import", "Bring settings from another machine"], ["devops config dotfiles register", "Add one file"]]
        .filter(([path]) => state.nodes.has(path))
        .map(([path, label]) => toolCard(tools, state.nodes.get(path), label)),
    ),
  );

  return { element, show: () => panel.ensure() };
}
