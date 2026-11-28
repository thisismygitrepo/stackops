import { h, tildify, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { agentButton } from "../../../agent_ask.js";
import { confirmAction } from "../../../overlays.js";
import { button, callout } from "../../../widgets.js";
import { ADD_COMMAND, APPLY_COMMAND, REMOVE_COMMAND } from "./add_script.js";
import { applyRemembered, readRemembered } from "./api.js";

const NOTHING = { file: "", missing: [], unlisted: [], problem: "" };
const named = (names) => new Intl.ListFormat("en", { type: "conjunction" }).format(names);

// The startup list in the dotfiles, where the scripts StackOps starts are kept for the person's other machines, set against this machine:
// what the list names for this system and is not started here, and the scripts of the dotfiles that start here without being on it. Each
// side has its way to be settled, which is what `utils machine autostart-apply` does. Nothing is shown when the two agree.
// `reload` reads the page again once something was changed.
export function createStartupList({ activity, outcome, reload }) {
  const element = h("div", { class: "autostart-notes" });
  let kept = NOTHING;
  let applying = false;

  // With `prune` the scripts that start here without being on the list are stopped as well, which is asked first.
  async function match(prune) {
    const { missing, unlisted } = kept;
    if (applying) return;
    if (prune) {
      const one = unlisted.length === 1;
      const sure = await confirmAction({
        title: `Stop starting ${named(unlisted)} here?`, confirm: "Stop starting here", tone: "danger",
        body: `Your startup list does not name ${one ? "it" : "them"} for this system, so ${one ? "it" : "they"} will no longer start on ${one ? "its" : "their"} own on this machine. The ${one ? "script itself is" : "scripts themselves are"} kept.${missing.length > 0 ? ` What the list does name is started here as well: ${named(missing.map((script) => script.name))}.` : ""}`,
      });
      if (!sure) return;
    }
    applying = true;
    paint();
    try {
      const done = await applyRemembered(prune);
      const said = [done.added.length > 0 && `${named(done.added)} ${done.added.length === 1 ? "starts" : "start"} here from now on.`, done.removed.length > 0 && `${named(done.removed)} no longer ${done.removed.length === 1 ? "starts" : "start"} here.`].filter(Boolean);
      if (said.length > 0) outcome.show({ said: said.join(" ") });
      for (const failure of done.failures) toast(failure);
    } catch (error) {
      toast(error.message);
    }
    applying = false;
    await reload();
  }

  function paint() {
    const { file, missing, unlisted, problem } = kept;
    if (problem) return element.replaceChildren(callout({ tone: "warn", title: "Your startup list could not be read", text: problem }));
    if (missing.length === 0 && unlisted.length === 0) return element.replaceChildren();
    const lines = [
      missing.length > 0 && `${named(missing.map((script) => (script.when === "boot" ? `${script.name} (with the computer)` : script.name)))} ${missing.length === 1 ? "is" : "are"} on the list for this system and ${missing.length === 1 ? "does" : "do"} not start here yet.`,
      unlisted.length > 0 && `${named(unlisted)} ${unlisted.length === 1 ? "starts" : "start"} here without being on the list.`,
    ].filter(Boolean);
    const start = button({ label: missing.length === 1 ? "Start it here" : "Start them here", glyph: "power", tone: "primary", small: true, onclick: () => match(false) });
    const stop = button({ label: unlisted.length === 1 ? "Stop it here" : "Stop them here", small: true, onclick: () => match(true) });
    start.disabled = stop.disabled = applying;
    const ask = agentButton(activity, { title: "The startup list", commands: [APPLY_COMMAND, ADD_COMMAND, REMOVE_COMMAND], about: `The list of scripts that start on their own on the person's machines, kept in ${tildify(file, state.boot.home)} in their dotfiles, and how this machine differs from it.` }, { small: true });
    element.replaceChildren(callout({ tone: "", title: "This machine and your startup list differ", text: lines.join(" "), where: file, extra: h("div", { class: "view-actions" }, missing.length > 0 && start, unlisted.length > 0 && stop, ask) }));
  }

  return {
    element,
    // A server older than this page has no startup list to tell of: then the page says nothing about one.
    read: () => readRemembered().catch((error) => (error.status === 404 ? NOTHING : { ...NOTHING, problem: error.message })),
    show(view) {
      kept = { ...NOTHING, ...view };
      paint();
    },
  };
}
