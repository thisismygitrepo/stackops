import { request, state } from "/assets/scripts/state.js";

// The vault file views' own calls to the server (vault_file_routes.py). A file is named by its source, for the folder the page works in.
const base = () => state.settings.workingDirectory;
const query = (fields) => new URLSearchParams({ base: base(), ...fields });

export const readHealth = () => request("GET", `/api/vault/file/health?${query({})}`);
export const runCheck = (source) => request("GET", `/api/vault/file/check?${query({ source })}`);
export const createFile = (source) => request("POST", "/api/vault/file/create", { base: base(), source });
export const refreshSchema = (source) => request("POST", "/api/vault/file/schema", { base: base(), source });
export const protectFile = (source) => request("POST", "/api/vault/file/protect", { base: base(), source });
export const readTarget = (source, path, signal) => request("GET", `/api/vault/file/copy/target?${query({ source, path })}`, undefined, signal);
export const copyLogins = (body) => request("POST", "/api/vault/file/copy", { base: base(), ...body });
