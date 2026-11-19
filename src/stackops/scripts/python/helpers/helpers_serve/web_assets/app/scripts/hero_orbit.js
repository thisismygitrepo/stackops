import { h, icon } from "/assets/scripts/dom.js";
import { SPACES } from "./catalog.js";

const ORBIT_SIZE = 250;
const CHIP_ICON_SIZE = 15;
const RING_STAGGER = 0.7;
const RINGS = [
  { inset: 0, seconds: 18, tone: "--violet", way: "normal", counter: "reverse" },
  { inset: 34, seconds: 12, tone: "--azure", way: "reverse", counter: "normal" },
  { inset: 70, seconds: 8, tone: "--mint", way: "normal", counter: "reverse" },
];

export function createHeroOrbit() {
  const spaces = SPACES.filter((space) => space.id !== "home");
  const rings = RINGS.map((ring, ringIndex) => {
    const radius = (ORBIT_SIZE - ring.inset * 2) / 2;
    const members = spaces.filter((_, index) => index % RINGS.length === ringIndex);
    const chips = members.map((space, index) => {
      const angle = (index / members.length) * Math.PI * 2 + ringIndex * RING_STAGGER;
      return h(
        "span",
        { class: "orbit-chip", style: `left:calc(50% + ${Math.cos(angle) * radius}px);top:calc(50% + ${Math.sin(angle) * radius}px)` },
        icon(space.glyph, CHIP_ICON_SIZE),
      );
    });
    return h(
      "i",
      { class: "orbit-ring", style: `inset:${ring.inset}px;--tone:var(${ring.tone});--turn:${ring.seconds}s;--way:${ring.way};--counter:${ring.counter}` },
      h("i", { class: "orbit-spin" }, chips),
    );
  });
  return h("div", { class: "hero-orbit", "aria-hidden": "true" }, rings, h("img", { class: "orbit-core", src: "/assets/favicon.svg", alt: "" }));
}
