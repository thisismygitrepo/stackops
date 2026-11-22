import { api, emit, on, state } from "/assets/scripts/state.js";

const cache = new Map();
const running = new Set();
const details = new Map();
let catalog = null;

const ANSI_PATTERN = /\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07/g;

// What a failed command said, in one line: from its first "Error" line to the end, so the cause is not dropped for the hint under it and a
// wrapped message stays whole. With no such line it is the last line, which is where a traceback names the exception.
function failureText(text) {
  const lines = text.replace(ANSI_PATTERN, "").split("\n").map((line) => line.replace(/[│╭╮╰╯─]/g, "").trim()).filter(Boolean);
  const start = lines.findIndex((line) => /^error(:|$)/i.test(line));
  return (start < 0 ? lines.slice(-1) : lines.slice(/^error$/i.test(lines[start]) ? start + 1 : start)).join(" ");
}

// One run, never cached: for results that must be current and are not worth keeping, such as a search. Pages use `query`.
// `signal` is an AbortSignal for a caller that may give up on the answer: aborting it drops the request, which makes the server stop the command.
// `query` passes none on purpose: its answer is cached and may be shared with another reader.
export async function capture(runArguments, signal) {
  const result = await api.capture({ arguments: runArguments, working_directory: state.settings.workingDirectory }, signal);
  const text = result.stdout.replace(ANSI_PATTERN, "");
  const trimmed = text.trim();
  let json;
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      json = JSON.parse(trimmed);
    } catch {
      json = undefined;
    }
  }
  if (json === undefined && result.exit_code !== 0) throw new Error(failureText(result.stderr) || failureText(result.stdout) || `It stopped with code ${result.exit_code}.`);
  return { json, text: text.replace(/\s+$/, ""), notes: result.stderr.replace(ANSI_PATTERN, "").trim(), exitCode: result.exit_code };
}

// A design choice: `fresh` asked for while the same command is still running joins that run, so a second press on Refresh, or one during a reload,
// does not run it twice. Not strictly fresh: the joined run began a moment earlier and can miss a change made outside this app in between.
// A change made through the app empties the cache first (`markStale`), so what is asked for after it never joins a run from before it.
export function query(runArguments, fresh = false) {
  const key = `${state.settings.workingDirectory}\n${runArguments.join("\u0000")}`;
  if (!cache.has(key) || (fresh && !running.has(cache.get(key)))) {
    const pending = capture(runArguments);
    cache.set(key, pending);
    running.add(pending);
    pending.catch(() => cache.get(key) === pending && cache.delete(key));
    pending.then(() => running.delete(pending), () => running.delete(pending));
  }
  return cache.get(key);
}

export function software(fresh = false) {
  if (fresh || !catalog) {
    const pending = api.software();
    catalog = pending;
    pending.catch(() => catalog === pending && (catalog = null));
  }
  return catalog;
}

export function commandDetail(path) {
  if (!details.has(path)) {
    const pending = api.command(path);
    details.set(path, pending);
    pending.catch(() => details.delete(path));
  }
  return details.get(path);
}

// A tool's parameters as its form shows them. Where this machine can list the valid values of a parameter the CLI takes as text (the server's
// `field_choices`), the field becomes a choice from that list. The lists are read afresh each time, so a sheet opened after a cloud was added
// offers it. A server that cannot give them leaves every field the way the CLI declares it.
export async function formDetail(path) {
  const [{ parameters }, { fields }] = await Promise.all([commandDetail(path), api.choices(path).catch(() => ({ fields: {} }))]);
  const listed = (spec) => ({ ...spec, control: "choice", listed: true, ...fields[spec.name], default: fields[spec.name].default ?? spec.default });
  return { parameters: parameters && parameters.map((spec) => (fields[spec.name] ? listed(spec) : spec)) };
}

export function markStale() {
  cache.clear();
  catalog = null;
  emit("data-stale");
}

// The bookkeeping of a view that shows fetched data, kept in one place. Its data starts out stale. `load` runs the view's `loader` and lowers the
// flag; a loader whose answer did not arrive calls `spoil`, so the next visit asks again. `ensure` is for each time the view is shown.
// With `signalled`, the refresh signal raises the flag too, and reloads at once when `element` is on screen.
export function staleKeeper(element, loader, signalled = true) {
  let stale = true;
  const load = (...given) => {
    stale = false;
    return loader(...given);
  };
  if (signalled) {
    on("data-stale", () => {
      stale = true;
      if (element.isConnected && !element.closest("[hidden]")) load();
    });
  }
  return { load, ensure: () => stale && load(), spoil: () => (stale = true) };
}
