import { h, tildify, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { agentButton } from "../agent_ask.js";
import { capture, markStale } from "../data.js";
import { confirmAction, openDialog } from "../overlays.js";
import { button } from "../widgets.js";

// Deleting an app is the CLI's own uninstall command: the page deletes nothing itself, and that command's checks apply. It deletes a program file
// that StackOps put in its install folder. An app that a package manager owns is removed by that manager's uninstall command when the catalog
// tells which one, and otherwise gets the reason here and is not asked about. Resolves to true once the app is gone.
export async function removeApp(app, activity) {
  const home = state.boot.home;
  if (app.removal_problem) {
    const dialog = openDialog({ label: `${app.name} cannot be deleted from here`, size: "small" });
    dialog.body.append(
      h("h2", { text: `StackOps cannot delete ${app.name}` }),
      h("p", { text: app.removal_problem.replaceAll(home, "~") }),
      h("div", { class: "dialog-actions" }, button({ label: "Close", onclick: () => dialog.close() })),
    );
    await dialog.closed;
    return false;
  }
  const sure = await confirmAction({
    title: `Delete ${app.name}?`, confirm: "Delete", tone: "danger",
    ask: agentButton(
      activity,
      { title: `Delete ${app.name}`, commands: ["devops software uninstall"], notes: [app.removal_command ? `Deleting it runs “${app.removal_command}”.` : `Deleting it removes ${app.binary}.`], ideas: ["What do I lose if I delete this app?"] },
      { small: true },
    ),
    body: app.removal_command
      ? `This runs “${app.removal_command}” on this machine. It shows in Activity, where you can answer what it asks, such as your password. Settings and data the app keeps elsewhere stay. You can install it again from here.`
      : `${tildify(app.binary, home)} is deleted from this machine. Settings and data the app keeps elsewhere stay. You can install it again from here.`,
  });
  if (!sure) return false;
  // An uninstall command runs as a task like an install does, because it may ask for a password or a yes. The task says how it went, and
  // tells the pages to read their data again when it ends.
  if (app.removal_command) {
    try {
      const task = await activity.start({ title: `Delete ${app.name}`, emoji: "🗑️", arguments: ["devops", "software", "uninstall", app.name], interactive: true, reveal: true });
      return (await task.done).exit_code === 0;
    } catch (error) {
      toast(`${app.name} was not deleted. ${error.message}`);
      return false;
    }
  }
  try {
    const [outcome] = (await capture(["devops", "software", "uninstall", app.name, "--json"])).json;
    if (!outcome.removed) throw new Error(outcome.problem);
  } catch (error) {
    toast(`${app.name} was not deleted. ${error.message}`);
    return false;
  }
  toast(`${app.name} was deleted.`, "info");
  markStale();
  return true;
}
