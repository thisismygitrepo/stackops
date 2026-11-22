import { toast } from "/assets/scripts/dom.js";
import { isMeasured } from "./disk_cleanup_rows.js";
import { CLEANUP_TOOL } from "./disk_cleanup_words.js";

// Cleans exactly the chosen places as a visible task, then measures them again to say what was freed. `onPhase` gets the run every time it moves on.
export async function runCleanup({ activity, scanner, items, roots, onPhase }) {
  const keys = items.map((target) => target.key);
  const searched = items.some((target) => target.action_kind === "projects");
  const freeNow = () => scanner.refreshDisk().then(() => scanner.disk().free, () => null);
  const freeBefore = await freeNow();
  let task;
  try {
    task = await activity.start({
      title: "Free up disk space", emoji: "🧹", interactive: true, reveal: true,
      arguments: [...CLEANUP_TOOL, "--yes", ...keys.flatMap((key) => ["--target", key]), ...(searched ? roots.flatMap((root) => ["--root", root]) : [])],
    });
  } catch (error) {
    toast(error.message);
    return;
  }
  const run = {
    phase: "cleaning", id: task.id, keys, freeBefore, freeAfter: null, freed: 0, exitCode: null, finishedAt: 0,
    items: items.map((target) => ({ key: target.key, title: target.title, before: isMeasured(target) && target.sized ? target.bytes : null, after: null })),
  };
  onPhase(run);
  const outcome = await task.done;
  Object.assign(run, { phase: "checking", exitCode: outcome.exit_code, finishedAt: outcome.finished_at ?? Date.now() / 1000 });
  onPhase(run);
  scanner.remeasure(keys);
  const [, freeAfter] = await Promise.all([scanner.whenMeasured(keys), freeNow()]);
  for (const item of run.items) {
    const target = scanner.targets.get(item.key);
    item.after = target?.phase !== "done" ? null : target.status === "empty" ? 0 : target.status === "ready" && target.sized ? target.bytes : null;
  }
  const freed = run.items.reduce((sum, item) => sum + (item.before !== null && item.after !== null ? Math.max(item.before - item.after, 0) : 0), 0);
  Object.assign(run, { phase: "done", freeAfter, freed });
  onPhase(run);
}
