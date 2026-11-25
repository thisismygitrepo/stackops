import { capture } from "../../data.js";

// Everything this page knows comes from the OneDrive commands themselves, asked for JSON. They answer in about a tenth of a second plus the
// time Microsoft takes, so the page needs nothing of its own on the server.
const GROUP = ["cloud", "onedrive"];
const NO_SECRETS_FILE = /secrets file not found/i;
let line = Promise.resolve();

// One command at a time. Each one signs in afresh with the account's saved token and writes the renewed token back to the secrets file, so
// two at once would be two writers of that file.
function inTurn(work) {
  const mine = line.then(work);
  line = mine.then(() => {}, () => {});
  return mine;
}

// A command's failure reads "Error: …". The word is dropped: where the page shows a failure it already says that something went wrong.
function ask(runArguments, signal) {
  return inTurn(async () => {
    signal?.throwIfAborted();
    try {
      return await capture([...GROUP, ...runArguments], signal);
    } catch (error) {
      if (error.name !== "AbortError") error.message = error.message.replace(/^error:\s*/i, "");
      throw error;
    }
  });
}

function listOf(result, what) {
  if (!Array.isArray(result.json)) throw new Error(`${what} came back in a form this page cannot read.`);
  return result.json;
}

export async function readAccounts() {
  try {
    return listOf(await ask(["accounts", "--json"]), "The list of accounts").map((entry) => ({ name: entry.account, signedIn: entry.authentication === "authenticated" }));
  } catch (error) {
    // Until the first account is added there is no secrets file, and the command reports that as a failure.
    if (NO_SECRETS_FILE.test(error.message)) return [];
    throw error;
  }
}

export const readSecretsPath = async () => (await ask(["config-path"])).text.trim();

export async function readStatus(account, signal) {
  const { json } = await ask(["status", account, "--json"], signal);
  if (!json || Array.isArray(json)) throw new Error("The drive's status came back in a form this page cannot read.");
  return json;
}

export const listFolder = async (account, folder, signal) => listOf(await ask(["list", folder, "--account", account, "--json"], signal), "The folder's contents");

// Dashes at the start are dropped: the command would read such a word as one of its options, and the drive's search ignores punctuation anyway.
export const searchWords = (text) => text.trim().replace(/^-+/, "").trim();
export const searchDrive = async (account, text, signal) => listOf(await ask(["search", searchWords(text), "--account", account, "--json"], signal), "The search results");

export const removeItem = (account, path) => ask(["delete", path, "--yes", "--account", account]);
export const addAccount = (name, clientId) => ask(["add-account", name, "--client-id", clientId, "--json"]);

// The commands that can take long run as tasks, where they can be watched and stopped. They are started in turn like the rest.
export const startInTurn = (start) => inTurn(start);
export const signInArguments = (account) => [...GROUP, "auth", account, "--json"];
export const uploadArguments = (account, localPath, remotePath, overwrite) => [...GROUP, "upload", localPath, remotePath, ...(overwrite ? ["--overwrite"] : []), "--account", account];
export const downloadArguments = (account, remotePath, localPath) => [...GROUP, "download", remotePath, localPath, "--account", account, "--json"];
