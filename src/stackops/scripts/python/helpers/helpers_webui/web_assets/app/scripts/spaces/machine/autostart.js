import { createStartupPage } from "./autostart/page.js";
import { AUTOSTART_HASH } from "./autostart/words.js";

// Startup programs, in place of the form made from the options of `utils machine autostart`: everything that starts on its own on arrival,
// drawn by when it starts, whose it is and what kind of thing it is, with the person's own entries turned off or removed from the page.
// It is a page of its own at #/machine/autostart behind its card on Machine, and not a sheet: the list runs to dozens of rows, and to
// hundreds with the standard parts of the system, and the picture above it needs the width.
let arrival = {};
let page = null;

// What the page is opened with is taken over as filters, by the command's parameter names. Nothing is ever changed from a preset: turning
// an entry off takes a click on the page and a confirmation.
export function open(_context, { preset }) {
  arrival = preset ?? {};
  if (location.hash === AUTOSTART_HASH) page?.show();
  else location.hash = AUTOSTART_HASH;
}

export function createPart(context) {
  page = createStartupPage(context, () => {
    const taken = arrival;
    arrival = {};
    return taken;
  });
  return page;
}
