import { openLocker } from "./locker.js";

// "Encrypt a file or folder" opens the sheet it shares with "Decrypt a file", on its own half.
export const open = (context, given) => openLocker(context, "encrypt", given);
