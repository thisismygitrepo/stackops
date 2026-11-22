import { VIEW_KEY } from "./catalog.js";

// The app page starts here and not in main.js. A module's imports are all fetched before its first line runs, so a check inside main.js loads the whole app view and only then leaves for the developer view. catalog.js imports nothing, which keeps this cheap.
if (localStorage.getItem(VIEW_KEY) === "dev") location.replace("/dev");
else import("./main.js");
