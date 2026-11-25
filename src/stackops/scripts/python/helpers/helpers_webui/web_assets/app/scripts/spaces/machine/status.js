import { h, icon } from "/assets/scripts/dom.js";
import { query } from "../../data.js";
import { createPanel } from "../../live_panel.js";
import { rise } from "../../motion.js";
import { glyphTile, pill } from "../../widgets.js";

const COMMAND = ["devops", "self", "status"];
// The parts of the CLI's health check (`devops self status`), each with the page that deals with it. The check's own "Machine" part is left
// out: About this machine, above this panel, shows the same facts. `slow` marks the part that alone takes several seconds. It is asked for by
// itself, so the others are on the page without waiting for it.
const PARTS = [
  { id: "shell", flag: "--shell", title: "Shell profile", glyph: "terminal", hue: 200, href: "#/sessions/shell-profile", place: "Sessions › Shell profile" },
  { id: "repos", flag: "--repos", title: "Projects", glyph: "branch", hue: 150, href: "#/projects", place: "Projects" },
  { id: "ssh", flag: "--ssh", title: "SSH", glyph: "key", hue: 30, href: "#/network/ssh", place: "Network › SSH access" },
  { id: "configs", flag: "--configs", title: "Managed settings", glyph: "sync", hue: 165, href: "#/dotfiles", place: "Dotfiles", slow: true },
  { id: "apps", flag: "--apps", title: "Apps", glyph: "apps", hue: 252, href: "#/apps", place: "Apps" },
  { id: "backup", flag: "--backup", title: "Backups", glyph: "database", hue: 290, href: "#/data", place: "Data" },
];
const LEVELS = { ready: ["Ready", "good"], attention: ["Needs attention", "warn"], error: ["Has a problem", "bad"] };

// Machine status, on the Machine page: how each part of this machine's setup stands, in one line each, with the way to the page that deals
// with it. It is the overview of the health check and nothing more: what a part holds is on that part's own page.
export function createStatusPanel() {
  const ask = (parts, fresh) => query([...COMMAND, ...parts.map((part) => part.flag), "--json"], fresh).then(({ json }) => json ?? {});

  return createPanel({
    title: "Machine status", skeletonShape: "card",
    load: async (fresh) => {
      const slow = ask(PARTS.filter((part) => part.slow), fresh);
      // It is listened to in `render`, after the quick parts are in. Until then a failure of it must not count as one nobody handled.
      slow.catch(() => {});
      return { quick: await ask(PARTS.filter((part) => !part.slow), fresh), slow };
    },
    render: ({ quick, slow }, { setCount }) => {
      const levels = new Map();
      const cards = new Map(
        PARTS.map((part) => {
          const mark = pill("Checking…");
          const line = h("p", { text: "Reading this machine…" });
          return [part.id, { mark, line, element: h("a", { class: "status-card lit", href: part.href, title: `Open ${part.place}` }, h("header", {}, glyphTile(part.glyph, part.hue, 38), h("strong", { text: part.title }), mark), line, h("em", {}, part.place, icon("arrow", 13))) }];
        }),
      );
      const grid = rise(h("div", { class: "status-grid" }, [...cards.values()].map((card) => card.element)));

      // `sections` holds what the check said about the parts it was asked for; a part it says nothing about could not be read.
      function fill(parts, sections) {
        for (const part of parts) {
          const section = sections?.[part.id];
          const [label, tone] = LEVELS[section?.level] ?? ["Unavailable", ""];
          const card = cards.get(part.id);
          card.mark.textContent = label;
          card.mark.className = `pill ${tone}`;
          card.line.textContent = section?.summary ?? "This part of the check could not be read.";
          levels.set(part.id, section?.level ?? "unread");
        }
        if (levels.size < PARTS.length) return setCount("checking the rest…");
        const waiting = [...levels.values()].filter((level) => level !== "ready").length;
        setCount(waiting === 0 ? `all ${PARTS.length} ready` : `${waiting} of ${PARTS.length} ${waiting === 1 ? "needs" : "need"} a look`);
      }

      fill(PARTS.filter((part) => !part.slow), quick);
      // A refresh draws the panel anew, so an answer that comes in after that belongs to cards no longer on the page.
      const late = (sections) => grid.isConnected && fill(PARTS.filter((part) => part.slow), sections);
      slow.then(late, () => late(null));
      return grid;
    },
  });
}
