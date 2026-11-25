import { toast } from "/assets/scripts/dom.js";
import { on, request, state } from "/assets/scripts/state.js";
import { markStale } from "../../data.js";
import { API, idOf } from "./words.js";

const onScreen = (element) => element.isConnected && !element.closest("[hidden]");

// Why a reading did not arrive, in words fit to show. A server started before this page existed has no answer for it, and says so with a 404
// that only a restart clears up.
export const reasonOf = (error) => (error.status === 404 ? "The StackOps server that is running is older than this page. Restart it, then open this page again." : error.message);

// Something the overview and a view of its own both show, read once for both. What was read stops being current when any run ends and when the
// working folder changes: it is then read again at once if a view that shows it is on screen, and on the next visit otherwise.
// `read(progress, { fresh, previous })` resolves to the value and may hand over a part of it early through `progress`, for a reading that
// arrives in steps. `previous` is the value it replaces, and `fresh` says the person asked for it (`reload`), so nothing may be carried over.
// A view registers with `watch(element, paint)` and calls `sync()` each time it is shown; `paint` gets `{ value, failure, loading }`.
function createReading(read) {
  const watchers = [];
  const reading = { value: null, failure: null, loading: false };
  let wanted = 0;
  let held = -1;
  let ticket = 0;
  let asked = false;
  const tell = () => {
    for (const watcher of watchers) watcher.paint(reading);
  };

  async function sync() {
    if (held === wanted) return;
    held = wanted;
    const mine = (ticket += 1);
    const given = { fresh: asked, previous: reading.value };
    asked = false;
    reading.loading = true;
    tell();
    try {
      const value = await read((part) => {
        if (mine !== ticket) return;
        reading.value = part;
        reading.failure = null;
        tell();
      }, given);
      if (mine !== ticket) return;
      reading.value = value;
      reading.failure = null;
    } catch (error) {
      if (mine !== ticket) return;
      reading.failure = error;
      // A reading that did not arrive is asked for again on the next visit. What an earlier one put on the page stays there, so it is said
      // once, here, that it is no longer current; a view with nothing to show says why in its own place.
      held = -1;
      if (reading.value) toast(`This could not be read again, so what is shown may be out of date. ${reasonOf(error)}`);
    }
    reading.loading = false;
    tell();
  }

  function expire() {
    wanted += 1;
    if (watchers.some((watcher) => onScreen(watcher.element))) sync();
  }
  on("data-stale", expire);
  on("workingDirectory", expire);

  return {
    reading, sync, tell,
    reload() {
      wanted += 1;
      asked = true;
      return sync();
    },
    // A view that starts watching after the reading arrived is shown it at once: `sync` has nothing new to tell it.
    // Returns the way to stop watching, for a view that goes away, such as a sheet.
    watch(element, paint) {
      const watcher = { element, paint };
      watchers.push(watcher);
      if (reading.value || reading.failure) paint(reading);
      return () => watchers.splice(watchers.indexOf(watcher), 1);
    },
  };
}

const base = () => new URLSearchParams({ base: state.settings.workingDirectory });
const askCheck = ({ kind, scope }) => request("GET", `${API}/files/check?${new URLSearchParams({ kind, scope, base: state.settings.workingDirectory })}`).catch((error) => ({ kind, ok: null, problem: error.message }));

// Every settings file, then whether each one that is there passes its check. The list is on the page at once; the checks take half a second
// each, run side by side, and each is shown as it comes in. Each file gets the `id` the page knows it by, and `checks` holds the answers by it.
// A design choice: when the page reads itself again after a run, a file that has not changed since it was checked (same place, size and time
// of change) keeps its answer and is not checked again, so the cards do not all blink through "Checking". An answer can depend on more than
// the file (the installer list names scripts beside it), which this misses; "Check again" and a card's Check button always check anew.
export const files = createReading(async (progress, { fresh, previous }) => {
  const listing = await request("GET", `${API}/files?${base()}`);
  for (const file of listing.files) file.id = idOf(file);
  const before = new Map((previous?.files ?? []).map((file) => [file.id, file]));
  const kept = (file) => !fresh && ["path", "size", "modified_at"].every((key) => before.get(file.id)?.[key] === file[key]) && previous.checks.get(file.id)?.ok != null;
  const checks = new Map(listing.files.filter((file) => file.exists && kept(file)).map((file) => [file.id, previous.checks.get(file.id)]));
  const shown = () => ({ ...listing, checks: new Map(checks) });
  progress(shown());
  await Promise.all(
    listing.files.filter((file) => file.exists && !checks.has(file.id)).map(async (file) => {
      checks.set(file.id, await askCheck(file));
      progress(shown());
    }),
  );
  return shown();
});

// One file checked again, with the answer put into the shared reading.
export async function recheck(file) {
  const { value } = files.reading;
  value.checks.delete(file.id);
  files.tell();
  const check = await askCheck(file);
  if (files.reading.value !== value) return check;
  value.checks.set(file.id, check);
  files.tell();
  return check;
}

export const createFile = ({ kind, scope }) => request("POST", `${API}/files/create`, { kind, scope, base: state.settings.workingDirectory });
export const readExample = (kind) => request("GET", `${API}/files/example?${new URLSearchParams({ kind })}`);
export const setup = createReading(() => request("GET", `${API}/setup`));
export const assets = createReading(() => request("GET", `${API}/assets`));

// A command run out of sight: it only opens the activity panel when it goes wrong. Resolves to whether it went well.
// A run that is not shown ends without the refresh signal a shown one sends, so it is sent here: these runs change settings other pages read.
export async function quietRun(activity, { title, emoji, runArguments }) {
  const run = await activity.start({ title, emoji, arguments: runArguments, interactive: false, reveal: false });
  const outcome = await run.done;
  markStale();
  if (outcome.exit_code !== 0) {
    activity.reveal(run.id);
    return false;
  }
  activity.remove(run.id);
  return true;
}
