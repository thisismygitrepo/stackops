import { debounce, formatClock, h, icon } from "/assets/scripts/dom.js";
import { confirmCleanup } from "./disk_cleanup_confirm.js";
import { createCleanupList } from "./disk_cleanup_list.js";
import { changedOptions, defaultOptions, openCleanupOptions } from "./disk_cleanup_options.js";
import { canPick, isMeasured, isQuiet } from "./disk_cleanup_rows.js";
import { runCleanup } from "./disk_cleanup_run.js";
import { createCleanupScanner } from "./disk_cleanup_scan.js";
import { cleanupBanner, createCleanupSummary, createCleanupTray } from "./disk_cleanup_summary.js";
import { RISKS, RISK_ORDER, categoryOf } from "./disk_cleanup_words.js";
import { replay } from "./motion.js";
import { button, notice, searchInput } from "./widgets.js";

const ROOTS_DELAY_MILLISECONDS = 700;
const total = (targets) => targets.reduce((sum, target) => sum + (isMeasured(target) ? target.bytes : 0), 0);

// Free up disk space: measure on arrival, let the person choose what goes, confirm, clean exactly that, then show what it freed.
export function createDiskCleanup({ activity }) {
  const picked = new Set();
  const decided = new Set();
  const options = defaultOptions();
  let risk = "all";
  let term = "";
  let run = null;
  let started = false;
  let clock = 0;

  const view = {
    picked, open: new Set(), locked: false, loading: true, scale: 0,
    matches: (target) => (risk === "all" || target.risk === risk) && (term === "" || `${target.title} ${target.note} ${categoryOf(target.category).title}`.toLowerCase().includes(term)),
    toggle: (key, on) => setMany([key], on),
    setMany,
    retry: (key) => scanner.retry(key),
    clearFilters() {
      risk = "all";
      term = "";
      search.input.value = "";
      paint();
    },
  };
  const scanner = createCleanupScanner({ onChange: onScan });
  const list = createCleanupList(view);
  const summary = createCleanupSummary();
  const all = () => [...scanner.targets.values()];
  const chosen = () => all().filter((target) => picked.has(target.key) && canPick(target));
  const wanted = (target) => isMeasured(target) && RISKS[target.risk].rank <= RISKS[options.level].rank && (options.admin || !target.requires_root);

  const bannerHolder = h("div");
  const problemHolder = h("div");
  const chips = h("div", { class: "chip-row" });
  const search = searchInput({
    placeholder: "Find a place",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      list.render(all());
    },
  });
  const tools = h("div", { class: "cleanup-tools" }, chips, h("span", { class: "spacer" }), search.element);
  const stamp = h("span", { class: "cleanup-stamp" });
  const badge = h("b", { hidden: true });
  const optionsButton = h("button", { class: "btn tune", type: "button", title: "What to look at and what to tick for you" }, icon("sliders", 16), h("span", { text: "Options" }), badge);
  const rescanButton = button({ label: "Scan again", glyph: "refresh", onclick: () => scan() });
  const tray = createCleanupTray({ onClear: () => setMany([...picked], false), onClean: clean });

  function setMany(keys, on) {
    for (const key of keys) {
      decided.add(key);
      if (on) picked.add(key);
      else picked.delete(key);
    }
    list.syncPicks();
    paintTotals();
    replay(tray.element, "bump");
  }

  function paintTotals() {
    const progress = scanner.progress();
    const ready = all().filter(isMeasured);
    const ticked = chosen();
    const bytes = total(ticked);
    summary.paint({ scan: progress, drive: scanner.disk(), found: total(ready), safe: total(ready.filter((target) => target.risk === "safe")), places: ready.length, picked: bytes });
    tray.paint({
      count: ticked.length, bytes, unsure: ticked.some((target) => !isMeasured(target) || !target.sized || target.estimateKind === "at_least"),
      hidden: progress.loading || scanner.failure() !== "" || scanner.targets.size === 0 || (run !== null && run.phase !== "done"),
    });
    stamp.textContent = !progress.busy && progress.measuredAt && scanner.failure() === "" ? `Measured at ${formatClock(progress.measuredAt / 1000)}` : "";
    rescanButton.disabled = progress.busy || view.locked;
  }

  function paintBanner() {
    bannerHolder.replaceChildren(
      ...(run
        ? [
            cleanupBanner(run, {
              onReveal: () => activity.reveal(run.id),
              // Letting go of a cleanup that is still running does not stop it: the page stops waiting and measures those places again.
              onDismiss() {
                const waiting = run.phase !== "done" ? run.keys : [];
                for (const key of waiting) picked.delete(key);
                run = null;
                view.locked = false;
                paintBanner();
                paint();
                scanner.remeasure(waiting);
              },
            }),
          ]
        : []),
    );
  }

  function paint() {
    const listed = all().filter((target) => !isQuiet(target));
    chips.replaceChildren(
      ...[["all", "Everything"], ...RISK_ORDER.map((id) => [id, RISKS[id].label])].map(([id, label]) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(risk === id), title: RISKS[id]?.hint,
            onclick: () => {
              risk = id;
              paint();
            },
          },
          h("span", { text: label }),
          h("b", { text: String(id === "all" ? listed.length : listed.filter((target) => target.risk === id).length) }),
        ),
      ),
    );
    const failure = scanner.failure();
    problemHolder.replaceChildren(...(failure ? [notice({ glyph: "alert", tone: "bad", title: "The scan could not start", body: `${failure.replace(/[.\s]*$/, "")}. If StackOps was just updated, restart it and open this page again.`, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => scan() }) })] : []));
    for (const part of [summary.element, tools, list.element]) part.hidden = failure !== "";
    badge.hidden = changedOptions(options) === 0;
    badge.textContent = String(changedOptions(options));
    list.render(all());
    paintTotals();
  }

  function onScan() {
    const progress = scanner.progress();
    view.loading = progress.loading;
    for (const target of scanner.targets.values()) {
      if (target.phase !== "done" && target.phase !== "error") continue;
      if (!canPick(target)) picked.delete(target.key);
      else if (!decided.has(target.key) && wanted(target)) picked.add(target.key);
      if (isMeasured(target)) decided.add(target.key);
    }
    if (!progress.loading) for (const key of [...picked]) if (!scanner.targets.has(key)) picked.delete(key);
    clearInterval(clock);
    if (progress.busy) clock = setInterval(paintTotals, 1000);
    paint();
  }

  function scan() {
    started = true;
    return scanner.start({ categories: options.categories, searchRoots: options.roots });
  }

  const rootsSoon = debounce(() => scanner.setRoots(options.roots), ROOTS_DELAY_MILLISECONDS);
  function optionsChanged(kind) {
    if (kind === "categories") scanner.setCategories(options.categories);
    else if (kind === "roots") rootsSoon();
    else {
      picked.clear();
      decided.clear();
      for (const target of all().filter(isMeasured)) {
        decided.add(target.key);
        if (wanted(target)) picked.add(target.key);
      }
    }
    paint();
  }

  async function clean() {
    const items = chosen().sort((left, right) => right.bytes - left.bytes);
    if (items.length === 0) return;
    // The dialog dims the page with a blur; nothing underneath keeps moving while it is open.
    element.classList.add("still");
    const sure = await confirmCleanup({ items, bytes: total(items) });
    element.classList.remove("still");
    if (!sure) return;
    await runCleanup({
      activity, scanner, items, roots: options.roots,
      onPhase(next) {
        if (run !== next && next.phase !== "cleaning") return;
        run = next;
        if (run.phase === "checking") for (const key of run.keys) picked.delete(key);
        view.locked = run.phase !== "done";
        paintBanner();
        paint();
        if (run.phase !== "checking") element.closest(".stage")?.scrollTo({ top: 0, behavior: "smooth" });
      },
    });
  }

  optionsButton.addEventListener("click", () => !optionsButton.classList.contains("open") && openCleanupOptions(optionsButton, { options, onChange: optionsChanged }));
  const element = h(
    "div",
    { class: "cleanup", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("a", { class: "cleanup-back", href: "#/machine" }, icon("back", 14), h("span", { text: "Machine" })), h("h1", { text: "Free up disk space" }), h("p", { text: "See what is taking up room, tick what you can live without, and remove it in one go. Nothing is deleted until you confirm." })),
      h("div", { class: "view-actions" }, stamp, optionsButton, rescanButton),
    ),
    bannerHolder,
    summary.element,
    tools,
    problemHolder,
    list.element,
    tray.element,
  );
  paint();
  return { element, show: () => !started && scan() };
}
