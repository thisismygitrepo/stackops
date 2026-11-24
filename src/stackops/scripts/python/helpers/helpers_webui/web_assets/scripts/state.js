const LAYOUT_KEY = "stackops-webui-layout";
const DIRECTORY_KEY = "stackops-webui-directory";
const listeners = new Map();

export const state = { boot: null, nodes: new Map(), parents: new Map(), settings: { workingDirectory: "", dockHeight: 320, expanded: [] } };

export function initState(boot) {
  state.boot = boot;
  const visit = (node, parent) => {
    state.nodes.set(node.path, node);
    state.parents.set(node.path, parent);
    node.leaves = node.children.length ? node.children.reduce((total, child) => total + visit(child, node), 0) : 1;
    return node.leaves;
  };
  visit(boot.tree, null);
  Object.assign(state.settings, JSON.parse(localStorage.getItem(LAYOUT_KEY) ?? "{}"));
  state.settings.workingDirectory = sessionStorage.getItem(DIRECTORY_KEY) ?? boot.working_directory;
}

export function setSetting(key, value) {
  state.settings[key] = value;
  if (key === "workingDirectory") sessionStorage.setItem(DIRECTORY_KEY, value);
  else localStorage.setItem(LAYOUT_KEY, JSON.stringify({ dockHeight: state.settings.dockHeight, expanded: state.settings.expanded }));
  emit(key, value);
}

export function on(event, callback) {
  listeners.set(event, [...(listeners.get(event) ?? []), callback]);
}

export function emit(event, payload) {
  for (const callback of listeners.get(event) ?? []) callback(payload);
}

export function nodeHash(node) {
  return node.path === "" ? "#/c" : `#/c/${node.path.split(" ").map(encodeURIComponent).join("/")}`;
}

export function lineage(node) {
  const chain = [];
  for (let current = node; current && current.kind !== "root"; current = state.parents.get(current.path)) chain.unshift(current);
  return chain;
}

export function parseRoute() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] === "c") return { view: "browse", path: parts.slice(1).join(" ") };
  if (parts[0] === "d") return { view: "dashboards", id: parts[1] ?? null };
  if (parts[0] === "map") return { view: "map" };
  return { view: "home" };
}

// On a page that shows another machine (other_machines.js), a server that does not answer and a sign-in that no longer holds mean one thing: the connection that showed it is gone.
const connectionGone = () => state.boot?.opened_from && `The connection to ${state.boot.opened_from.machine} is gone. Go back to ${state.boot.opened_from.name} and open ${state.boot.opened_from.machine} again.`;

// Every failure is thrown with a sentence fit to show as it is, and nothing is shown from here: the caller decides where it appears, once.
// An answer that is not OK also carries `status`, its HTTP status number. A call cancelled through `signal` rejects with the browser's AbortError.
// Exported for a view that keeps its server calls with itself (app/scripts/features.js); the calls every page shares are in `api` below.
export async function request(method, path, body, signal) {
  const response = await fetch(path, {
    method,
    signal,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).catch((error) => {
    if (signal?.aborted) throw error;
    throw new Error(connectionGone() || "The StackOps server is not answering. Check that it is still running.");
  });
  // A server error can arrive as plain text; the status message below then stands in for it.
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  signal?.throwIfAborted();
  if (response.ok) return payload;
  const message = response.status === 401 ? connectionGone() || "This session's access expired because the server restarted. Open the new link it printed." : (payload?.error ?? `${method} ${path} failed with status ${response.status}.`);
  throw Object.assign(new Error(message), { status: response.status });
}

export const api = {
  bootstrap: () => request("GET", "/api/bootstrap"),
  command: (path) => request("GET", `/api/command?path=${encodeURIComponent(path)}`),
  choices: (path) => request("GET", `/api/choices?path=${encodeURIComponent(path)}`),
  paths: (prefix, base) => request("GET", `/api/paths?prefix=${encodeURIComponent(prefix)}&base=${encodeURIComponent(base)}`),
  directory: (path, base) => request("GET", `/api/directory?path=${encodeURIComponent(path)}&base=${encodeURIComponent(base)}`),
  capture: (body, signal) => request("POST", "/api/capture", body, signal),
  software: () => request("GET", "/api/software"),
  softwareVersion: (name, fresh) => request("GET", `/api/software/version?name=${encodeURIComponent(name)}${fresh ? "&fresh=1" : ""}`),
  file: (path) => request("GET", `/api/file?path=${encodeURIComponent(path)}`),
  saveFile: (body) => request("PUT", "/api/file", body),
  vault: (base, reveal) => request("GET", `/api/vault?${new URLSearchParams({ base, reveal })}`),
  vaultLogin: (base, { source, index, version }) => request("GET", `/api/vault/login?${new URLSearchParams({ base, source, index, version })}`),
  saveVaultLogin: (body) => request("PUT", "/api/vault/login", body),
  deleteVaultLogin: (base, { source, index, version }) => request("DELETE", `/api/vault/login?${new URLSearchParams({ base, source, index, version })}`),
  scripts: (base) => request("GET", `/api/scripts?${new URLSearchParams({ base })}`),
  onlineScripts: () => request("GET", "/api/scripts/online"),
  scriptText: (base, { source, name }) => request("GET", `/api/scripts/text?${new URLSearchParams({ base, source, name })}`),
  createScript: (body) => request("POST", "/api/scripts", body),
  runs: () => request("GET", "/api/runs"),
  startRun: (body) => request("POST", "/api/runs", body),
  stopRun: (id) => request("POST", `/api/runs/${id}/stop`, {}),
  deleteRun: (id) => request("DELETE", `/api/runs/${id}`),
};
