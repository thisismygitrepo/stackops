import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { openDialog } from "../../../overlays.js";
import { button, glyphTile, iconButton } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { developerEffects, restartSteps } from "./steps.js";
import { RESTART_LEDE, dirtyCount, home, shortId } from "./words.js";

// What a finished run is compared against to say what it changed.
export const snapshot = (state) => ({ version: state.installed?.version ?? state.started_version, head: state.checkout?.head?.sha ?? "" });

// The last stop before an update that deletes settings or publishes commits: what exactly goes, by name and by number, as it stands at this
// moment. Resolves to true only on an explicit yes. Committing and pushing also takes a tick, since it cannot be taken back from here.
export function confirmUpdate({ state, effects, options }) {
  const dialog = openDialog({ label: "Confirm the update", size: "machine-update-confirm" });
  const publishes = options.developer;
  const go = button({ label: publishes ? "Commit, push and update" : "Replace and update", glyph: "download", tone: "danger", onclick: () => dialog.close(true) });
  const agree = h("input", { type: "checkbox", onchange: () => (go.disabled = !agree.checked) });
  go.disabled = publishes;
  const parts = [];
  if (publishes) {
    const { checkout } = state;
    const dirty = dirtyCount(checkout);
    parts.push(
      h(
        "section",
        {},
        h("h3", {}, icon("branch", 15), `In ${home(checkout.path)}, before anything is updated`),
        h("ol", {}, developerEffects(state).map((text) => h("li", { text }))),
        dirty > 0 && h("ul", { class: "machine-update-files" }, checkout.names.map((name) => h("li", { text: name })), dirty > checkout.names.length && h("li", { class: "more", text: `and ${plural(dirty - checkout.names.length, "more file")}` })),
      ),
    );
  }
  if (options.settings) {
    const present = effects?.settings?.present ?? [];
    parts.push(
      h(
        "section",
        {},
        h("h3", {}, icon("sliders", 15), "After the update, to your app settings"),
        h("p", { text: present.length > 0 ? `Deletes the settings you have for ${plural(present.length, "program")} and puts the packaged ones in their place. No copy of yours is kept.` : "Puts the packaged settings in place for every program StackOps ships them for. Where you have a settings file of your own, it is deleted first and no copy is kept." }),
        present.length > 0 && h("div", { class: "machine-update-names" }, present.map((name) => h("span", { text: name }))),
      ),
    );
  }
  dialog.body.append(
    h("header", { class: "machine-update-confirm-head" }, glyphTile("alert", 350, 46), h("div", {}, h("h2", { text: publishes ? "Commit, push, then update?" : "Replace your app settings?" }), h("p", { text: "This is what the update does besides installing the new version. It starts as soon as you confirm." }))),
    h("div", { class: "machine-update-confirm-parts" }, parts),
    publishes && h("label", { class: "machine-update-ack" }, agree, h("span", { text: "I want these changes committed and pushed." })),
    h("div", { class: "dialog-actions" }, button({ label: "Go back", onclick: () => dialog.close(false) }), go),
  );
  return dialog.closed.then((answer) => answer === true);
}

function changeLine(run, state) {
  const now = snapshot(state);
  const head = state.checkout?.head;
  if (now.version !== run.before.version) return `StackOps went from ${run.before.version} to ${now.version}.`;
  if (now.head !== run.before.head && head) return `The source folder moved on to "${head.title}", commit ${shortId(head.sha)}.`;
  return state.route === "checkout" ? "No new commits came in. The tool was still built again from the source folder." : `StackOps was already at ${now.version}. uv and the packages StackOps uses were still brought up to date.`;
}

const banner = (tone, mark, ...content) => h("section", { class: `machine-update-banner ${tone}` }, mark, ...content);
const text = (title, ...body) => h("div", { class: "machine-update-banner-text" }, h("h2", { text: title }), ...body);

// What an update is doing, and once it has ended, what it changed and what is left to do. With no run of this page's own, it still speaks up
// when the server reports that StackOps was installed again after this web UI started.
export function runBanner({ run, state, onReveal, onDismiss }) {
  if (!run) {
    if (!state.restart_needed) return null;
    return banner("warn", h("span", { class: "task-mark stopped" }, icon("power", 22)), text("StackOps was installed again after this web UI started", h("p", { text: RESTART_LEDE }), restartSteps(state)));
  }
  const reveal = (label) => button({ label, glyph: "terminal", small: true, onclick: onReveal });
  if (run.phase === "running") {
    return banner("working", h("span", { class: "task-mark" }, h("i", { class: "ring" })), text("Updating StackOps", h("p", { text: "It runs in the Activity panel. If it asks for a password, type it there." })), reveal("Show progress"));
  }
  const dismiss = iconButton("close", "Dismiss", onDismiss);
  const finished = h("small", { class: "dim", text: `Finished at ${formatClock(run.finishedAt)}` });
  if (run.exitCode === 0) {
    return banner("good", h("span", { class: "task-mark done" }, icon("check", 22)), text("Updated. Now restart the web UI", h("p", { text: `${changeLine(run, state)} ${RESTART_LEDE}` }), restartSteps(state), finished), reveal("Show what happened"), dismiss);
  }
  const title = run.stopped ? "The update was stopped" : "The update stopped with a problem";
  const body = run.stopped ? "Whatever had finished by then stays done. The page shows where things stand now." : "The steps after the one that failed did not run. The console shows which step it was and what it said.";
  return banner("bad", h("span", { class: `task-mark ${run.stopped ? "stopped" : "failed"}` }, icon(run.stopped ? "stop" : "alert", 22)), text(title, h("p", { text: body }), finished), reveal("Show what happened"), dismiss);
}
