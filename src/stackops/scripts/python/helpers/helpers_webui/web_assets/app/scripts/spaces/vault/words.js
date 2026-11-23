import { toast } from "/assets/scripts/dom.js";
import { copyText } from "../../widgets.js";
import { plural, relativeTime } from "../../words.js";

export const EVERYWHERE = "all";
// How much of each secret value the page asks the server for. The hiding is done there, so a hidden value is not in the page at all.
export const REVEALS = [["hidden", "Hidden"], ["partial", "Partly"], ["full", "Shown"]];
export const MASK = "••••••••";
// The files a login can live in, as the server names them: the user's own, the project's, and one per member of a workspace (`workspace:<name>`).
const PLACES = { user: "Yours", workspace: "This project" };
export const PLACE_BLURBS = { user: "On hand in every project.", workspace: "Kept with this project, for everyone who works in it." };
const DAY_MILLISECONDS = 86400000;

export const kindOf = (source) => source.split(":")[0];
export function placeLabel(source) {
  const [kind, member] = source.split(":");
  return member ? `${PLACES[kind]} · ${member}` : PLACES[kind];
}

export const keyOf = (login) => `${login.source}\n${login.index}`;
export const valueCount = (login) => login.secrets.reduce((total, secret) => total + secret.values.length, 0);
// A value written out the way the server does it: text as it is, anything else as compact JSON.
export const valueText = (value) => (typeof value === "string" ? value : JSON.stringify(value));
export const listOf = (text) => [...new Set(text.split(",").map((part) => part.trim()).filter(Boolean))];

// Everything a search looks through: names and labels, never a value.
export function haystackOf(login, source) {
  const secrets = login.secrets.flatMap((secret) => [secret.name, secret.description, ...secret.tags, ...secret.scopes, ...secret.values.map((row) => row.key), ...Object.entries(secret.metadata ?? {}).flat()]);
  const own = [login.name, login.accountName, login.username, login.email, login.url, login.description, ...(login.tags ?? []), ...Object.entries(login.metadata ?? {}).flat()];
  return [...own, ...secrets, placeLabel(source)].filter(Boolean).join(" ").toLowerCase();
}

export function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

// What a secret's rotation record says in a few words, in the warning tone once it is overdue. Null for a secret that keeps no record.
export function rotationNote(rotation = {}) {
  const { lastRotated, rotateEveryDays } = rotation;
  if (!lastRotated && !rotateEveryDays) return null;
  const every = rotateEveryDays ? `every ${plural(rotateEveryDays, "day")}` : "";
  if (!lastRotated) return { text: `Rotate ${every} · no date recorded`, tone: "" };
  const age = Math.floor((Date.parse(today()) - Date.parse(lastRotated)) / DAY_MILLISECONDS);
  if (Number.isNaN(age)) return { text: `Rotated ${lastRotated}`, tone: "" };
  const when = age <= 0 ? "today" : age === 1 ? "yesterday" : relativeTime(lastRotated);
  if (rotateEveryDays && age > rotateEveryDays) return { text: `Rotation due · last ${when}`, tone: "warn" };
  return { text: [`Rotated ${when}`, every].filter(Boolean).join(" · "), tone: "" };
}

// A click handler that fetches something: a refusal is said once, as a message, and is nobody else's to catch.
export const telling = (action) => () => action().catch((error) => toast(error.message));

// Copies text that still has to be fetched; `read` returns a promise of it. Safari only allows a copy that starts in the click itself, so where
// the browser can take a pending answer the clipboard is handed that, instead of being called once the answer is in.
export async function copyPending(read) {
  // Without a clipboard nothing is fetched: `copyText` only says why copying is not possible here.
  if (!navigator.clipboard || !window.ClipboardItem) return copyText(navigator.clipboard ? await read() : "");
  await navigator.clipboard.write([new ClipboardItem({ "text/plain": read().then((text) => new Blob([text], { type: "text/plain" })) })]);
  return true;
}
