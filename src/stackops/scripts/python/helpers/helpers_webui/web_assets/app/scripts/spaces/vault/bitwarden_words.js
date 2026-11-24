import { tildify } from "/assets/scripts/dom.js";
import { state as app } from "/assets/scripts/state.js";
import { relativeTime } from "../../words.js";

export const BITWARDEN_HASH = "#/vault/bitwarden";
export const UNLOCK_PATH = "devops vault bitwarden login-and-unlock";
export const FIND_PATH = "devops vault bitwarden search";
export const SYNC_PATH = "devops vault bitwarden sync";
export const CLEAN_PATH = "devops vault bitwarden clean-cache";
export const BITWARDEN_PATHS = [UNLOCK_PATH, FIND_PATH, SYNC_PATH, CLEAN_PATH, "devops vault bitwarden export-session"];
export const APPS_ADDRESS = "#/apps/bw";
// The values Unlock reads from the vault, under a login called `bitwarden`.
export const KEY_NAMES = ["BW_CLIENTID", "BW_CLIENTSECRET", "BW_PASSWORD"];
// A copy this old is said to be out of step.
const STALE_DAYS = 7;
const DAY_MILLISECONDS = 86400000;

export const syncedLong = (state) => Boolean(state.last_sync) && Date.now() - Date.parse(state.last_sync) > STALE_DAYS * DAY_MILLISECONDS;

// The way from nothing to a vault that is open and in step, as four steps, each with how this machine stands on it. `state` is null while
// Bitwarden is still being asked: the steps that depend on it then show as being worked out.
export function stepsOf(place, state) {
  const pending = { tone: "busy", detail: "Asking Bitwarden" };
  const blocked = { tone: "idle", detail: "" };
  const installed = place.installed ? { tone: "good", title: "Installed", detail: tildify(place.program, app.boot.home) } : { tone: "bad", title: "Not installed", detail: "The command-line program bw is not on this machine" };
  if (!place.installed) return [installed, { ...blocked, title: "Signed in" }, { ...blocked, title: "Unlocked" }, { ...blocked, title: "In step" }];
  if (!state) return [installed, { ...pending, title: "Signed in" }, { ...pending, title: "Unlocked" }, { ...pending, title: "In step" }];
  const signedIn = state.status === "locked" || state.status === "unlocked";
  const unlocked = state.status === "unlocked";
  return [
    installed,
    state.status === "unknown" ? { tone: "warn", title: "No answer", detail: "Bitwarden did not say how it stands" } : signedIn ? { tone: "good", title: "Signed in", detail: state.account || "Account not named" } : { tone: "idle", title: "Signed out", detail: "No account is signed in" },
    unlocked ? { tone: "good", title: "Unlocked", detail: "The saved session opens it" } : { tone: "idle", title: signedIn ? "Locked" : "Unlocked", detail: !signedIn ? "" : state.session_saved ? "The saved session no longer opens it" : "No session is saved here" },
    !signedIn ? { ...blocked, title: "In step" } : !state.last_sync ? { tone: "idle", title: "Never synced", detail: "" } : { tone: syncedLong(state) ? "warn" : "good", title: `Synced ${relativeTime(state.last_sync)}`, detail: new Date(state.last_sync).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) },
  ];
}

// The page's first line: how Bitwarden stands, in a sentence, with a tone.
export function headlineOf(place, state) {
  if (!place.installed) return { tone: "idle", title: "Bitwarden's command-line program is not installed", body: "StackOps reaches your Bitwarden vault through the program bw. Install it, and this page signs in and looks logins up for you." };
  if (!state) return { tone: "busy", title: "Asking Bitwarden how it stands", body: "This runs bw once, which takes a second or two." };
  if (state.status === "unknown") return { tone: "warn", title: "Bitwarden did not answer", body: "The program is installed, but it did not say whether it is signed in. Check again in a moment." };
  if (state.status === "unauthenticated") return { tone: "idle", title: "Bitwarden is signed out", body: "Unlock signs in with the API key kept in your vault and opens the vault in one step." };
  if (state.status === "locked") return { tone: "warn", title: "Bitwarden is locked", body: `Signed in${state.account ? ` as ${state.account}` : ""}. Unlock it to search, sync or copy a login.` };
  return syncedLong(state)
    ? { tone: "warn", title: "Bitwarden is unlocked, and out of step", body: `Last synced ${relativeTime(state.last_sync)}. Sync to bring this machine's copy up to date.` }
    : { tone: "good", title: "Bitwarden is unlocked", body: `Signed in${state.account ? ` as ${state.account}` : ""}${state.last_sync ? `, last synced ${relativeTime(state.last_sync)}` : ", never synced"}.` };
}

// What a Bitwarden command said when it failed, in this page's words. The command prints what `bw` answered, and the known answers are put plainly.
const FAILURES = [
  [/client_id or client_secret is incorrect/i, "Bitwarden refused the API key kept in your vault. Check the client ID and client secret of the login called bitwarden."],
  [/invalid master password/i, "Bitwarden refused the master password kept in your vault as BW_PASSWORD."],
  [/multiple bitwarden secret bundles matched/i, "Your vault holds more than one Bitwarden API key. Choose the account to unlock."],
  [/credentials not found in stackops secrets/i, "Your vault has no login called bitwarden that holds an API key."],
  [/missing required keys/i, "The Bitwarden API key in your vault is missing one of its three values."],
  [/must be a user api key/i, "The client ID in your vault is not a personal API key. A personal one starts with user."],
  [/could not save vault cache/i, "The session could not be kept, because this machine's GPG key could not encrypt it."],
  [/not logged in/i, "Bitwarden is signed out. Unlock it first."],
  [/vault is locked/i, "Bitwarden is locked. Unlock it first."],
  [/command not found/i, "Bitwarden's command-line program is not installed on this machine."],
  [/fetch failed|ENOTFOUND|ECONNREFUSED|network/i, "Bitwarden's server could not be reached. Check the network and try again."],
];
export function failureOf(said) {
  const whole = said.join(" ");
  const known = FAILURES.find(([pattern]) => pattern.test(whole));
  return known ? known[1] : (said.at(-1) ?? "The command stopped without saying why.").replace(/^(stderr|stdout):\s*/i, "");
}

export const KINDS = { login: "Logins", note: "Notes", card: "Cards", identity: "Identities", other: "Other" };
export const hostOf = (address) => {
  try {
    return new URL(address).host || address;
  } catch {
    return address;
  }
};
