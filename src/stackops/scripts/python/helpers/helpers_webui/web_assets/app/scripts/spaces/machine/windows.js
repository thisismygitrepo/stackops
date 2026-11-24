import { createWindowsPage } from "./windows/page.js";
import { WINDOWS_HASH } from "./windows/words.js";

// Open windows, in place of the form made from the options of `utils machine window`: every window on arrival, drawn on a map of the screens
// and listed by app, with the command's actions as buttons. It is a page of its own at #/machine/windows and not a sheet, because a list to
// look through, a map and a selection need the room, and because it stays worth watching while other things are done.
let arrival = {};
let page = null;

// Of what the page may be opened with, only a title is taken over, as the text in its search box. An action is never taken from a preset:
// minimizing or closing a window takes a click on the page.
export function open(_context, { preset }) {
  arrival = preset ?? {};
  if (location.hash === WINDOWS_HASH) page?.show();
  else location.hash = WINDOWS_HASH;
}

export function createPart(context) {
  page = createWindowsPage(context, () => {
    const taken = arrival;
    arrival = {};
    return taken;
  });
  return page;
}
