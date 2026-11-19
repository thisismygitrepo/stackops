import { toast } from "./dom.js";

const LAYOUT_KEY = "stackops-serve-layout";
const DIRECTORY_KEY = "stackops-serve-directory";
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

async function request(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 401) {
    toast("This session's access expired because the server restarted. Open the new link it printed.");
    throw new Error("Access expired.");
  }
  // A server error can arrive as plain text; the status message below then stands in for it.
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.error ?? `${method} ${path} failed with status ${response.status}.`);
  return payload;
}

export const api = {
  bootstrap: () => request("GET", "/api/bootstrap"),
  command: (path) => request("GET", `/api/command?path=${encodeURIComponent(path)}`),
  paths: (prefix, base) => request("GET", `/api/paths?prefix=${encodeURIComponent(prefix)}&base=${encodeURIComponent(base)}`),
  capture: (body) => request("POST", "/api/capture", body),
  software: () => request("GET", "/api/software"),
  runs: () => request("GET", "/api/runs"),
  startRun: (body) => request("POST", "/api/runs", body),
  stopRun: (id) => request("POST", `/api/runs/${id}/stop`, {}),
  deleteRun: (id) => request("DELETE", `/api/runs/${id}`),
};
