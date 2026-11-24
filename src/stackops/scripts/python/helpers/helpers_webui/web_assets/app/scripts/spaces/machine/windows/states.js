import { h } from "/assets/scripts/dom.js";
import { button, glyphTile, notice, skeleton } from "../../../widgets.js";

const UNSUPPORTED = {
  wayland: {
    title: "This desktop runs Wayland",
    body: "On Linux this works with an X11 desktop only. Wayland does not let one program list or move the windows of another. Many systems offer an X11 session, often called Xorg, on the sign-in screen.",
  },
  unsupported_system: { title: "Not available on this system", body: "Listing and moving windows works on macOS, on Windows, and on Linux with an X11 desktop." },
};

// macOS keeps this permission per app and gives no way to ask for it from here, so the page says where it is and which app to switch on.
// `launcher` is the app this StackOps was started from when the server could tell, or empty. The page goes on checking while this is shown.
function permissionPanel({ launcher, onOpenSettings, onCheck }) {
  const which = launcher
    ? ["Switch on ", h("b", { text: launcher }), ", the app this StackOps seems to have been started from. If it is not in the list, add it with the plus button."]
    : ["Switch on the app you started StackOps from, which is usually your terminal. If it is not in the list, add it with the plus button."];
  return h(
    "section",
    { class: "windows-permission" },
    glyphTile("lock", 252, 52),
    h(
      "div",
      { class: "windows-permission-text" },
      h("h2", { text: "macOS has not allowed this yet" }),
      h("p", { text: "Seeing and moving other apps' windows needs the Accessibility permission. macOS gives it to the app StackOps was started from, not to StackOps itself." }),
      h(
        "ol",
        { class: "windows-steps" },
        h("li", { text: "Open System Settings, then Privacy & Security, then Accessibility." }),
        h("li", {}, which),
        h("li", { text: "Come back here. The windows show up on their own. If they do not, quit StackOps and start it again." }),
      ),
      h("div", { class: "windows-permission-actions" }, button({ label: "Open Accessibility settings", glyph: "external", tone: "primary", onclick: onOpenSettings }), button({ label: "Check again", glyph: "refresh", onclick: onCheck })),
    ),
  );
}

// What the page shows in place of the list while there is none: the first load, a machine that cannot list its windows, or a failure.
// `missing` is a server from before this page existed, which only a restart cures.
export function stateView(state, { onOpenSettings, onCheck, onPlain }) {
  if (state.kind === "loading") return h("div", { class: "windows-loading" }, skeleton(1, "card"), skeleton(5, "row"));
  if (state.kind === "unavailable" && state.reason === "permission") return permissionPanel({ launcher: state.launcher, onOpenSettings, onCheck });
  if (state.kind === "unavailable") return notice({ glyph: "monitor", ...UNSUPPORTED[state.reason] });
  if (state.missing) {
    return notice({
      glyph: "refresh", title: "Restart StackOps to use this page", body: "This page is newer than the StackOps server that is running. Stop the server, start it again, then reload this page.",
      action: button({ label: "Use the plain form for now", small: true, onclick: onPlain }),
    });
  }
  return notice({ glyph: "alert", tone: "bad", title: "The windows could not be listed", body: state.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: onCheck }) });
}
