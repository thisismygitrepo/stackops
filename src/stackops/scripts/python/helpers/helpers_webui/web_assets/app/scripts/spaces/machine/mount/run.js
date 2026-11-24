import { toast } from "/assets/scripts/dom.js";
import { consoleText } from "../../../console_session.js";
import { markStale } from "../../../data.js";
import { titleOf } from "./model.js";

const REASON_LIMIT = 320;

// What the command said went wrong, from the console of its run: its "Mount failed" line with what follows it, or what stands under "Error".
// The line the server closes every run with ("[exit 1 · 0.9s]") ends it.
function reasonIn(text) {
  const lines = text.split("\n").map((line) => line.replace(/[│╭╮╰╯─]/g, "").trim()).filter(Boolean);
  const closing = lines.findIndex((line) => /^\[(exit \d+|stopped|done) · /.test(line));
  const said = closing < 0 ? lines : lines.slice(0, closing);
  const failed = said.findIndex((line) => line.startsWith("Mount failed:"));
  const error = said.findIndex((line) => /^error(:|$)/i.test(line));
  const reason = failed >= 0 ? said.slice(failed).join(" ").replace(/^Mount failed:\s*/, "") : error >= 0 ? said.slice(/^error$/i.test(said[error]) ? error + 1 : error).join(" ") : "";
  return reason.length > REASON_LIMIT ? `${reason.slice(0, REASON_LIMIT)}…` : reason;
}

// Mounts as a task in the Activity panel, which is where a password is typed, then reads the devices again to say how it went. The panel only
// opens by itself when something will be asked for. A task that runs out of sight does not tell the other pages to read again when it ends,
// so that is done here. `onPhase` gets the run when it starts and again when it is over; `read` reads the list.
// It counts as mounted when the command says so or the list shows it: what is inside an encrypted device is mounted under another name, so the
// list cannot always tell. The place comes from the list, or from the plan when that named a folder.
export async function runMount({ activity, device, plan, read, onPhase }) {
  const name = titleOf(device);
  const asks = plan.asks.length > 0;
  let task;
  try {
    task = await activity.start({ title: `Mount ${name}`, emoji: "🔌", arguments: plan.arguments, interactive: true, reveal: asks });
  } catch (error) {
    toast(error.message);
    return;
  }
  const run = { phase: "mounting", id: task.id, name, asks, result: "", place: "", reason: "", finishedAt: 0 };
  onPhase(run);
  const outcome = await task.done;
  if (!asks) markStale();
  const picture = await read();
  const now = picture?.devices.find((other) => other.path === device.path);
  const mounted = outcome.exit_code === 0 || now?.state === "mounted";
  Object.assign(run, {
    phase: "done", result: mounted ? "mounted" : outcome.stopped ? "stopped" : "failed",
    place: now?.mounted_at || (mounted ? plan.place.shown : ""),
    reason: mounted ? "" : reasonIn(consoleText(task.terminal)),
    finishedAt: outcome.finished_at ?? Date.now() / 1000,
  });
  onPhase(run);
}
