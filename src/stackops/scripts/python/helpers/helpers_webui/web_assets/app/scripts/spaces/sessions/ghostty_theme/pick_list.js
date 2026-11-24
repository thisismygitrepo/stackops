import { h } from "/assets/scripts/dom.js";
import { button, pill, searchInput } from "../../../widgets.js";
import { plural } from "../../../words.js";

// Every theme name in one scrolling list, narrowed as you type, each with its own Apply. No previews: Ghostty's picker is the place for those.
// The rows are made once and only shown or hidden after that, so typing stays quick with several hundred names.
// `onApply(name)` returns a promise, and the list takes no other press until it settles. `mark` says which names are in use now.
export function createPickList({ names, term, onApply }) {
  const count = h("span", { class: "count" });
  const empty = h("li", { class: "ghostty-theme-empty dim", text: "No theme has that in its name.", hidden: true });
  const list = h("ul", { class: "ghostty-theme-names", "aria-label": "Themes" });
  let inUse = new Set();

  async function press(name) {
    list.classList.add("busy");
    list.setAttribute("aria-busy", "true");
    try {
      await onApply(name);
    } finally {
      list.classList.remove("busy");
      list.removeAttribute("aria-busy");
    }
  }

  const rows = names.map((name) => {
    const tail = h("span", { class: "ghostty-theme-tail" });
    return { name, key: name.toLowerCase(), tail, used: null, element: h("li", { class: "ghostty-theme-row" }, h("span", { class: "ghostty-theme-name", title: name, text: name }), tail) };
  });

  function mark(used) {
    inUse = used;
    for (const row of rows) {
      const now = inUse.has(row.name);
      if (row.used === now) continue;
      row.used = now;
      row.element.classList.toggle("current", now);
      row.tail.replaceChildren(now ? pill("In use", "good") : button({ label: "Apply", small: true, tone: "ghost", title: `Set ${row.name} as Ghostty's theme`, onclick: () => press(row.name) }));
    }
  }

  // Every word typed has to be in the name, in any order.
  function narrow(text) {
    const words = text.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    for (const row of rows) {
      const fits = words.every((word) => row.key.includes(word));
      row.element.hidden = !fits;
      if (fits) shown += 1;
    }
    empty.hidden = shown > 0;
    count.textContent = words.length ? `${shown.toLocaleString()} of ${plural(rows.length, "theme")}` : plural(rows.length, "theme");
    list.scrollTop = 0;
  }

  const box = searchInput({ placeholder: "Find a theme by name", oninput: narrow });
  box.input.value = term;
  list.append(...rows.map((row) => row.element), empty);
  mark(inUse);
  narrow(term);
  return { element: h("div", { class: "ghostty-theme-pick" }, h("div", { class: "ghostty-theme-bar" }, box.element, count), list), mark };
}
