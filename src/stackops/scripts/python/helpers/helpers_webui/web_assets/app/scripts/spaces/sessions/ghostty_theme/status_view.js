import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { software } from "../../../data.js";
import { button, keyValue, notice, pill } from "../../../widgets.js";
import { APP_NAME, DOWNLOAD_ADDRESS, isUnset, themeWords } from "./words.js";

// The way to get Ghostty: its page in Apps when the catalog can install it on this system, and Ghostty's own download page when it cannot.
// The catalog takes a moment to read, so the button arrives after the words around it.
function installAction() {
  const holder = h("div", { class: "ghostty-theme-install" }, h("div", { class: "skeleton" }));
  const download = () => h("a", { class: "btn", href: DOWNLOAD_ADDRESS, target: "_blank", rel: "noopener noreferrer" }, icon("external", 16), h("span", { text: "Get Ghostty" }));
  software().then(
    (catalog) =>
      holder.replaceChildren(
        catalog.apps.some((app) => app.name === APP_NAME)
          ? button({ label: "Install Ghostty", glyph: "download", tone: "primary", title: "Opens Ghostty in Apps, where one click installs it", onclick: () => (location.hash = `#/apps/${APP_NAME}`) })
          : download(),
      ),
    () => holder.replaceChildren(download()),
  );
  return holder;
}

// What stands at the top of the sheet: that Ghostty is here and the theme it is set to use, or what is in the way and what to do about it.
export function statusView(status) {
  if (status.state === "ready") {
    const theme = status.theme && (isUnset(status.theme) ? h("span", { class: "dim", text: "None set. Ghostty is using its built-in colours." }) : h("strong", { text: themeWords(status.theme) }));
    return keyValue([["Ghostty", pill("Installed", "good")], ["Theme in use", theme]]);
  }
  if (status.state === "unreachable") {
    return notice({
      glyph: "plug", title: "StackOps cannot run Ghostty from here",
      body: `Ghostty is installed at ${tildify(status.app, state.boot.home)}, but its command only works inside Ghostty's own windows. Start StackOps from a Ghostty window, then open this again.`,
    });
  }
  if (state.boot.platform === "Windows") {
    return notice({ glyph: "terminal", title: "Ghostty is not on this machine", body: "Ghostty is a terminal app for macOS and Linux. It does not run on Windows, so there is nothing to set up here." });
  }
  return notice({
    glyph: "terminal", title: "Ghostty is not on this machine",
    body: "Ghostty is a terminal app. Once it is installed, you can open its theme picker from here or set a theme by name.",
    action: installAction(),
  });
}

// A server that was running before this sheet existed has no answer for it, which is the one failure with a known way out.
export function statusFailure(error, retry) {
  if (error.status === 404) {
    return notice({ glyph: "refresh", title: "StackOps needs a restart for this", body: "StackOps was updated while it was running, and this sheet needs the new version. Restart StackOps, then open this again." });
  }
  return notice({ glyph: "alert", tone: "bad", title: "Could not check for Ghostty", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: retry }) });
}
