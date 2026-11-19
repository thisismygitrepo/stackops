import { h, icon, toast } from "/assets/scripts/dom.js";
import { capture, markStale } from "../../data.js";
import { openDialog } from "../../overlays.js";
import { button, skeleton } from "../../widgets.js";
import { KIND_BY_ID, softenPaths } from "./health_model.js";
import { pathChip } from "./health_overview.js";

const FOCUSES = { configuration: "configuration", server: "mcp", hook: "hook", plugin: "plugin", skill: "skill", instructions: "instructions" };
const SCOPES = { local: "workspace", global: "user" };

// What is built in or set for the whole computer is read-only to a reset, and a protected place is never touched.
export const canRemove = (row) => row.reachable && Object.hasOwn(SCOPES, row.origin);

// Taking something away is the reset command narrowed to one thing: the page deletes and edits nothing itself, and that command's own checks apply.
const resetArguments = (agent, row, match) => ["agents", "reset", agent.id, "--directory", agent.directory, "--scope", SCOPES[row.origin], "--resource", FOCUSES[row.kind], `--match=${match}`, "--json"];

// The reset command picks things by a piece of text. Everything it lists at this row's path is read first, then the text only this row has is used.
async function planRemoval(agent, row) {
  const preview = async (match) => ({ match, plan: (await capture(resetArguments(agent, row, match))).json.plan });
  const atPath = await preview(row.path);
  const command = row.raw.detail.slice(row.raw.detail.indexOf(": ") + 2);
  const mine = atPath.plan.entries.filter((entry) => entry.path === row.path && (row.command ? entry.command === command : entry.name === row.raw.name && (row.kind !== "server" || entry.command === row.raw.detail)));
  if (mine.length === 0) return null;
  if (mine.length === atPath.plan.entries.length || (mine.length > 1 && !row.command)) return atPath;
  return preview(mine.length === 1 ? `${mine[0].name} ${mine[0].event} ${mine[0].command} ${mine[0].path}` : `${command} ${row.path}`);
}

function changeLine(change, entries) {
  const taken = entries.filter((entry) => entry.removal?.path === change.path);
  const deleted = change.action === "remove";
  const count = `${taken.length} ${taken.length === 1 ? "entry is" : "entries are"}`;
  const text = deleted
    ? `This ${taken.some((entry) => entry.removal.format === "directory") ? "folder, with everything in it," : "file"} is deleted`
    : `${count} ${taken.every((entry) => entry.removal.action === "disable") ? "switched off" : "taken out"} in this file, and the rest of it stays`;
  return h("li", {}, icon(deleted ? "trash" : "pencil", 15), h("div", {}, h("span", { text }), pathChip(change.path)));
}

// Shows what would change before anything does. Resolves to true once the thing is gone.
export function removeResource({ agent, row }) {
  const label = KIND_BY_ID[row.kind];
  const dialog = openDialog({ label: `Remove this ${label.one}`, size: "small removal" });
  const area = h("div", { class: "removal-area" }, skeleton(2, "row"));
  const cancel = button({ label: "Cancel", onclick: () => dialog.close(false) });
  const confirm = button({ label: "Remove", glyph: "trash", tone: "danger", onclick: apply });
  let chosen = null;
  confirm.disabled = true;

  function stop(text, reasons = []) {
    area.replaceChildren(h("p", { text }), h("ul", { class: "removal-reasons" }, reasons.map((reason) => h("li", { text: softenPaths(reason) }))));
    cancel.replaceChildren(h("span", { text: "Close" }));
    confirm.hidden = true;
  }

  async function apply() {
    confirm.disabled = true;
    cancel.disabled = true;
    try {
      const done = (await capture([...resetArguments(agent, row, chosen.match), "--apply"])).json;
      if (!done.applied) return stop("The reset stopped, and nothing was changed. What is in the way:", done.plan.blockers);
      dialog.close(true);
      toast(`Removed. ${agent.name} picks this up the next time it starts.`, "info");
      markStale();
    } catch (error) {
      stop(`This could not be removed. ${error.message}`);
    } finally {
      cancel.disabled = false;
    }
  }

  dialog.body.append(h("h2", { text: `Remove this ${label.one}?` }), h("code", { class: "removal-name", text: row.name }), area, h("div", { class: "dialog-actions" }, cancel, confirm));
  planRemoval(agent, row).then(
    (found) => {
      if (!found) return stop(`A reset has nothing of its own to take away here. This ${label.one} is built into ${agent.name}, or it comes from something else that has to be changed instead.`);
      if (found.plan.blockers.length > 0) return stop("A reset stops here, so nothing would be changed. What is in the way:", found.plan.blockers);
      chosen = found;
      const shared = found.plan.changes.some((change) => change.action === "remove") ? " Any other agent that shares it loses it too." : "";
      area.replaceChildren(h("ul", { class: "removal-plan" }, found.plan.changes.map((change) => changeLine(change, found.plan.entries))), h("p", { class: "removal-note", text: `This is permanent: nothing is backed up.${shared}` }));
      confirm.disabled = false;
    },
    (error) => stop(`This could not be checked. ${error.message}`),
  );
  return dialog.closed.then((answer) => answer === true);
}
