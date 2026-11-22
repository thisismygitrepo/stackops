import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { clockText, sizeText } from "./disk_cleanup_words.js";
import { countUp } from "./motion.js";
import { button, glyphTile, iconButton, pill } from "./widgets.js";
import { plural } from "./words.js";

const NEARLY_FULL = 0.1;
const NAMED_LIMIT = 2;

// The top of the page: how much can be freed, how the scan is going, and what the selection does to the disk.
export function createCleanupSummary() {
  const overline = h("span", { class: "overline" });
  const figure = h("strong", { class: "cleanup-figure num", text: "—" });
  const line = h("p");
  const fill = h("i");
  const status = h("span");
  const hint = h("small", { class: "dim" });
  const progress = h("div", { class: "cleanup-progress" }, h("div", { class: "cleanup-bar" }, fill), h("p", {}, h("i", { class: "ring" }), status), hint);
  const diskHead = h("div", { class: "cleanup-disk-head" });
  const diskFree = h("strong", { class: "num" });
  const diskOf = h("span", { class: "dim" });
  const used = h("i", { class: "used" });
  const gain = h("i", { class: "gain" });
  const after = h("p");
  const disk = h("div", { class: "cleanup-disk" }, diskHead, h("div", { class: "cleanup-disk-figure" }, diskFree, diskOf), h("div", { class: "disk-meter" }, used, gain), after);
  const element = h("section", { class: "cleanup-hero" }, h("div", { class: "cleanup-total" }, overline, figure, line, progress), disk);

  function paint({ scan, drive, found, safe, places, picked }) {
    const working = scan.busy;
    overline.textContent = scan.loading ? "Looking around" : working ? "Found so far" : "Can be freed";
    if (!scan.loading) countUp(figure, found, (value) => (found === 0 ? "0 GB" : sizeText(value, found)));
    line.replaceChildren(...(scan.loading ? ["Finding the places that collect clutter…"] : places === 0 ? [working ? "Nothing yet." : "Nothing to remove right now."] : [`in ${plural(places, "place")} · `, ...(safe > 0 ? [h("b", { text: sizeText(safe) }), " of it is safe to remove"] : ["none of it is marked safe"])]));
    progress.hidden = !working;
    if (working) {
      const names = scan.measuring.map((target) => target.title);
      const left = scan.total - scan.done;
      fill.style.transform = `scaleX(${scan.total ? scan.done / scan.total : 0})`;
      status.textContent = scan.loading
        ? "Starting…"
        : `Measuring ${names.slice(0, NAMED_LIMIT).join(", ")}${names.length > NAMED_LIMIT ? ` and ${names.length - NAMED_LIMIT} more` : ""} · ${left} of ${scan.total} left · ${clockText(scan.seconds)}`;
      hint.textContent = "Big folders take a minute or two to measure. You can start ticking what is already here.";
    }
    disk.hidden = !drive;
    if (!drive) return;
    const share = drive.free / drive.total;
    diskHead.replaceChildren(h("span", { class: "overline", text: "This disk" }), ...(share < NEARLY_FULL ? [pill("Almost full", "bad")] : []));
    diskFree.textContent = `${sizeText(drive.free)} free`;
    diskOf.textContent = `of ${sizeText(drive.total)}`;
    const gained = Math.min(picked, drive.total - drive.free);
    const usedShare = Math.max(drive.total - drive.free - gained, 0) / drive.total;
    used.style.setProperty("--share", String(usedShare));
    gain.style.setProperty("--from", String(usedShare));
    gain.style.setProperty("--share", String(gained / drive.total));
    disk.classList.toggle("tight", share < NEARLY_FULL);
    after.replaceChildren(...(picked > 0 ? ["After cleaning: about ", h("b", { text: `${sizeText(drive.free + picked)} free` })] : ["Tick places below to see how much room you get back."]));
  }

  return { element, paint };
}

// The bar that stays in view: what is ticked, what that frees, and the one button that starts the cleanup.
export function createCleanupTray({ onClear, onClean }) {
  const title = h("strong");
  const note = h("span");
  const clear = button({ label: "Clear", tone: "ghost", onclick: onClear });
  const clean = button({ label: "Clean selected", glyph: "trash", tone: "primary", onclick: onClean });
  const element = h("div", { class: "tray cleanup-tray", hidden: true }, glyphTile("trash", 350, 38), h("div", { class: "cleanup-tray-text" }, title, note), h("span", { class: "spacer" }), clear, clean);
  return {
    element,
    paint({ count, bytes, unsure, hidden }) {
      element.hidden = hidden;
      title.textContent = count ? `${plural(count, "place")} ticked` : "Nothing ticked yet";
      note.textContent = count ? `You will free ${bytes > 0 ? `about ${sizeText(bytes)}` : "an unknown amount"}${unsure && bytes > 0 ? " or more" : ""}` : "Tick the places you want to empty.";
      clear.hidden = count === 0;
      clean.disabled = count === 0;
    },
  };
}

function outcomeItem(item) {
  const left = item.after ?? item.before ?? 0;
  const text = item.after === 0 ? (item.before ? `${sizeText(item.before)} removed` : "Removed") : item.after === null ? "Not checked" : item.before && item.after < item.before ? `${sizeText(left)} left` : "Still there";
  return h("li", { class: item.after === 0 ? "gone" : "kept" }, icon(item.after === 0 ? "check" : "alert", 13), h("span", { text: item.title }), h("b", { class: "num", text }));
}

// What a cleanup is doing, and afterwards what it freed.
export function cleanupBanner(run, { onReveal, onDismiss }) {
  if (run.phase !== "done") {
    const cleaning = run.phase === "cleaning";
    return h(
      "section",
      { class: "cleanup-banner working" },
      h("span", { class: "task-mark" }, h("i", { class: "ring" })),
      h("div", { class: "cleanup-banner-text" }, h("h2", { text: cleaning ? `Cleaning ${plural(run.items.length, "place")}…` : "Checking what was freed…" }), h("p", { text: cleaning ? "It runs in the console. If it asks for a password, type it there." : "Measuring the cleaned places again." })),
      button({ label: "Show progress", glyph: "terminal", small: true, onclick: onReveal }),
      iconButton("close", "Stop waiting for it", onDismiss),
    );
  }
  const failed = run.exitCode !== 0;
  // Not strictly correct: when a cleaned place has no size to compare, before or after, the figure is what the disk itself gained meanwhile,
  // which other programs move too. It is only used when the places add up to nothing, and it says "about".
  const unsure = run.items.some((item) => item.before === null || item.after === null);
  const gained = run.freed === 0 && unsure && run.freeBefore !== null && run.freeAfter !== null ? Math.max(run.freeAfter - run.freeBefore, 0) : 0;
  const emptied = !failed && run.items.every((item) => item.after === 0);
  const title = run.freed > 0 ? `Freed ${sizeText(run.freed)}` : gained > 0 ? `Freed about ${sizeText(gained)}` : emptied ? "Cleaned" : "Nothing was freed";
  const poor = failed || (run.freed === 0 && gained === 0 && !emptied);
  const diskLine = run.freeBefore !== null && run.freeAfter !== null ? `This disk has ${sizeText(run.freeAfter)} free now; it had ${sizeText(run.freeBefore)} before.` : "";
  const problem = failed ? "At least one place could not be cleaned. " : "";
  return h(
    "section",
    { class: `cleanup-banner ${poor ? "warn" : "good"}` },
    h("span", { class: `task-mark ${poor ? "failed" : "done"}` }, icon(poor ? "alert" : "check", 22)),
    h("div", { class: "cleanup-banner-text" }, h("h2", { text: title }), h("p", { text: `${problem}${diskLine}` }), h("ul", { class: "cleanup-outcome" }, run.items.map(outcomeItem)), h("small", { class: "dim", text: `Finished at ${formatClock(run.finishedAt)}` })),
    button({ label: "Show what happened", glyph: "terminal", small: true, onclick: onReveal }),
    iconButton("close", "Dismiss", onDismiss),
  );
}
