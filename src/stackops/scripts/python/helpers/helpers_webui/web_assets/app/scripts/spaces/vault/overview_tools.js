import { h } from "/assets/scripts/dom.js";
import { request, state } from "/assets/scripts/state.js";
import { toolCard } from "../../space_kit.js";
import { sectionHead } from "../../widgets.js";
import { formatBytes, plural } from "../../words.js";
import { kindOf, rotationNote, valueCount } from "./words.js";

const FILE_TOOLS = ["devops vault validate", "devops vault stats", "devops vault subset", "devops vault init"];
const BITWARDEN_TOOLS = ["devops vault bitwarden login-and-unlock", "devops vault bitwarden search", "devops vault bitwarden sync", "devops vault bitwarden clean-cache"];
const NOT_INSTALLED = { text: "Not installed here", tone: "", off: true };
// What each card says its tool does, in the words of its view. The shared catalogue still words these the way the commands' help does.
const BLURBS = {
  "devops vault validate": "Shows whether each vault file is usable, and what is wrong if not.",
  "devops vault stats": "Counts of logins, secrets and values, and what is due.",
  "devops vault subset": "Tick the logins to copy and write them to another vault file.",
  "devops vault init": "Start a vault file for yourself or for this project.",
  "devops vault bitwarden login-and-unlock": "Sign in with the API key in your vault and open Bitwarden.",
  "devops vault bitwarden search": "Search your Bitwarden logins and copy a password or code.",
  "devops vault bitwarden sync": "Bring this machine's copy of your Bitwarden vault up to date.",
  "devops vault bitwarden clean-cache": "Remove the session and search results saved on this machine.",
};

// What each vault file card says about the files, from what the list of logins already read. Nothing more is asked of the server for it.
function fileStates(sources) {
  const there = sources.filter((source) => source.exists);
  const broken = there.filter((source) => source.problem);
  const logins = sources.flatMap((source) => source.logins);
  const due = logins.reduce((total, login) => total + login.secrets.filter((secret) => rotationNote(secret.rotation)?.tone === "warn").length, 0);
  const missing = sources.filter((source) => !source.exists);
  return {
    "devops vault validate":
      broken.length > 0 ? { text: broken.length === 1 ? "A file cannot be read" : `${broken.length} files cannot be read`, tone: "bad" }
      : there.length === 0 ? { text: "No vault file yet", tone: "" }
      : due > 0 ? { text: `Reads fine · ${plural(due, "secret")} due for replacement`, tone: "warn" }
      : { text: "Reads fine", tone: "good" },
    "devops vault stats": logins.length > 0 ? { text: `${plural(logins.length, "login")} · ${plural(logins.reduce((total, login) => total + valueCount(login), 0), "value")}`, tone: "" } : { text: "Nothing to count yet", tone: "", off: true },
    "devops vault subset": logins.length > 0 ? { text: `${plural(logins.length, "login")} to choose from`, tone: "" } : { text: "Nothing to copy yet", tone: "", off: true },
    "devops vault init":
      missing.length === 0 ? { text: there.length === 1 ? "Your file exists" : "Every file exists", tone: "", off: true }
      : { text: missing.some((source) => kindOf(source.name) === "user") ? "Yours is not created yet" : "This project has none yet", tone: "" },
  };
}

// What each Bitwarden card can say without running Bitwarden or opening its cache: whether the program is installed, and what is saved here.
function bitwardenStates(place) {
  if (!place) return {};
  const cache = place.cache_exists ? { text: `${formatBytes(place.cache_bytes)} saved on this machine`, tone: "" } : { text: "Nothing saved", tone: "", off: true };
  if (!place.installed) return { ...Object.fromEntries(BITWARDEN_TOOLS.map((path) => [path, NOT_INSTALLED])), "devops vault bitwarden clean-cache": cache };
  return { "devops vault bitwarden login-and-unlock": { text: "Installed", tone: "" }, "devops vault bitwarden clean-cache": cache };
}

// The tool cards under the list of logins. Each opens its tool's view, and says in a line how things stand where that is cheap to know: a card
// whose tool has nothing to do here is dimmed, with the reason, and still opens.
export function createToolSections({ tools }) {
  const cards = new Map();
  const grid = (paths) =>
    h("div", { class: "tool-grid" }, paths.filter((path) => state.nodes.has(path)).map((path) => {
      const card = toolCard(tools, state.nodes.get(path));
      const line = h("em", { class: "vault-tools-card-state", hidden: true });
      card.title = BLURBS[path];
      card.querySelector(".tool-card-text span").textContent = BLURBS[path];
      card.querySelector(".tool-card-text").append(line);
      cards.set(path, { card, line });
      return card;
    }));
  const elements = [
    h("section", { class: "block" }, sectionHead("The vault file"), grid(FILE_TOOLS)),
    h("section", { class: "block" }, sectionHead("Bitwarden"), grid(BITWARDEN_TOOLS)),
  ];

  function paint(states) {
    for (const [path, found] of Object.entries(states)) {
      const held = cards.get(path);
      if (!held) continue;
      held.line.hidden = false;
      held.line.textContent = found.text;
      held.line.className = `vault-tools-card-state ${found.tone}`;
      held.card.classList.toggle("vault-tools-card-off", Boolean(found.off));
    }
  }

  return {
    elements,
    paintFiles: (sources) => paint(fileStates(sources)),
    // A server without this route, one started before the page files changed, leaves the Bitwarden cards as plain cards.
    readBitwarden: () => request("GET", "/api/vault/bitwarden/place").then((place) => paint(bitwardenStates(place)), () => {}),
  };
}
