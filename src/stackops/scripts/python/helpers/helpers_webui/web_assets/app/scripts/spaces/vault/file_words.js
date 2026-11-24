import { plural } from "../../words.js";
import { kindOf } from "./words.js";

export const FILE_HASH = "#/vault/file";
export const VALIDATE_PATH = "devops vault validate";
export const STATS_PATH = "devops vault stats";
export const INIT_PATH = "devops vault init";
export const ROTATE_PATH = "devops vault rotate";
export const FILE_PATHS = [VALIDATE_PATH, STATS_PATH, INIT_PATH];

// A vault file by whose it is, as a title and as the start of a sentence.
export function fileTitle(name) {
  const member = name.split(":")[1];
  return member ? `Vault file of ${member}` : kindOf(name) === "user" ? "Your vault file" : "This project's vault file";
}
export const FILE_BLURBS = { user: "On hand in every project.", workspace: "Kept with this project, for everyone who works in it." };

const dueOf = (file) => (file.holds?.rotation ?? []).filter((row) => row.state === "due").length;

// What is worth acting on in a file that reads fine. Each is a line of its checklist; none of them stops the vault from working.
export function concernsOf(file) {
  if (!file.holds) return [];
  return [
    !file.private && "open",
    file.holds.unloadable_names > 0 && "unloadable",
    dueOf(file) > 0 && "due",
  ].filter(Boolean);
}

// How one file stands, from the quick reading and, once it is in, the full check.
export function standingOf(file, check) {
  if (!file.exists) return { id: "missing", tone: "idle", label: "Not created yet" };
  if (file.finding) return { id: "broken", tone: "bad", label: "Cannot be read" };
  if (check?.verdict === "invalid") return { id: "broken", tone: "bad", label: "Fails the full check" };
  const concerns = concernsOf(file).length;
  if (concerns > 0) return { id: "attention", tone: "warn", label: `${plural(concerns, "thing")} to look at` };
  return check ? { id: "good", tone: "good", label: "In good shape" } : { id: "checking", tone: "good", label: "Reads fine" };
}

// The page's first line: the worst standing among the files that exist, in a sentence.
export function summaryOf(files, checks) {
  const there = files.filter((file) => file.exists);
  const broken = there.filter((file) => standingOf(file, checks.get(file.name)).id === "broken");
  if (broken.length > 0) {
    return {
      tone: "bad", title: broken.length === 1 ? `${fileTitle(broken[0].name)} cannot be used` : `${broken.length} vault files cannot be used`,
      body: "Nothing in a file that fails its check can be loaded or changed until it is repaired. What is wrong, and where, is under the file.",
    };
  }
  if (there.length === 0) return { tone: "idle", title: "There is no vault file yet", body: "Create one below. Adding a login on the Vault page creates it too." };
  const holds = there.map((file) => file.holds);
  const count = (key) => holds.reduce((total, held) => total + held[key], 0);
  const held = `${plural(count("logins"), "login")}, ${plural(count("secrets"), "secret")} and ${plural(count("values"), "value")}`;
  const concerns = there.reduce((total, file) => total + concernsOf(file).length, 0);
  if (concerns > 0) return { tone: "warn", title: `The vault works, with ${plural(concerns, "thing")} to look at`, body: `It holds ${held}. Each thing to look at is marked under its file.` };
  return { tone: "good", title: there.length === 1 ? "The vault file is in good shape" : `All ${there.length} vault files are in good shape`, body: `${held}, counted without reading a value into this page.` };
}

// The optional notes a login or secret can carry, as the server counts them: [count's name, what it is a share of, what to call it].
export const DESCRIBED = [
  ["login_description", "logins", "Logins that say what they are for"],
  ["login_account", "logins", "Logins that name their account"],
  ["login_username", "logins", "Logins with a user name"],
  ["login_email", "logins", "Logins with an email"],
  ["login_url", "logins", "Logins with a web address"],
  ["secret_description", "secrets", "Secrets that say what they are for"],
  ["secret_rotation", "secrets", "Secrets that record when they were replaced"],
  ["secret_tags", "secrets", "Secrets with a tag"],
  ["secret_scopes", "secrets", "Secrets with a scope"],
];
export const LABEL_KINDS = [["login_tags", "Login tags"], ["secret_tags", "Secret tags"], ["scopes", "Scopes"]];

// Where a secret stands against its own replacement interval: a tone, a few words, and how much of the interval is used up (0 to 1).
export function rotationWords(row) {
  const left = row.every - row.age;
  const every = `every ${plural(row.every, "day")}`;
  if (row.state === "due") return { tone: "bad", text: `${plural(-left, "day")} overdue`, detail: `Replaced ${row.last}, ${every}`, share: 1 };
  if (row.state === "soon" || row.state === "fine") {
    return { tone: row.state === "soon" ? "warn" : "good", text: left === 0 ? "Due today" : `Due in ${plural(left, "day")}`, detail: `Replaced ${row.last}, ${every}`, share: row.age / row.every };
  }
  if (row.state === "unscheduled") return { tone: "", text: "No interval set", detail: `Replaced ${row.last}`, share: 0 };
  return { tone: "", text: "No date recorded", detail: row.every ? `Meant to be replaced ${every}` : "Its rotation record is empty", share: 0 };
}
const RANKS = { due: 0, soon: 1, fine: 2, unscheduled: 3, undated: 4 };
// Most pressing first: overdue by how long, then by how soon the next one is due.
export const byUrgency = (left, right) => RANKS[left.state] - RANKS[right.state] || (left.every - left.age) - (right.every - right.age) || left.login.localeCompare(right.login);
