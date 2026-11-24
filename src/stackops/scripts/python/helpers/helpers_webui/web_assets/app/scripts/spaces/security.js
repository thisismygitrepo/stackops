import { h } from "/assets/scripts/dom.js";
import { createView, linkCard } from "../space_kit.js";
import { button, sectionHead, segmented } from "../widgets.js";
import { createPostureSection } from "./security/posture.js";
import { createScanStarter } from "./security/scan_start.js";
import { createScansSection } from "./security/scans.js";
import { createToolCards } from "./security/tool_cards.js";
import { SCANS_HASH } from "./security/words.js";

const SECTIONS = [["overview", "This machine"], ["scans", "Scans"]];

// Two sections that swap in place: what is installed here and how it stands, at #/security, and the saved scans, at #/security/scans/…
// Under them, the tools that each open a sheet of their own (feature_lists/security.js), as cards that say what this machine has for them.
export function createSecuritySpace(context) {
  const starter = createScanStarter(context);
  const sections = { overview: createPostureSection({ ...context, starter }), scans: createScansSection({ ...context, starter }) };
  let current = null;
  const picker = segmented(SECTIONS, (id) => (location.hash = id === "overview" ? "#/security" : SCANS_HASH));
  const cards = createToolCards(context);
  // The secrets themselves have a page of their own; what stays here is the way to it, beside the tools that lock files.
  cards.locks.prepend(linkCard({ href: "#/vault", emoji: "🔐", name: "devops vault", title: "Vault", blurb: "The logins, keys and tokens kept for you. See, add, change and remove them." }));
  const element = createView(
    {
      title: "Security", lede: "What VirusTotal's antivirus engines make of the apps installed here, and a record of every scan.",
      actions: [button({ label: "Scan a file", glyph: "report", onclick: starter.file }), button({ label: "Scan every app", glyph: "shield", tone: "primary", onclick: starter.everything })],
    },
    h("div", { class: "section-bar" }, picker.element),
    Object.values(sections).map((section) => section.element),
    h("section", { class: "block" }, sectionHead("Work with saved scans"), cards.scans),
    h("section", { class: "block" }, sectionHead("Files to and from the cloud"), cards.cloud),
    h("section", { class: "block" }, sectionHead("Secrets and encryption"), cards.locks),
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
      cards.ensure();
    },
  };
}
