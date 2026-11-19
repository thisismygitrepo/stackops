import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { RISKS, actionText, adminText, codeNodes, estimateText, firstSentence, plainNote, qualifierNoteOf, qualifierOf, quietReason, sizeText } from "./disk_cleanup_words.js";
import { button, keyValue } from "./widgets.js";

const PATH_PREVIEW = 6;
const PATH_LIMIT = 200;

export const isMeasured = (target) => target.phase === "done" && target.status === "ready";
// A place that took too long to measure can still be cleaned: the cleanup measures it again, without a time limit.
export const canPick = (target) => isMeasured(target) || (target.phase === "error" && target.slow);
export const isQuiet = (target) => target.phase === "done" && target.status !== "ready";

function pathList(target) {
  const list = h("ul", { class: "cleanup-paths" });
  const more = h("button", { class: "link", type: "button", text: `Show all ${target.paths.length.toLocaleString()}` });
  const paint = (limit) => {
    const hidden = target.paths.length - Math.min(limit, target.paths.length);
    list.replaceChildren(
      ...target.paths.slice(0, limit).map((entry) => h("li", {}, h("code", { class: "path", text: tildify(entry.path, state.boot.home) }), h("b", { class: "num", text: sizeText(entry.bytes) }))),
      ...(hidden > 0 && limit === PATH_LIMIT ? [h("li", { class: "dim", text: `…and ${hidden.toLocaleString()} more` })] : []),
    );
    more.hidden = limit === PATH_LIMIT || hidden === 0;
  };
  more.addEventListener("click", () => paint(PATH_LIMIT));
  paint(PATH_PREVIEW);
  return h("div", { class: "cleanup-inside" }, h("h4", { text: target.paths.length > PATH_PREVIEW ? "Biggest items inside" : "What is removed" }), list, more);
}

function detail(target) {
  const measured = isMeasured(target);
  return h(
    "div",
    { class: "cleanup-detail" },
    h("p", { class: "cleanup-note" }, codeNodes(plainNote(target.note))),
    keyValue([
      ["What happens", measured && actionText(target)],
      ["How much", measured && target.sized && qualifierOf(target) && `${estimateText(target)}. ${qualifierNoteOf(target)}`],
      ["How risky", `${RISKS[target.risk].label}. ${RISKS[target.risk].hint}`],
      ["Permission", target.requires_root && adminText(state.boot.platform)],
    ].filter(([, value]) => value)),
    measured && target.paths.length > 0 && pathList(target),
  );
}

function sizeCell(target, view) {
  if (target.phase === "error") {
    return h("div", { class: "cleanup-size" }, h("span", { class: "dim", text: target.slow ? "Too big to measure quickly" : "Not measured" }), button({ label: "Try again", glyph: "refresh", small: true, onclick: () => view.retry(target.key) }));
  }
  if (target.phase !== "done") return h("div", { class: "cleanup-size pending" }, target.phase === "measuring" && h("i", { class: "ring" }), h("span", { text: target.phase === "measuring" ? "Measuring" : "In line" }));
  if (!target.sized) return h("div", { class: "cleanup-size" }, h("span", { class: "dim", text: "Size unknown" }));
  return h(
    "div",
    { class: "cleanup-size" },
    h("span", { class: "cleanup-amount" }, qualifierOf(target) && h("small", { text: qualifierOf(target) }), h("strong", { class: "num", text: sizeText(target.bytes) })),
    h("i", { class: "cleanup-weight", style: `--share:${view.scale ? Math.max(target.bytes / view.scale, 0.012) : 0}` }),
  );
}

export function targetRow(target, view) {
  const risk = RISKS[target.risk];
  const pickable = canPick(target);
  const key = target.key;
  const box = h("input", { class: "cleanup-check", type: "checkbox", "data-part": "check", "aria-label": `Remove ${target.title}`, disabled: !pickable || view.locked });
  box.checked = view.picked.has(key);
  box.addEventListener("change", () => view.toggle(key, box.checked));
  const more = h("button", { class: "icon-btn cleanup-more", type: "button", "data-part": "more", "aria-expanded": "false", title: "What this is and what is inside", "aria-label": `Details for ${target.title}` }, icon("down", 16));
  const summary = target.phase === "error" ? [target.slow ? "It can still be removed; its size shows up afterwards." : target.problem] : codeNodes(firstSentence(target.note));
  const main = h(
    "div",
    { class: "cleanup-main" },
    box,
    h("div", { class: "cleanup-text" }, h("strong", { text: target.title }), h("span", {}, summary)),
    target.requires_root && h("span", { class: "pill cleanup-admin", title: adminText(state.boot.platform) }, icon("lock", 12), "Needs admin"),
    h("span", { class: `pill ${risk.tone}`, title: risk.hint, text: risk.label }),
    sizeCell(target, view),
    more,
  );
  const row = h("li", { class: `cleanup-row${box.checked ? " picked" : ""}${pickable ? "" : " unpickable"}${target.phase === "error" && !target.slow ? " failed" : ""}`, "data-key": key }, main);
  const setOpen = (open) => {
    more.setAttribute("aria-expanded", String(open));
    row.querySelector(".cleanup-detail")?.remove();
    if (open) row.append(detail(target));
  };
  more.addEventListener("click", () => {
    const open = !view.open.has(key);
    if (open) view.open.add(key);
    else view.open.delete(key);
    setOpen(open);
  });
  main.addEventListener("click", (event) => {
    if (event.target.closest("button, input") || !pickable || view.locked) return;
    box.checked = !box.checked;
    view.toggle(key, box.checked);
  });
  setOpen(view.open.has(key));
  return { row, box };
}

export function quietFold(targets, open, onToggle) {
  const fold = h(
    "details",
    { class: "fold cleanup-quiet", open },
    h("summary", {}, icon("chevron", 14), h("span", { text: `Nothing to free in ${targets.length} other place${targets.length === 1 ? "" : "s"}` })),
    h(
      "ul",
      {},
      targets.map((target) => {
        const reason = quietReason(target);
        return h("li", {}, h("strong", { text: target.title }), h("span", { class: "dim", text: reason.label }), reason.detail && h("small", { class: "dim", title: reason.detail, text: reason.detail }));
      }),
    ),
  );
  fold.addEventListener("toggle", () => onToggle(fold.open));
  return fold;
}
