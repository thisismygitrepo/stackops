import { h, icon } from "/assets/scripts/dom.js";
import { button, highlight, iconButton, notice, searchInput, skeleton } from "../../widgets.js";
import { formatBytes, plural, relativeTime } from "../../words.js";
import { listFolder, searchDrive, searchWords } from "./onedrive_api.js";
import { KINDS, addressOf, folderOf, isFolder, joinPath, kindOf, kindWord, safeLink } from "./onedrive_words.js";

const ROW_LIMIT = 300;
const FOCUS_PAUSE_MILLISECONDS = 350;
const COLUMNS = [["name", "Name"], ["kind", "Kind"], ["size", "Size"], ["modified", "Changed"]];
// A column starts in the order that is asked for most: names from A, sizes from the largest, changes from the newest.
const STARTS_DESCENDING = new Set(["size", "modified"]);
const SORT_VALUE = {
  name: (item) => item.name.toLowerCase(),
  kind: (item) => kindWord(kindOf(item)),
  size: (item) => item.size ?? 0,
  modified: (item) => Date.parse(item.last_modified) || 0,
};
const fullDate = (value) => (Number.isNaN(Date.parse(value)) ? "" : new Date(value).toLocaleString());

// The files of one account: a folder at a time, or what a search of the whole drive found. A folder's listing is kept for the visit, so going
// back to it shows at once; Refresh and anything that changes it ask the drive again. The page hands in what its buttons do, and hears through
// `onListed` of each listing the drive gave.
export function createFiles({ onUpload, onDownload, onDelete, onSignIn, onListed }) {
  const kept = new Map();
  let account = null;
  let folder = "/";
  let items = null;
  let listedAt = 0;
  let found = null;
  let searched = "";
  let term = "";
  let kind = "all";
  let sort = { key: "name", descending: false };
  let problem = null;
  let loading = false;
  let showAll = false;
  let request = null;

  const count = h("span", { class: "count" });
  const path = h("nav", { class: "od-path", "aria-label": "Folder" });
  const kinds = h("div", { class: "chip-row od-kinds" });
  const share = h("div", { class: "od-share" });
  const body = h("div", { class: "od-list" });
  const filter = searchInput({
    placeholder: "Filter this list",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      showAll = false;
      paintList();
    },
  });
  const drive = searchInput({ placeholder: "Search the whole drive", oninput: (value) => value.trim() === "" && found !== null && leaveSearch() });
  drive.input.addEventListener("keydown", (event) => event.key === "Enter" && search(drive.input.value));
  drive.element.classList.add("od-drive-search");
  drive.element.title = "Type a word and press Enter";
  const uploader = button({ label: "Upload", glyph: "up", tone: "primary", small: true, title: "Put a file from this computer into this folder", onclick: () => onUpload({ account, folder, names: (items ?? []).filter((item) => !isFolder(item)).map((item) => item.name) }) });
  const refresher = iconButton("refresh", "Ask the drive again", () => (found === null ? open(account, folder, true) : search(searched)));
  const element = h(
    "section",
    { class: "panel od-files" },
    h("header", { class: "panel-head" }, h("h2", { text: "Files" }), count, h("span", { class: "spacer" }), drive.element, uploader, refresher),
    h("div", { class: "panel-body" }, path, h("div", { class: "od-tools" }, filter.element, kinds), share, body),
  );

  const listed = () => found ?? items ?? [];
  const keyOf = (name, where) => `${name}\n${where}`;
  // Where an item is: beside the others in the open folder, or wherever the drive says a search result sits.
  const pathOf = (item) => {
    const where = found === null ? folder : folderOf(item);
    return where === null ? null : joinPath(where, item.name);
  };

  function paintPath() {
    if (found !== null) {
      path.replaceChildren(
        h("a", { class: "od-path-back", href: addressOf(account, folder), onclick: leaveSearch }, icon("back", 15), h("span", { text: folder === "/" ? "Back to the top folder" : `Back to ${folder.slice(folder.lastIndexOf("/") + 1)}` })),
        h("span", { class: "od-path-here", text: `Everything in the drive that matches “${searched}”` }),
      );
      return;
    }
    const names = folder.split("/").filter(Boolean);
    const steps = [{ label: "OneDrive", where: "/" }, ...names.map((name, index) => ({ label: name, where: `/${names.slice(0, index + 1).join("/")}` }))];
    path.replaceChildren(
      ...steps.flatMap((step, index) => [
        index > 0 && icon("chevron", 12),
        index === steps.length - 1 ? h("span", { class: "od-path-here", text: step.label }) : h("a", { href: addressOf(account, step.where), text: step.label }),
      ]).filter(Boolean),
    );
  }

  // The kinds that are in the list, as buttons that narrow it. They are also the key to the bar under them: each carries its kind's colour.
  function paintKinds() {
    const all = listed();
    const folders = all.filter(isFolder).length;
    const present = KINDS.map((entry) => ({ ...entry, count: all.filter((item) => kindOf(item) === entry.id).length })).filter((entry) => entry.count > 0);
    const chip = (id, label, total, slot) =>
      h("button", { class: "chip-button", type: "button", "aria-pressed": String(kind === id), onclick: () => ((kind = kind === id && id !== "all" ? "all" : id), (showAll = false), paintKinds(), paintList()) }, slot && h("i", { class: "od-swatch", "data-kind": slot }), h("span", { text: label }), h("b", { text: total.toLocaleString() }));
    kinds.replaceChildren(...[all.length > 0 && chip("all", "All", all.length), folders > 0 && chip("folder", "Folders", folders), ...present.map((entry) => chip(entry.id, entry.label, entry.count, entry.id))].filter(Boolean));

    // What the files in the list weigh, by kind. Folders are left out: a folder's size is everything inside it, which is not this folder's own files.
    const sized = present.map((entry) => ({ ...entry, bytes: all.filter((item) => kindOf(item) === entry.id).reduce((total, item) => total + (item.size ?? 0), 0) })).filter((entry) => entry.bytes > 0);
    const total = sized.reduce((sum, entry) => sum + entry.bytes, 0);
    share.hidden = total === 0;
    if (total === 0) return;
    share.replaceChildren(
      h("span", { class: "od-share-label", text: `${formatBytes(total)} in ${plural(all.length - folders, "file")}` }),
      h(
        "div",
        { class: "od-share-bar", role: "img", "aria-label": `Size by kind: ${sized.map((entry) => `${entry.label} ${formatBytes(entry.bytes)}`).join(", ")}` },
        sized.map((entry) => h("i", { "data-kind": entry.id, style: `flex-grow:${entry.bytes}`, title: `${entry.label}: ${formatBytes(entry.bytes)}, ${entry.bytes / total < 0.01 ? "under 1" : Math.round((entry.bytes / total) * 100)}% of the files here` })),
      ),
    );
  }

  function rowOf(item) {
    const where = pathOf(item);
    const itemKind = kindOf(item);
    const link = safeLink(item.web_url);
    const parent = found === null ? null : folderOf(item);
    const name = highlight(item.name, term);
    return h(
      "tr",
      { class: "od-row" },
      h(
        "td",
        { class: "od-name" },
        h("span", { class: "od-mark", "data-kind": itemKind }, icon(isFolder(item) ? "folder" : "report", 16)),
        isFolder(item) && where ? h("a", { href: addressOf(account, where), title: `Open ${item.name}` }, name) : h("span", { title: item.name }, name),
      ),
      h("td", { class: "dim", text: kindWord(itemKind) }),
      h("td", { class: "num", text: isFolder(item) && !item.size ? "—" : formatBytes(item.size ?? 0) }),
      h("td", { class: "dim", title: fullDate(item.last_modified), text: relativeTime(item.last_modified) || "—" }),
      found !== null && h("td", {}, parent === null ? h("span", { class: "dim", text: "—" }) : h("a", { class: "od-where", href: addressOf(account, parent), title: "Open the folder it is in", text: parent === "/" ? "OneDrive" : parent })),
      h(
        "td",
        { class: "od-acts" },
        !isFolder(item) && where && iconButton("download", `Download ${item.name}`, () => onDownload({ account, path: where, item })),
        link && h("a", { class: "icon-btn", href: link, target: "_blank", rel: "noopener", title: "Open on OneDrive's site", "aria-label": `Open ${item.name} on OneDrive's site` }, icon("external", 16)),
        where && h("button", { class: "icon-btn danger", type: "button", title: "Move to the recycle bin", "aria-label": `Move ${item.name} to the recycle bin`, onclick: () => onDelete({ account, path: where, item }) }, icon("trash", 16)),
      ),
    );
  }

  function header() {
    const head = ([key, label]) =>
      h(
        "th",
        { "aria-sort": sort.key === key ? (sort.descending ? "descending" : "ascending") : "none" },
        h("button", { type: "button", title: `Sort by ${label.toLowerCase()}`, onclick: () => ((sort = { key, descending: sort.key === key ? !sort.descending : STARTS_DESCENDING.has(key) }), paintList()) }, label, icon("down", 12)),
      );
    return h("thead", {}, h("tr", {}, COLUMNS.map(head), found !== null && h("th", { text: "Folder" }), h("th", { class: "od-acts", "aria-label": "Actions" })));
  }

  function sorted(rows) {
    const value = SORT_VALUE[sort.key];
    const order = (first, second) => {
      // By name, folders stay ahead of files. By size or date they mix, so the largest or newest thing is on top whatever it is.
      if (sort.key === "name" && isFolder(first) !== isFolder(second)) return isFolder(first) ? -1 : 1;
      const [a, b] = [value(first), value(second)];
      const way = a < b ? -1 : a > b ? 1 : first.name.localeCompare(second.name);
      return sort.descending ? -way : way;
    };
    return [...rows].sort(order);
  }

  function paintList() {
    const all = listed();
    const rows = sorted(all.filter((item) => (kind === "all" || kindOf(item) === kind) && (term === "" || item.name.toLowerCase().includes(term))));
    count.textContent = loading ? "Asking the drive…" : problem ? "" : `${rows.length === all.length ? plural(all.length, "item") : `${rows.length.toLocaleString()} of ${plural(all.length, "item")}`}${found === null && listedAt ? ` · listed ${relativeTime(listedAt)}` : ""}`;
    if (problem) {
      body.replaceChildren(
        notice({
          glyph: "alert", tone: "bad", title: found === null ? "This folder did not load" : "The search did not work", body: problem,
          action: h(
            "div",
            { class: "dialog-actions" },
            found === null && folder !== "/" && h("a", { class: "btn small ghost", href: addressOf(account, "/") }, h("span", { text: "Go to the top folder" })),
            button({ label: "Sign in again", glyph: "key", small: true, tone: "ghost", title: "For when the saved sign-in is no longer accepted", onclick: () => onSignIn(account) }),
            button({ label: "Try again", glyph: "refresh", small: true, onclick: () => (found === null ? open(account, folder, true) : search(searched)) }),
          ),
        }),
      );
      return;
    }
    if (loading && all.length === 0) return body.replaceChildren(...skeleton(5, "row"));
    if (all.length === 0) {
      return body.replaceChildren(
        found === null
          ? notice({ glyph: "folder", title: "This folder is empty", body: "Upload a file to put something in it.", action: button({ label: "Upload a file", glyph: "up", small: true, onclick: () => uploader.click() }) })
          : notice({ glyph: "search", title: "Nothing in the drive matches", body: `No file or folder has “${searched}” in its name or contents.` }),
      );
    }
    if (rows.length === 0) return body.replaceChildren(notice({ glyph: "search", title: "Nothing here matches", body: "Clear the filter or pick another kind." }));
    const shown = showAll ? rows : rows.slice(0, ROW_LIMIT);
    const table = h("div", { class: "table-scroll" }, h("table", { class: "data-table od-table" }, header(), h("tbody", {}, shown.map(rowOf))));
    // A long list is cut short so the page stays quick; the button brings the rest.
    const more = h("div", { class: "od-more" }, button({ label: `Show all ${rows.length.toLocaleString()}`, small: true, onclick: () => ((showAll = true), paintList()) }));
    body.replaceChildren(...(shown.length < rows.length ? [table, more] : [table]));
  }

  function paint() {
    element.classList.toggle("loading", loading);
    uploader.hidden = found !== null;
    paintPath();
    paintKinds();
    paintList();
  }

  function clearNarrowing() {
    term = "";
    kind = "all";
    showAll = false;
    filter.input.value = "";
  }

  // Shows `nextFolder` of `nextAccount`: from what is kept of it, or from the drive when nothing is or `fresh` is asked.
  async function open(nextAccount, nextFolder, fresh = false) {
    const moved = nextAccount !== account || nextFolder !== folder || found !== null;
    account = nextAccount;
    folder = nextFolder;
    request?.abort();
    request = null;
    if (moved) {
      clearNarrowing();
      found = null;
      searched = "";
      drive.input.value = "";
    }
    const held = kept.get(keyOf(account, folder));
    problem = null;
    if (held && !fresh) {
      ({ items, at: listedAt } = held);
      loading = false;
      return paint();
    }
    const mine = (request = new AbortController());
    if (moved) items = null;
    loading = true;
    paint();
    try {
      const got = await listFolder(account, folder, mine.signal);
      if (request !== mine) return;
      items = got;
      listedAt = Date.now() / 1000;
      kept.set(keyOf(account, folder), { items, at: listedAt });
      onListed(account);
    } catch (error) {
      if (request !== mine) return;
      items = null;
      problem = error.message;
    }
    request = null;
    loading = false;
    paint();
  }

  async function search(text) {
    const words = searchWords(text);
    if (words === "" || account === null) return;
    request?.abort();
    const mine = (request = new AbortController());
    clearNarrowing();
    searched = words;
    drive.input.value = words;
    found = [];
    problem = null;
    loading = true;
    paint();
    try {
      const got = await searchDrive(account, words, mine.signal);
      if (request !== mine) return;
      found = got;
    } catch (error) {
      if (request !== mine) return;
      problem = error.message;
    }
    request = null;
    loading = false;
    paint();
  }

  function leaveSearch() {
    if (found !== null) open(account, folder);
  }

  return {
    element,
    open,
    search,
    // After a pause: the search window that led here hands the focus back to the page as it closes, and that must not undo this.
    focusSearch: () => setTimeout(() => drive.input.focus(), FOCUS_PAUSE_MILLISECONDS),
    // After a change to `where` of `name`: what is kept of it is dropped, and it is asked for again if it is the folder on show.
    changed(name, where) {
      kept.delete(keyOf(name, where));
      if (name !== account) return;
      if (found !== null) search(searched);
      else if (where === folder) open(account, folder, true);
    },
    forget: (name) => [...kept.keys()].filter((key) => key.startsWith(`${name}\n`)).forEach((key) => kept.delete(key)),
  };
}
