import { toast } from "/assets/scripts/dom.js";
import { api } from "/assets/scripts/state.js";
import { consoleText } from "../../console_session.js";
import { reasonOf, typeWhenAsked } from "./kit.js";
import { archivePlace, shareAddress } from "./export_steps.js";
import { EXPORT_PROMPT } from "./words.js";

const OFFER_POLL_MILLISECONDS = 300;

// Resolves once the command has said the archive is on offer, which it does when its server answers, or once the task has ended.
function offered(task, address) {
  return new Promise((resolve) => {
    let over = false;
    task.done.then(() => (over = true));
    const look = () => {
      if (over) return resolve(false);
      if (task.terminal && consoleText(task.terminal).includes(`Ready: ${address}`)) return resolve(true);
      setTimeout(look, OFFER_POLL_MILLISECONDS);
    };
    look();
  });
}

// Runs the export command as a task and reports how it stands through `onPhase`. The command asks for the password in its console; the page
// types it there. The task runs out of sight unless it may ask for more, as a sign-in over SSH does. `read` reads the plan again, which is
// how the page learns that the archive is there.
export async function runExport({ activity, plan, choice, read, onPhase }) {
  const { way } = choice;
  const password = choice.password;
  const remote = choice.remote.trim();
  const runArguments = ["devops", "config", "dotfiles", "export", ...(choice.elsewhere ? ["--output", choice.place.path] : []), ...(way === "share" ? ["--serve"] : []), ...(way === "ssh" ? ["--ssh", "--remote", remote] : [])];
  let task;
  try {
    task = await activity.start({ title: way === "ssh" ? `Send dotfiles to ${remote}` : way === "share" ? "Offer dotfiles on the network" : "Make a dotfiles archive", emoji: "📤", arguments: runArguments, interactive: true, reveal: way === "ssh" });
  } catch (error) {
    toast(error.message);
    return;
  }
  const run = { phase: "packing", way, remote, id: task.id, elsewhere: choice.elsewhere, place: archivePlace(plan, choice), needsTyping: false, result: "", reason: "", stop: () => api.stopRun(task.id).catch((error) => toast(error.message)) };
  onPhase(run);
  const typed = await typeWhenAsked(task, EXPORT_PROMPT, password);
  if (typed === "unseen" || typed === "unsafe") {
    run.needsTyping = true;
    activity.reveal(task.id);
    onPhase(run);
  }
  if (way === "share" && (await offered(task, shareAddress(plan)))) {
    run.phase = "offering";
    await read();
    onPhase(run);
  }
  const outcome = await task.done;
  const wasOffering = run.phase === "offering";
  run.phase = "done";
  run.result = wasOffering ? "offered" : outcome.exit_code === 0 ? (way === "ssh" ? "sent" : "made") : outcome.stopped ? "stopped" : "failed";
  run.reason = run.result === "failed" ? reasonOf(task) : "";
  await read();
  onPhase(run);
}
