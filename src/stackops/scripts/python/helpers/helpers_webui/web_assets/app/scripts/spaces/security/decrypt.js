import { openLocker } from "./locker.js";

// "Decrypt a file" opens the sheet it shares with "Encrypt a file or folder", on its own half.
export const open = (context, given) => openLocker(context, "decrypt", given);
