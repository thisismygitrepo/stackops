import { debounce, h, icon, tildify } from "/assets/scripts/dom.js";
import { nodeHash, state } from "/assets/scripts/state.js";
import { capture } from "./data.js";
import { openSheet } from "./overlays.js";
import { editFile } from "./space_kit.js";
import { button, copyChip, emojiTile, highlight, notice, searchInput, segmented, skeleton } from "./widgets.js";
import { plural } from "./words.js";

const SEARCH_DELAY_MILLISECONDS = 350;
const SHORTEST_TERM = 2;
const HIT_STEP = 200;
const MODES = [["text", "Inside files"], ["file", "File names"]];
// What was last searched for, so coming back from the editor lands on the same results.
const last = { term: "", mode: "text", extension: "" };

// The guided sheet for `seek`, over its `--json` output. Design choice: symbol and meaning-based search stay in the developer view, because
// on a mid-sized repository a symbol search takes several seconds and returns megabytes, which is no good for search-as-you-type.
export function openFind({ activity }) {
  const node = state.nodes.get("seek");
  const home = state.boot.home;
  const root = state.settings.workingDirectory.replace(/^~(?=\/|$)/, home);
  const sheet = openSheet({ label: "Find in files", wide: true });
  const count = h("span", { class: "count" });
  const results = h("div", { class: "find-results" });
  const more = h("button", { class: "btn small ghost", type: "button", hidden: true });
  let hits = [];
  let limit = HIT_STEP;
  let ticket = 0;

  // The editor reads `file:line`, so the Edit every page uses also lands on the matching line. The sheet closes because the editor opens in the activity panel behind it.
  const edit = (path, line) => {
    sheet.close();
    editFile(activity, { title: `${path.split("/").at(-1)}${line ? `:${line}` : ""}`, kind: "file", path: line ? `${path}:${line}` : path });
  };

  function paint() {
    const term = last.term.trim();
    const files = new Map();
    for (const hit of hits.slice(0, limit)) files.set(hit.path, [...(files.get(hit.path) ?? []), hit]);
    results.replaceChildren(
      ...[...files].map(([path, found]) => {
        const shown = path.startsWith(`${root}/`) ? path.slice(root.length + 1) : tildify(path, home);
        const cut = shown.lastIndexOf("/");
        return h(
          "div",
          { class: "find-file" },
          h(
            "header",
            {},
            h("strong", { text: shown.slice(cut + 1) }),
            copyChip(path, cut < 0 ? "./" : shown.slice(0, cut)),
            button({ label: "Open", glyph: "terminal", small: true, tone: "ghost", title: "Open this file in a text editor inside the activity panel", onclick: () => edit(path) }),
          ),
          found.filter((hit) => hit.line).map((hit) =>
            h(
              "div",
              { class: "find-hit" },
              copyChip(`${path}:${hit.line}`, String(hit.line)),
              h("button", { class: "find-line", type: "button", title: "Open at this line in a text editor inside the activity panel", onclick: () => edit(path, hit.line) }, highlight(hit.text.trim(), term)),
            ),
          ),
        );
      }),
    );
    if (hits.length === 0) results.replaceChildren(notice({ glyph: "search", title: "Nothing found", body: last.mode === "file" ? "No file name matches that." : "No file contains that." }));
    count.textContent = hits.length === 0 ? "" : last.mode === "file" ? plural(hits.length, "file") : `${plural(hits.length, "line")} in ${plural(new Set(hits.map((hit) => hit.path)).size, "file")}`;
    more.hidden = hits.length <= limit;
    more.textContent = `Show ${Math.min(HIT_STEP, hits.length - limit)} more of ${hits.length.toLocaleString()}`;
  }

  async function search() {
    const mine = (ticket += 1);
    const term = last.term.trim();
    const extension = last.extension.trim();
    more.hidden = true;
    if (last.mode === "text" && term.length < SHORTEST_TERM) {
      count.textContent = "";
      results.classList.remove("loading");
      results.replaceChildren(notice({ glyph: "search", title: "Type what you are looking for", body: `Every file under ${tildify(root, home)} is searched as you type.` }));
      return;
    }
    results.classList.add("loading");
    if (!results.querySelector(".find-file")) results.replaceChildren(...skeleton(4, "row"));
    try {
      const { json } = await capture(["seek", ".", ...(term ? [term] : []), ...(last.mode === "file" ? ["--file"] : []), ...(extension ? ["--extension", extension] : []), "--json"]);
      if (mine !== ticket) return;
      hits = json ?? [];
      limit = HIT_STEP;
      paint();
    } catch (error) {
      if (mine !== ticket) return;
      count.textContent = "";
      results.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The search didn't run", body: error.message }));
    }
    results.classList.remove("loading");
  }

  const searchSoon = debounce(search, SEARCH_DELAY_MILLISECONDS);
  const box = searchInput({
    placeholder: "What are you looking for?",
    oninput: (value) => {
      last.term = value;
      searchSoon();
    },
  });
  box.input.value = last.term;
  const modes = segmented(MODES, (mode) => {
    last.mode = mode;
    modes.set(mode);
    search();
  });
  const extensionBox = h("input", {
    class: "text-input", type: "text", spellcheck: "false", autocomplete: "off", placeholder: "Any file type", "aria-label": "File type", title: "Only look in files of this type, such as py or md",
    value: last.extension,
    oninput: () => {
      last.extension = extensionBox.value;
      searchSoon();
    },
  });
  more.addEventListener("click", () => {
    limit += HIT_STEP;
    paint();
  });
  sheet.body.append(
    h("header", { class: "tool-head" }, emojiTile(node.icon || "🔎", node.path, 56), h("div", {}, h("span", { class: "overline", text: "StackOps" }), h("h1", { text: "Find in files" }), h("p", { text: `Looks through ${tildify(root, home)} and every folder inside it.` }))),
    h("div", { class: "find-bar" }, box.element, modes.element, extensionBox, h("span", { class: "spacer" }), count),
    results,
    more,
  );
  sheet.foot.hidden = false;
  sheet.foot.append(h("a", { class: "dev-link", href: `/dev${nodeHash(node)}`, title: "Symbol and meaning-based search, and every other option, are in the developer view" }, icon("code", 14), h("span", { text: "Developer view" })));
  modes.set(last.mode);
  box.input.focus();
  search();
}
