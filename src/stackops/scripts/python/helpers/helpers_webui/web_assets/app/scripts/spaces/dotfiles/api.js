import { request, state } from "/assets/scripts/state.js";

const base = () => state.settings.workingDirectory;

// What an export made now would hold, where it would go and which ways of handing it over this machine has.
export const readExportPlan = () => request("GET", "/api/dotfiles/export/plan");
// Whether the typed place for the archive is free, read from the working folder as the path suggestions are.
export const checkExportPlace = (path) => request("GET", `/api/dotfiles/export/place?${new URLSearchParams({ path, base: base() })}`);
export const readImportState = () => request("GET", "/api/dotfiles/import/state");
// Opens the archive without unpacking it and says what bringing it in would change. The password travels in the request's body.
export const lookInside = (source, password) => request("POST", "/api/dotfiles/import/inspect", { source, password, base: base() });
// `question` holds the register command's values by the names the route reads; `note` is left out to keep the note an entry already has.
export const checkRegister = (question) => request("GET", `/api/dotfiles/register/check?${new URLSearchParams({ ...question, base: base() })}`);

// Saves a file dropped onto the page in the home folder of the machine the page shows, and says where it is.
export async function receiveArchive(file) {
  const response = await fetch("/api/dotfiles/import/receive", { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file }).catch(() => {
    throw new Error("The StackOps server is not answering. Check that it is still running.");
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.error ?? "The archive could not be saved on this machine.");
  return payload;
}
