import { api, emit, state } from "/assets/scripts/state.js";

const cache = new Map();
const details = new Map();
let catalog = null;

const ANSI_PATTERN = /\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07/g;

function lastLine(text) {
  const lines = text.replace(ANSI_PATTERN, "").split("\n").map((line) => line.replace(/[│╭╮╰╯─]/g, "").trim()).filter(Boolean);
  return lines.at(-1) ?? "";
}

async function capture(runArguments) {
  const result = await api.capture({ arguments: runArguments, working_directory: state.settings.workingDirectory });
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
  if (json === undefined && result.exit_code !== 0) throw new Error(lastLine(result.stderr) || lastLine(result.stdout) || `It stopped with code ${result.exit_code}.`);
  return { json, text: text.replace(/\s+$/, ""), notes: result.stderr.replace(ANSI_PATTERN, "").trim(), exitCode: result.exit_code };
}

export function query(runArguments, fresh = false) {
  const key = `${state.settings.workingDirectory}\n${runArguments.join("\u0000")}`;
  if (fresh || !cache.has(key)) {
    const pending = capture(runArguments);
    cache.set(key, pending);
    pending.catch(() => cache.get(key) === pending && cache.delete(key));
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

export function markStale() {
  cache.clear();
  catalog = null;
  emit("data-stale");
}
