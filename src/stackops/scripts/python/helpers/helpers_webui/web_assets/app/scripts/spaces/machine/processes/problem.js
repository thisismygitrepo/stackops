import { h } from "/assets/scripts/dom.js";
import { button, callout, notice } from "../../../widgets.js";
import { TOOL_PATH } from "./words.js";

// What the page says when it cannot read the machine: nothing to show yet, a list that stopped following, or a server this page itself stopped.
// It is only built again when what it says changes, so its buttons are not replaced at every failed reading.
export function createProblem({ tools, onRetry }) {
  const element = h("div", { class: "procs-problem" });
  let shown = "";

  function paint({ listed, failure, ended }) {
    const signature = ended ? "ended" : failure ? `${listed} ${failure.status ?? ""} ${failure.message}` : "";
    if (signature === shown) return;
    shown = signature;
    const again = button({ label: "Try again", glyph: "refresh", small: true, onclick: onRetry });
    const actions = () => h("div", { class: "dialog-actions" }, button({ label: "Open the plain form", small: true, onclick: () => tools.open(TOOL_PATH, { plain: true }) }), again);
    element.replaceChildren(
      ...(ended
        ? [callout({ tone: "bad", title: "StackOps was stopped", text: "This page cannot read the machine any more. Start StackOps again and open the link it prints." })]
        : !failure
          ? []
          : listed
            ? [callout({ tone: "warn", title: "The list is not updating", text: failure.message, extra: again })]
            : failure.status === 404
              ? // The page's scripts are served as they are on disk, while its routes are the ones the server started with.
                [notice({ glyph: "power", title: "StackOps needs a restart", body: "This page is newer than the StackOps server that is running. Stop the server, start it again and reload this page.", action: actions() })]
              : [notice({ glyph: "alert", tone: "bad", title: "The process list could not be read", body: failure.message, action: actions() })]),
    );
  }

  return { element, paint };
}
