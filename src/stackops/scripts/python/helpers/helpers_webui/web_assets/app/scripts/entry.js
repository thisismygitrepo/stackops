import { VIEW_KEY } from "./catalog.js";

// The app page starts here and not in main.js. A module's imports are all fetched before its first line runs, so a check inside main.js loads the whole app view and only then leaves for the developer view. catalog.js imports nothing, which keeps this cheap.
// main.js is added as a script tag and not with import(): the page's load event then still waits for the app, as it did when main.js was the page's own script, and whatever drives the page counts on that.
if (localStorage.getItem(VIEW_KEY) === "dev") location.replace("/dev");
else {
  // A module that is missing or broken stops the app before main.js runs, so main.js cannot say so. The browser reports a missing file on the script tag and a broken one on the window; until the app is up, either one replaces the loading note.
  const failed = (event) => document.body.classList.contains("booted") || document.getElementById("app").replaceChildren(Object.assign(document.createElement("p"), { className: "boot-note failed", textContent: `StackOps could not start: ${event.message ?? "a part of the page did not load. The browser's console names it."}` }));
  window.addEventListener("error", failed);
  document.head.append(Object.assign(document.createElement("script"), { type: "module", src: "/assets/app/scripts/main.js", onerror: failed }));
}
