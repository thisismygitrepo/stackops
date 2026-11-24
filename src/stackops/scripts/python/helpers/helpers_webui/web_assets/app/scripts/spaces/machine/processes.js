import { createProcessesPage } from "./processes/page.js";
import { PROCESSES_HASH } from "./processes/words.js";

// The Processes page, which stands in for the form of `utils machine kill-process`. It is made once, by whichever asks first: the Machine
// page showing it at its address, or a tool opening it with filters to start from.
let page = null;

export function createPart(context) {
  page ??= createProcessesPage(context);
  return page;
}

export function open(context, { preset }) {
  createPart(context).applyPreset(preset);
  location.hash = PROCESSES_HASH;
}
