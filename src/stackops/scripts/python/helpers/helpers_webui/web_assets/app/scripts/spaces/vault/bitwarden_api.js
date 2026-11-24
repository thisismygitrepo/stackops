import { api, request, state } from "/assets/scripts/state.js";

const ANSI_PATTERN = /\x1b\[[0-9;?]*[ -/]*[@-~]/g;

// The Bitwarden page's own calls to the server (vault_bitwarden_routes.py). What is asked for travels in the request's body: an item's ID and
// the kind of value wanted never become part of an address.
export const readPlace = () => request("GET", "/api/vault/bitwarden/place");
export const readState = () => request("GET", "/api/vault/bitwarden/state");
export const readItems = (fresh) => request("POST", "/api/vault/bitwarden/items", { fresh });
export const readValue = (id, field) => request("POST", "/api/vault/bitwarden/value", { id, field }).then((answer) => answer.text);

// Runs one of the Bitwarden commands to its end and says how it went. `said` is what the command printed, as plain lines, for the page to
// put into its own words; the commands print progress and labels, never a value.
export async function runCommand(commandArguments) {
  const result = await api.capture({ arguments: ["devops", "vault", "bitwarden", ...commandArguments], working_directory: state.settings.workingDirectory });
  const lines = `${result.stderr}\n${result.stdout}`.replace(ANSI_PATTERN, "").split("\n").map((line) => line.replace(/[│╭╮╰╯─]/g, "").trim()).filter(Boolean);
  return { ok: result.exit_code === 0, said: lines };
}
