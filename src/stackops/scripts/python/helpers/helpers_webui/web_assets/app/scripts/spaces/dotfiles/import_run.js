import { toast } from "/assets/scripts/dom.js";
import { markStale } from "../../data.js";
import { button } from "../../widgets.js";
import { reasonOf, runBanner, typeWhenAsked } from "./kit.js";
import { APPLY_PRESET, IMPORT_PROMPT, SYNC_PATH, count } from "./words.js";

// Runs the import command as a task and reports how it stands through `onPhase`. With `password` it brings in the archive at `source`, typing
// the password into the command's prompt. Without one it copies straight from `remote` over SSH, in sight, because a sign-in may be asked for.
// A task that runs out of sight does not tell the pages to read again when it ends, so that is done here: the whole folder has changed.
export async function runImport({ activity, source, password, remote, read, onPhase }) {
  const overSsh = password === null;
  let task;
  try {
    task = await activity.start({
      title: overSsh ? `Copy dotfiles from ${remote}` : "Bring in dotfiles", emoji: "📥", interactive: true, reveal: overSsh,
      arguments: ["devops", "config", "dotfiles", "import", ...(overSsh ? ["--ssh", "--remote", remote] : ["--url", source])],
    });
  } catch (error) {
    toast(error.message);
    return;
  }
  const run = { phase: "working", overSsh, remote, id: task.id, needsTyping: false, result: "", reason: "", files: 0 };
  onPhase(run);
  if (!overSsh) {
    const typed = await typeWhenAsked(task, IMPORT_PROMPT, password);
    if (typed === "unseen" || typed === "unsafe") {
      run.needsTyping = true;
      activity.reveal(task.id);
      onPhase(run);
    }
  }
  const outcome = await task.done;
  if (!overSsh && !run.needsTyping) markStale();
  const machine = await read();
  Object.assign(run, { phase: "done", result: outcome.exit_code === 0 ? "done" : outcome.stopped ? "stopped" : "failed", reason: outcome.exit_code === 0 ? "" : reasonOf(task), files: machine?.files ?? 0 });
  onPhase(run);
}

export function importBanner({ run, tools, onReveal, onDismiss }) {
  const show = button({ label: "Show the console", glyph: "terminal", small: true, onclick: onReveal });
  const close = button({ label: "Dismiss", small: true, tone: "ghost", onclick: onDismiss });
  if (run.phase === "working") {
    return runBanner({ tone: "", busy: true, title: run.overSsh ? `Copying from ${run.remote}…` : "Bringing the archive in…", text: run.needsTyping ? "Type the password in the console to go on." : run.overSsh ? "The console asks if a sign-in is needed." : "It is opened, checked and put in place of the dotfiles folder.", actions: [show] });
  }
  if (run.result === "done") {
    return runBanner({
      tone: "good", title: "The settings are on this machine", text: `Your dotfiles folder now holds ${count(run.files, "file", "files")}. They are not in use yet. Applying puts each one where its program looks for it.`,
      actions: [button({ label: "Apply to this machine", glyph: "download", small: true, tone: "primary", onclick: () => tools.open(SYNC_PATH, { preset: APPLY_PRESET }) }), close],
    });
  }
  return runBanner({ tone: "bad", title: run.result === "stopped" ? "Stopped before it finished" : "Nothing was brought in", text: run.reason || "The console has the details.", actions: [show, close] });
}
