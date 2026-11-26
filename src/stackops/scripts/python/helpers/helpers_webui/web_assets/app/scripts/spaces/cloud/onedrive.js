import { h, icon, toast } from "/assets/scripts/dom.js";
import { on, state } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { button, notice, pill, skeleton } from "../../widgets.js";
import { formatBytes, humanize } from "../../words.js";
import { createAccountsBar, createSignIn, openAddAccount } from "./onedrive_accounts.js";
import { readAccounts, readSecretsPath, readStatus } from "./onedrive_api.js";
import { createFiles } from "./onedrive_files.js";
import { createTransfers, deleteItem, openDownload, openUpload } from "./onedrive_transfers.js";
import { FILES_WORD, PAGE_ADDRESS, addressOf, nameOf, parentOf, safeLink } from "./onedrive_words.js";

const COMMANDS = ["auth", "status", "accounts", "list", "search", "download", "upload", "delete", "config-path", "add-account"];
const NEARLY_FULL = 0.9;

// This page's stylesheet comes with the page, on its first visit, the way its script does: the app's start does not grow with it. The page
// waits for it, so it is never drawn bare.
const STYLES = "/assets/app/styles/cloud_onedrive.css";
if (!document.querySelector(`link[href="${STYLES}"]`)) await new Promise((resolve) => document.head.append(h("link", { rel: "stylesheet", href: STYLES, onload: resolve, onerror: resolve })));

let announce;
const pageReady = new Promise((resolve) => (announce = resolve));

// How full the drive is: who it belongs to, a bar, and the numbers behind it.
function createStorage({ onSignIn }) {
  const element = h("section", { class: "od-storage" });
  let request = null;
  let failed = false;
  async function load(account) {
    request?.abort();
    const mine = (request = new AbortController());
    failed = false;
    element.replaceChildren(...skeleton(1, "row"));
    let status;
    try {
      status = await readStatus(account, mine.signal);
    } catch (error) {
      if (request !== mine) return;
      failed = true;
      element.replaceChildren(
        h("div", { class: "od-storage-problem" }, icon("alert", 17), h("span", { text: `The drive's size could not be read. ${error.message}` }), button({ label: "Sign in again", glyph: "key", small: true, tone: "ghost", onclick: () => onSignIn(account) }), button({ label: "Try again", glyph: "refresh", small: true, onclick: () => load(account) })),
      );
      return;
    }
    if (request !== mine) return;
    const used = Number.isFinite(status.used_bytes) ? status.used_bytes : null;
    const total = Number.isFinite(status.total_bytes) && status.total_bytes > 0 ? status.total_bytes : null;
    const share = used !== null && total !== null ? Math.min(used / total, 1) : null;
    const site = safeLink(status.web_url);
    element.replaceChildren(
      h(
        "div",
        { class: "od-storage-who" },
        h("strong", { text: status.account || account }),
        status.drive_type && pill(`${humanize(String(status.drive_type))} drive`),
        share !== null && share >= NEARLY_FULL && h("span", { class: "pill warn" }, icon("alert", 12), h("span", { text: "Nearly full" })),
        h("span", { class: "spacer" }),
        site && h("a", { class: "btn small", href: site, target: "_blank", rel: "noopener", title: "Opens the drive on OneDrive's site" }, h("span", { text: "Open OneDrive" }), icon("external", 14)),
      ),
      share === null
        ? h("p", { class: "dim", text: used === null ? "The drive does not say how much is in use." : `${formatBytes(used)} in use.` })
        : h(
            "div",
            { class: "od-meter-block" },
            h("div", { class: "od-meter", role: "meter", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(Math.round(share * 100)), "aria-label": "Space in use" }, h("i", { style: `width:${Math.max(share * 100, 0.5)}%` })),
            h("div", { class: "od-meter-words" }, h("span", {}, h("strong", { class: "num", text: formatBytes(used) }), ` of ${formatBytes(total)} in use`), h("span", { class: "num", text: `${Math.round(share * 100)}%` }), h("span", { class: "spacer" }), h("span", { class: "dim num", text: `${formatBytes(total - used)} free` })),
          ),
    );
  }
  return { element, load, failed: () => failed };
}

export function createPart(context) {
  const { activity, tools } = context;
  // The "Ask an agent" button of one of this page's forms, by the OneDrive command the form stands for.
  const askAbout = (command) => agentButton(activity, { commands: [`cloud onedrive ${command}`] }, { small: true });
  let accounts = null;
  let reading = null;
  let stale = false;
  let selected = null;
  let folder = "/";
  let shownAccount = null;
  // Set by a press on "Sign in again" for an account that is signed in, so its sign-in is shown in place of its files.
  let renewing = null;

  const bar = createAccountsBar({ onPick: (name) => (location.hash = addressOf(name)), onAdd: () => addAccountDialog() });
  const transfers = createTransfers({ activity });
  const signIn = createSignIn({ activity, onDone: (account) => signedIn(account) });
  const storage = createStorage({ onSignIn: (account) => renew(account) });
  const files = createFiles({
    onUpload: ({ account, folder: where, names }) => openUpload({ account, folder: where, names, transfers, ask: askAbout("upload"), onDone: () => (files.changed(account, where), storage.load(account)) }),
    onDownload: (target) => openDownload({ ...target, transfers, ask: askAbout("download") }),
    onDelete: (target) => deleteItem({ ...target, onDone: () => (files.changed(target.account, parentOf(target.path)), storage.load(target.account)) }),
    onSignIn: (account) => renew(account),
    // The drive answers again, so a size that could not be read before is asked for once more.
    onListed: (account) => storage.failed() && storage.load(account),
  });
  const drive = h("div", { class: "od-drive", hidden: true }, storage.element, transfers.element, files.element);
  const empty = h("div", { class: "od-empty" }, ...skeleton(3, "row"));
  const every = h(
    "details",
    { class: "od-every" },
    h("summary", {}, icon("terminal", 14), h("span", { text: "The commands behind this page" })),
    h("p", { class: "dim", text: "Each opens the command's own form, with every option it has." }),
    h("div", { class: "chip-row" }, COMMANDS.filter((name) => state.nodes.has(`cloud onedrive ${name}`)).map((name) => h("button", { class: "chip-button", type: "button", text: humanize(name), onclick: () => tools.open(`cloud onedrive ${name}`, { plain: true }) }))),
  );
  const element = h("div", { class: "onedrive" }, bar.element, empty, signIn.element, drive, every);

  readSecretsPath().then(bar.showKept, () => {});
  on("data-stale", () => (stale = true));

  function addAccountDialog() {
    openAddAccount({ taken: (accounts ?? []).map((account) => account.name), ask: askAbout("add-account"), onAdded: (name) => ((stale = true), (location.hash = addressOf(name)), paint()) });
  }

  function renew(account) {
    renewing = account;
    files.forget(account);
    lay();
    signIn.start(account);
  }

  async function signedIn(account) {
    renewing = null;
    stale = true;
    shownAccount = null;
    toast(`${account} is signed in.`, "info");
    await paint();
  }

  // Which of the page's parts are on show, for the accounts as last read and the one selected.
  function lay() {
    const account = accounts?.find((candidate) => candidate.name === selected) ?? null;
    bar.paint(accounts ?? [], selected);
    const needsSignIn = account !== null && (!account.signedIn || renewing === account.name);
    empty.hidden = accounts !== null && accounts.length > 0;
    drive.hidden = account === null || needsSignIn;
    if (account !== null && needsSignIn) signIn.show(account.name);
    else signIn.hide();
    return { account, needsSignIn };
  }

  // The accounts as the command lists them now. Asked once, then again after anything on this machine may have changed them.
  function readAccountsOnce() {
    if (stale || reading === null) {
      stale = false;
      reading = readAccounts().then(
        (list) => (accounts = list),
        (error) => {
          stale = true;
          accounts = null;
          throw error;
        },
      );
    }
    return reading;
  }

  async function paint() {
    try {
      await readAccountsOnce();
    } catch (error) {
      signIn.hide();
      drive.hidden = true;
      empty.hidden = false;
      empty.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The accounts could not be read", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => paint() }) }));
      return;
    }
    if (accounts.length === 0) {
      selected = null;
      lay();
      empty.replaceChildren(
        notice({
          glyph: "globe", title: "No OneDrive account yet",
          body: "Add an account, sign in once on Microsoft's site, and its files show here: to browse, search, upload and download.",
          action: button({ label: "Add an account", glyph: "plus", tone: "primary", onclick: addAccountDialog }),
        }),
      );
      return;
    }
    // An address names its account; without one, the last one shown stays, or the first that is signed in.
    if (!accounts.some((account) => account.name === selected)) selected = (accounts.find((account) => account.signedIn) ?? accounts[0]).name;
    const { account, needsSignIn } = lay();
    if (needsSignIn) return;
    if (shownAccount !== account.name) {
      shownAccount = account.name;
      storage.load(account.name);
    }
    files.open(account.name, folder);
  }

  // `rest` is the address past the page's own: nothing, or "files", an account and the folders down to the one to show.
  function show(rest) {
    if (rest[0] === FILES_WORD && rest[1]) {
      if (rest[1] !== selected) renewing = null;
      selected = rest[1];
      folder = `/${rest.slice(2).join("/")}`;
    } else folder = "/";
    paint();
  }

  // What opening one of the collection's commands does here, once the accounts are read. `preset` holds values by the command's parameter names.
  async function act(command, preset) {
    await paint();
    if (accounts === null) return;
    if (command === "add-account") return addAccountDialog();
    const account = accounts.find((candidate) => candidate.name === (preset.account_name ?? selected));
    if (!account) return;
    if (command === "auth") return account.signedIn ? renew(account.name) : signIn.start(account.name);
    if (!account.signedIn || account.name !== selected) return;
    const remote = typeof preset.remote_path === "string" && preset.remote_path.startsWith("/") ? preset.remote_path.replace(/\/+$/, "") || "/" : null;
    if (command === "list" && remote) location.hash = addressOf(account.name, remote);
    if (command === "search" && typeof preset.query === "string" && preset.query) files.search(preset.query);
    else if (command === "search") files.focusSearch();
    if (command === "upload") openUpload({ account: account.name, folder, names: [], preset: typeof preset.local_path === "string" ? preset.local_path : "", transfers, ask: askAbout("upload"), onDone: () => (files.changed(account.name, folder), storage.load(account.name)) });
    if (command === "download" && remote && remote !== "/") openDownload({ account: account.name, path: remote, item: { name: nameOf(remote), type: "file", size: null }, transfers, ask: askAbout("download") });
  }

  announce({ act });
  return { element, show };
}

// Any of the collection's commands, opened from anywhere, leads to the page. `command` is which one it was (feature_lists/cloud.js).
export async function open(_context, { preset = {}, command } = {}) {
  if (!location.hash.startsWith(PAGE_ADDRESS)) location.hash = PAGE_ADDRESS;
  (await pageReady).act(command, preset);
}
