import { h, icon, toast } from "/assets/scripts/dom.js";
import { confirmAction } from "../../../overlays.js";
import { editFile } from "../../../space_kit.js";
import { button, copyChip, iconButton } from "../../../widgets.js";
import { SHELLS, STANDINGS, TOOL_PATH, shortPath, standingOf, standingText } from "./words.js";

// What the page can do: set a shell up as a task the person watches, with a banner that says how it went; install a missing program; open a
// profile in the editor. `read()` gives the state the page last showed, `reload()` reads it again and resolves once that is on the page, and
// `onChange` is called when the banner has something new to say.
export function createActions({ activity, read, reload, onChange }) {
  let run = null;
  let starting = false;

  const linesText = (shell) => {
    const missing = shell.files.filter((file) => !file.line_present).map((file) => shortPath(file.path));
    const all = shell.files.map((file) => shortPath(file.path)).join(" and ");
    return missing.length === 0 ? `${all} already ${shell.files.length > 1 ? "have their lines and stay as they are" : "has its line and stays as it is"}.` : `It also adds one line to ${missing.join(" and ")}.`;
  };

  async function setUp(shell) {
    if (starting || run?.phase === "running") return;
    const { name } = SHELLS[shell.id];
    const settings = read().folders.find((folder) => folder.name === "settings");
    // The settings folder is replaced as a whole. Once it exists there can be changes in it to lose, so the run takes a yes first.
    if (settings.exists) {
      const again = !STANDINGS[standingOf(shell)].due;
      const sure = await confirmAction({
        title: again ? `Set up ${name} again?` : `Set up ${name}?`, confirm: again ? "Set up again" : "Set up",
        body: `This replaces the folder ${shortPath(settings.path)} with a fresh copy of the settings StackOps ships, so anything you changed inside that folder is lost. StackOps' scripts are copied afresh too. ${linesText(shell)}`,
      });
      if (!sure) return;
    }
    starting = true;
    onChange();
    let task;
    try {
      task = await activity.start({ title: `Set up ${name}`, emoji: "🐚", arguments: [...TOOL_PATH.split(" "), "--shell", shell.route], interactive: true, reveal: true });
    } catch (error) {
      starting = false;
      onChange();
      toast(error.message);
      return;
    }
    starting = false;
    run = { id: task.id, shellId: shell.id, phase: "running", exitCode: null, stopped: false, painted: "" };
    onChange();
    const outcome = await task.done;
    // The banner only says how it went once the page shows what the run left behind, so the two never disagree.
    const current = await reload();
    if (run?.id !== task.id) return;
    // A page that could not be read again says so itself, and a banner would only repeat what was true before the run.
    if (!current) {
      run = null;
      return;
    }
    run = { ...run, phase: "done", exitCode: outcome.exit_code, stopped: Boolean(outcome.stopped) };
    onChange();
  }

  function banner() {
    if (!run) return null;
    const shell = read().shells.find((candidate) => candidate.id === run.shellId);
    const { name } = SHELLS[run.shellId];
    const reveal = (label) => button({ label, glyph: "terminal", small: true, onclick: () => activity.reveal(run.id) });
    const dismiss = iconButton("close", "Dismiss", () => {
      run = null;
      onChange();
    });
    // The page draws the banner again each time it reads the machine, so it only plays its entrance when it has something new to say.
    const fresh = run.painted === run.phase ? "" : " fresh";
    run.painted = run.phase;
    if (run.phase === "running") {
      return h(
        "section",
        { class: `shellprof-banner working${fresh}` },
        h("span", { class: "task-mark" }, h("i", { class: "ring" })),
        h("div", { class: "shellprof-banner-text" }, h("h2", { text: `Setting up ${name}…` }), h("p", { text: "It runs in the activity panel." })),
        reveal("Show progress"),
        dismiss,
      );
    }
    const standing = standingOf(shell);
    const good = run.exitCode === 0 && !STANDINGS[standing].due;
    const title = good ? `${name} is set up` : run.exitCode === 0 ? `The run finished, but ${name} is not set up` : run.stopped ? `Setting up ${name} was stopped` : `Setting up ${name} did not finish`;
    const text = good ? "Open a new terminal to see it. A terminal that is already open picks it up when you run this in it." : run.exitCode === 0 ? standingText(shell, standing) : "The activity panel shows how far it got.";
    return h(
      "section",
      { class: `shellprof-banner ${good ? "good" : "warn"}${fresh}` },
      h("span", { class: `task-mark ${good ? "done" : "failed"}` }, icon(good ? "check" : "alert", 22)),
      h("div", { class: "shellprof-banner-text" }, h("h2", { text: title }), h("p", { text }), good && shell.reload_command && copyChip(shell.reload_command)),
      reveal("Show what happened"),
      dismiss,
    );
  }

  return {
    setUp, banner,
    busy: () => starting || run?.phase === "running",
    install: (app, name) => activity.start({ title: `Install ${name}`, emoji: "📦", arguments: ["devops", "software", "install", app], interactive: true, reveal: true }).catch((error) => toast(error.message)),
    openFile: (file) => editFile(activity, { title: shortPath(file.path), kind: "file", path: file.path }),
  };
}
