import { h, tildify, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { capture, markStale } from "../data.js";
import { confirmAction, openDialog } from "../overlays.js";
import { button } from "../widgets.js";

// Deleting an app is the CLI's own uninstall command: the page deletes nothing itself, and that command's checks apply. It deletes a program file
// that StackOps put in its install folder and nothing else, so an app that a package manager owns gets the reason here and is not asked about.
// Resolves to true once the app is gone.
export async function removeApp(app) {
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
    body: `${tildify(app.binary, home)} is deleted from this machine. Settings and data the app keeps elsewhere stay. You can install it again from here.`,
  });
  if (!sure) return false;
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
