import { h } from "/assets/scripts/dom.js";
import { createView, toolGrid } from "../space_kit.js";
import { button, sectionHead, segmented } from "../widgets.js";
import { createPostureSection } from "./security/posture.js";
import { createScanStarter } from "./security/scan_start.js";
import { createScansSection } from "./security/scans.js";
import { SCANS_HASH } from "./security/words.js";

const SECTIONS = [["overview", "This machine"], ["scans", "Scans"]];
const SCAN_TOOLS = ["devops security install", "devops security export", "devops security upload", "devops security download"];
const SECRET_TOOLS = ["devops vault stats", "devops vault validate", "devops vault add", "devops vault rotate", "devops data encrypt", "devops data decrypt"];

// Two sections that swap in place: what is installed here and how it stands, at #/security, and the saved scans, at #/security/scans/…
export function createSecuritySpace(context) {
  const starter = createScanStarter(context);
  const sections = { overview: createPostureSection({ ...context, starter }), scans: createScansSection({ ...context, starter }) };
  let current = null;
  const picker = segmented(SECTIONS, (id) => (location.hash = id === "overview" ? "#/security" : SCANS_HASH));
  const element = createView(
    {
      title: "Security", lede: "What VirusTotal's antivirus engines make of the apps installed here, and a record of every scan.",
      actions: [button({ label: "Scan a file", glyph: "report", onclick: starter.file }), button({ label: "Scan every app", glyph: "shield", tone: "primary", onclick: starter.everything })],
    },
    h("div", { class: "section-bar" }, picker.element),
    Object.values(sections).map((section) => section.element),
    h("section", { class: "block" }, sectionHead("Work with saved scans"), toolGrid(context.tools, SCAN_TOOLS)),
    h("section", { class: "block" }, sectionHead("Secrets and encryption"), toolGrid(context.tools, SECRET_TOOLS)),
  );
  return {
    element,
    show(route) {
      const id = route[0] === "scans" ? "scans" : "overview";
      for (const [key, section] of Object.entries(sections)) section.element.hidden = key !== id;
      picker.set(id);
      if (current !== id) element.closest(".stage").scrollTo(0, 0);
      current = id;
      sections[id].show(route.slice(1));
    },
  };
}
