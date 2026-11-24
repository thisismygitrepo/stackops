import { createPart, open as openSsh } from "./ssh.js";

// `devops network ssh add-key` opens the SSH page with the keyboard on its "Add a key" part.
export { createPart };
export const open = (context, given) => openSsh(context, given, "keys");
