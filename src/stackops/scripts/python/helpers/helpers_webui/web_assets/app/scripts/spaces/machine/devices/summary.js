import { h } from "/assets/scripts/dom.js";
import { stat } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { countsOf } from "./model.js";
import { diskName, size, volumeName } from "./words.js";

const NAMED = 2;
const named = (names) => `${names.slice(0, NAMED).join(", ")}${names.length > NAMED ? ` and ${names.length - NAMED} more` : ""}`;

// The four things to know before reading the list: the room left on this computer, what is plugged in, what waits to be mounted, and what
// is mounted from other computers.
export function createDeviceSummary() {
  const free = stat({ glyph: "database", hue: 252, label: "Free on this computer" });
  const plugged = stat({ glyph: "plug", hue: 28, label: "Plugged in" });
  const waiting = stat({ glyph: "eyeOff", hue: 200, label: "Not mounted" });
  const shares = stat({ glyph: "globe", hue: 150, label: "Network shares" });
  const element = h("section", { class: "stats devices-stats" }, free.element, plugged.element, waiting.element, shares.element);

  function paint(picture) {
    const counts = countsOf(picture);
    free.set(counts.free === null ? "—" : size(counts.free), counts.internal ? `of ${size(counts.room)} on ${plural(counts.internal, "internal disk")}` : "No internal disk was found");
    plugged.set(counts.plugged.length, counts.plugged.length ? named(counts.plugged.map(diskName)) : "No external disk or disk image");
    waiting.set(counts.waiting, counts.waiting ? "Press Mount on one to use it" : "Everything is mounted");
    shares.set(counts.shares.length, counts.shares.length ? named(counts.shares.map(volumeName)) : "None connected");
  }

  return { element, paint };
}
