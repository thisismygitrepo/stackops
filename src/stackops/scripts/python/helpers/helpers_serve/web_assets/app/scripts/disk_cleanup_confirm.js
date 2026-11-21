import { h, icon } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { RISKS, adminHow, codeNodes, plainNote, sizeText } from "./disk_cleanup_words.js";
import { openDialog } from "./overlays.js";
import { button, glyphTile } from "./widgets.js";

// The last stop before anything is deleted: every place by name, what is lost with it, and the total. Resolves to true only on an explicit yes.
export function confirmCleanup({ items, bytes }) {
  const dialog = openDialog({ label: "Confirm cleanup", size: "cleanup-confirm" });
  const count = `${items.length} place${items.length === 1 ? "" : "s"}`;
  const risky = items.filter((target) => target.risk === "danger");
  const admin = items.filter((target) => target.requires_root);
  const unsized = items.filter((target) => target.phase !== "done" || !target.sized);
  const go = button({ label: `Remove ${count}`, glyph: "trash", tone: "danger", onclick: () => dialog.close(true) });
  const agree = h("input", { class: "cleanup-check", type: "checkbox", onchange: () => (go.disabled = !agree.checked) });
  go.disabled = risky.length > 0;
  dialog.body.append(
    h(
      "header",
      { class: "confirm-head" },
      glyphTile("trash", 350, 46),
      h("div", {}, h("h2", { text: `Remove ${count}?` }), h("p", {}, "This frees ", h("b", { text: bytes > 0 ? `${unsized.length ? "at least" : "about"} ${sizeText(bytes)}` : "an unknown amount" }), ". It starts as soon as you confirm and cannot be undone.")),
    ),
    h(
      "ul",
      { class: "confirm-list" },
      items.map((target) =>
        h(
          "li",
          {},
          h("strong", { text: target.title }),
          target.risk === "safe" ? h("span") : h("span", { class: `pill ${RISKS[target.risk].tone}`, text: RISKS[target.risk].label }),
          h("b", { class: "num", text: target.phase === "done" && target.sized ? sizeText(target.bytes) : "Size unknown" }),
          target.risk !== "safe" && h("p", {}, codeNodes(plainNote(target.note))),
        ),
      ),
    ),
    h(
      "div",
      { class: "confirm-notes" },
      admin.length > 0 && h("p", {}, icon("lock", 15), h("span", { text: `${admin.length === 1 ? "One of these needs" : `${admin.length} of these need`} administrator rights. ${adminHow(state.boot.platform)}` })),
      unsized.length > 0 && h("p", {}, icon("alert", 15), h("span", { text: `${unsized.length === 1 ? "One place has" : `${unsized.length} places have`} no measured size, so the real total is higher.` })),
      h("p", {}, icon("clock", 15), h("span", { text: "Each place is emptied as it is right now, including anything added since it was measured." })),
      risky.length > 0 && h("label", { class: "confirm-ack" }, agree, h("span", { text: `I understand that ${risky.length === 1 ? "the place" : "the places"} marked Risky cannot be recovered.` })),
    ),
    h("div", { class: "dialog-actions" }, button({ label: "Keep everything", onclick: () => dialog.close(false) }), go),
  );
  return dialog.closed.then((answer) => answer === true);
}
