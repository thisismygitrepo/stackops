import { open as openStartup } from "./autostart.js";

// `utils machine autostart-add`, wherever it is opened: the Startup programs page with its dialog for picking the script, in place of a
// form with a box to type the script's name into.
export const open = (context) => openStartup(context, { preset: { add_script: true } });
