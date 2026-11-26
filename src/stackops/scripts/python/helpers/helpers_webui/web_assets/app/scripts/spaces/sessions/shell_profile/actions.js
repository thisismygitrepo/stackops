import { h, icon, toast } from "/assets/scripts/dom.js";
import { agentButton } from "../../../agent_ask.js";
import { confirmAction } from "../../../overlays.js";
import { editFile } from "../../../space_kit.js";
import { button, copyChip, iconButton } from "../../../widgets.js";
import { COPY_TOOL, SHELLS, STANDINGS, TOOL_PATH, profileNames, shortPath, standingOf, standingText } from "./words.js";

const RELOAD_HINT = "Open a new terminal to see it. A terminal that is already open picks it up when you run this in it.";

// What the page can do. Two things run as a task the person watches, with a banner that says how it went: setting a shell up, and copying
// StackOps' files for a shell that gets its line by hand. Then there is installing a missing program and opening a profile in the editor.
// `read()` gives the state the page last showed, `reload()` reads it again and resolves once that is on the page, and `onChange` is called
// when the banner has something new to say.
export function createActions({ activity, read, reload, onChange }) {
  let run = null;
  let starting = false;

  // What a run does to the shell's profile, for the question asked before it.
  function linesText(shell) {
    const names = profileNames(shell);
    const missing = names.filter((_, index) => !shell.files[index].line_present);
    if (missing.length === 0) return `${names.join(" and ")} already ${names.length > 1 ? "have their lines and stay as they are" : "has its line and stays as it is"}.`;
    if (shell.files.some((file) => file.old_line_present)) return `It also swaps the old StackOps line in ${missing.join(" and ")} for the current one.`;
    return `It also adds one line${missing.length > 1 ? " each" : ""} to ${missing.join(" and ")}.`;
  }

  // One run at a time. `ask` is the question's title, button and last sentence; `judge` turns the shell as the run left it into the banner's words.
  async function launch(shell, { title, doing, emoji, runArguments, ask, judge }) {
    if (starting || run?.phase === "running") return;
    const settings = read().folders.find((folder) => folder.name === "settings");
    // The settings folder is replaced as a whole. Once it exists there can be changes in it to lose, so the run takes a yes first.
    if (settings.exists) {
      const body = `This replaces the folder ${shortPath(settings.path)} with a fresh copy of the settings StackOps ships, so anything you changed inside that folder is lost. StackOps' scripts are copied afresh too. ${ask.tail}`;
      if (!(await confirmAction({ title: ask.title, confirm: ask.confirm, body }))) return;
    }
    starting = true;
    onChange();
    let task;
    try {
      task = await activity.start({ title, emoji, arguments: runArguments, interactive: true, reveal: true });
    } catch (error) {
      starting = false;
      onChange();
      toast(error.message);
      return;
    }
    starting = false;
    run = { id: task.id, phase: "running", title: `${doing}…`, text: "It runs in the activity panel.", painted: "" };
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
    // How it went is settled here and not judged again later: a profile also changes without this run.
    const after = read().shells.find((candidate) => candidate.id === shell.id);
    const failed = { good: false, title: outcome.exit_code === 0 ? `${doing} ran, but it did not take` : outcome.stopped ? `${doing} was stopped` : `${doing} did not finish`, text: "The activity panel shows how far it got." };
    run = { ...run, phase: "done", command: "", ...(outcome.exit_code === 0 && after && !after.blocker ? judge(after) : failed) };
    onChange();
  }

  function setUp(shell) {
    const { name } = SHELLS[shell.id];
    const again = !STANDINGS[standingOf(shell)].due;
    return launch(shell, {
      title: `Set up ${name}`, doing: `Setting up ${name}`, emoji: "🐚", runArguments: [...TOOL_PATH.split(" "), "--shell", shell.route],
      ask: { title: again ? `Set up ${name} again?` : `Set up ${name}?`, confirm: again ? "Set up again" : "Set up", tail: linesText(shell) },
      judge: (after) => (standingOf(after) === "ready" ? { good: true, title: `${name} is set up`, text: RELOAD_HINT, command: after.reload_command } : { good: false, title: `The run finished, but ${name} is not set up`, text: standingText(after, standingOf(after)) }),
    });
  }

  // For a shell the command does not act on: the same copying a setup run does, with no line added to a profile.
  function copyFiles(shell) {
    const { name } = SHELLS[shell.id];
    const profile = profileNames(shell).join(" and ");
    return launch(shell, {
      title: "Copy StackOps' files", doing: "Copying StackOps' files", emoji: "📋", runArguments: COPY_TOOL,
      ask: { title: "Copy StackOps' files?", confirm: "Copy", tail: shell.files.some((file) => file.old_line_present) ? `It also swaps the old StackOps line in ${profile} for the current one.` : `${profile} is not changed.` },
      judge: (after) =>
        !after.setup_in_place || !after.setup_current
          ? { good: false, title: "The run finished, but the files are not in place", text: standingText(after, standingOf(after)) }
          : standingOf(after) === "ready"
            ? { good: true, title: `StackOps' files are in place for ${name}`, text: RELOAD_HINT, command: after.reload_command }
            : { good: true, title: "StackOps' files are in place", text: `${name} loads them once the line is in ${profile}.` },
    });
  }

  function banner() {
    if (!run) return null;
    const working = run.phase === "running";
    // The page draws the banner again each time it reads the machine, so it only plays its entrance when it has something new to say.
    const fresh = run.painted === run.phase ? "" : " fresh";
    run.painted = run.phase;
    return h(
      "section",
      { class: `shellprof-banner ${working ? "working" : run.good ? "good" : "warn"}${fresh}` },
      h("span", { class: `task-mark${working ? "" : run.good ? " done" : " failed"}` }, working ? h("i", { class: "ring" }) : icon(run.good ? "check" : "alert", 22)),
      h("div", { class: "shellprof-banner-text" }, h("h2", { text: run.title }), h("p", { text: run.text }), !working && run.command && copyChip(run.command)),
      button({ label: working ? "Show progress" : "Show what happened", glyph: "terminal", small: true, onclick: () => activity.reveal(run.id) }),
      iconButton("close", "Dismiss", () => {
        run = null;
        onChange();
      }),
    );
  }

  return {
    setUp, copyFiles, banner,
    busy: () => starting || run?.phase === "running",
    install: (app, name) => activity.start({ title: `Install ${name}`, emoji: "📦", arguments: ["devops", "software", "install", app], interactive: true, reveal: true }).catch((error) => toast(error.message)),
    openFile: (file) => editFile(activity, { title: shortPath(file.path), kind: "file", path: file.path }),
    // The button that stands beside a profile's "Open in editor".
    askAbout: (file) =>
      agentButton(
        activity,
        {
          title: shortPath(file.path), commands: [TOOL_PATH], files: [{ label: "the shell profile", path: file.path }],
          about: "A shell reads its profile each time a terminal opens. One line in it loads StackOps' short commands, prompt and history search.",
          ideas: ["Explain what this profile loads, line by line", "Add this to my profile: …"],
        },
        { small: true },
      ),
  };
}
