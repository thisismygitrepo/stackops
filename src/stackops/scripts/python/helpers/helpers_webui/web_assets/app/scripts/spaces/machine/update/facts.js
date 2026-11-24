import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { copyChip, keyValue, pathChip, pill } from "../../../widgets.js";
import { plural, relativeTime } from "../../../words.js";
import { dirtyCount, incomingCount, remoteName, shortId } from "./words.js";

const since = (seconds) => h("span", { title: new Date(seconds * 1000).toLocaleString(), text: relativeTime(seconds) });
const lines = (...parts) => h("div", { class: "machine-update-lines" }, ...parts);
const small = (text) => h("small", { class: "dim", text });

const SOURCES = {
  index: () => ["PyPI, the Python package index"],
  checkout: (install) => [lines(h("span", { text: "The source folder" }), pathChip(install.origin), small("Edits to that folder take effect without installing again."))],
  folder: (install) => [lines(h("span", { text: "A copy of the folder" }), pathChip(install.origin))],
  repository: (install) => [lines(h("span", { text: "A git address" }), copyChip(install.origin))],
  archive: (install) => [lines(h("span", { text: "A downloaded file" }), copyChip(install.origin))],
};

function installFacts(state) {
  const install = state.installed;
  const served = state.served_by_installed
    ? `This install, since ${formatClock(state.started_at)}`
    : lines(h("span", { text: state.served_from ? "Another copy" : "Source files with no install record" }), state.served_from && pathChip(state.served_from), small("The update leaves that copy alone. It changes the tool."));
  if (!install) {
    return keyValue([["Installed by", "Nothing on record. StackOps runs here from its source files."], ["Version running", state.started_version], ["This page comes from", served]]);
  }
  return keyValue([
    ["Installed by", install.uv_tool ? "uv, as one of its tools" : lines(h("span", { text: "Something other than uv's tools" }), small("The update installs StackOps as a uv tool. This copy stays as it is."))],
    ["Comes from", SOURCES[install.source](install)],
    ["Lives in", pathChip(install.location)],
    ["Python", install.python],
    ["Last installed", since(install.installed_at)],
    ["This page comes from", served],
  ]);
}

// Three counts that say at a glance how the source folder stands against the place it follows.
function tallies(state, latest) {
  const { checkout } = state;
  const dirty = dirtyCount(checkout);
  const incoming = incomingCount(checkout, latest);
  const tally = (glyph, tone, number, label, hint) => h("div", { class: `machine-update-tally ${number > 0 ? tone : ""}`, title: hint }, icon(glyph, 16), h("strong", { class: "num", text: String(number) }), h("span", { text: label }));
  return h(
    "div",
    { class: "machine-update-tallies" },
    tally("pencil", "warn", dirty, dirty === 1 ? "file not committed" : "files not committed", dirty ? `${plural(checkout.changed, "changed file")} and ${plural(checkout.untracked, "new file")}` : "Nothing is waiting to be committed"),
    tally("up", "accent", checkout.ahead, checkout.ahead === 1 ? "commit not pushed" : "commits not pushed", "Commits of yours that the place this branch follows does not have"),
    tally("down", "accent", incoming, incoming === 1 ? "commit waiting" : "commits waiting", "Commits the update would bring in"),
  );
}

function checkoutFacts(state) {
  const { checkout } = state;
  const head = checkout.head;
  const declared = checkout.version && state.installed && checkout.version !== state.installed.version;
  return keyValue([
    ["Folder", pathChip(checkout.path)],
    ["Branch", checkout.branch ? lines(h("span", { text: checkout.branch }), checkout.upstream ? small(`Follows ${checkout.upstream}`) : pill("Follows nothing", "warn")) : pill("None checked out", "warn")],
    ["Last commit", head && lines(h("span", { text: head.title }), h("small", { class: "dim" }, since(head.committed_at), " · ", h("code", { text: shortId(head.sha) })))],
    ["Pushes to", checkout.origin ? copyChip(checkout.origin, remoteName(checkout.origin)) : pill("No remote called origin", "warn")],
    ["Last fetched", checkout.fetched_at === null ? "Never" : since(checkout.fetched_at)],
    ["Version in the folder", declared && lines(h("span", { text: checkout.version }), small(`The install record still says ${state.installed.version}. The next update brings them in line.`))],
  ]);
}

// Two cards: how StackOps is installed here, and for an install from a source folder, how that folder stands. Everything here is read from this
// machine. The page places them: the folder beside what is new, and the install beside it where there is no folder.
export function createFacts() {
  const installBody = h("div");
  const folderBody = h("div", { class: "machine-update-checkout" });
  const install = h("section", { class: "machine-update-card machine-update-install" }, h("header", { class: "machine-update-card-head" }, h("h2", { text: "How it is installed" })), installBody);
  const folder = h("section", { class: "machine-update-card machine-update-folder" }, h("header", { class: "machine-update-card-head" }, h("h2", { text: "The source folder" })), folderBody);

  function paint({ state, latest }) {
    installBody.replaceChildren(installFacts(state));
    folder.hidden = state.route !== "checkout";
    if (state.route !== "checkout") return;
    if (state.checkout.problem !== "") {
      folderBody.replaceChildren(keyValue([["Folder", pathChip(state.checkout.path)], ["State", pill(state.checkout.problem === "not_repository" ? "No git history" : "Git could not read it", "bad")]]));
      return;
    }
    folderBody.replaceChildren(tallies(state, latest), checkoutFacts(state));
  }

  return { install, folder, paint };
}
