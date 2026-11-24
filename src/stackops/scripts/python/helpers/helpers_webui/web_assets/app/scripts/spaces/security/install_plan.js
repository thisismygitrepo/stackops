import { h, icon } from "/assets/scripts/dom.js";
import { avatar, button, notice, pill, searchInput } from "../../widgets.js";
import { plural } from "../../words.js";
import { pathWord } from "./tools_kit.js";
import { INSTALL_REASONS } from "./tools_words.js";
import { RUN_STATES, VERDICTS } from "./words.js";

const FILTERS = [["all", "Everything", () => true], ["ready", "Can be installed", (row) => row.reason === "ready"], ["skip", "Left alone", (row) => row.reason !== "ready"]];
// The install command finds an app by its name without regard to case, so that is how the page tells the chosen ones apart.
export const keyOf = (row) => row.name.toLowerCase();

// Why a scan has nothing to install, when it has nothing: the scan did not finish, it kept no copies, or every file has a reason of its own.
function nothingToInstall(plan, { onScanWithUpload }) {
  if (plan.rows.length === 0) return notice({ glyph: "shield", title: "This scan checked no files", body: "There is nothing in it to install." });
  if (plan.rows.every((row) => row.reason === "unfinished")) {
    return notice({ glyph: "clock", title: "This scan did not finish", body: `Only a scan that ran to its end can be installed from. This one is marked "${RUN_STATES[plan.run.status][0]}". Choose another scan above.` });
  }
  if (plan.rows.some((row) => row.reason === "no_copy")) {
    return notice({
      glyph: "up", title: "This scan kept no cloud copies",
      body: "Installing downloads the copy a scan uploads of each clean app. This scan uploaded none, because uploading is off unless a scan is started with it. Run a scan with uploading on, then install from that one.",
      action: button({ label: "Scan with uploading on", glyph: "shield", tone: "primary", onclick: onScanWithUpload }),
    });
  }
  return notice({ glyph: "info", title: "Nothing in this scan can be installed", body: "Every file in it is left alone. The reason for each one is in the list below." });
}

// What installing from one scan would do, before anything is installed: which apps are clean and have a copy to download, which are left
// alone and why, and where they go. The apps to install are ticked; `onChange` hears every change of the choice.
export function createInstallPlan({ onChange, onScanWithUpload }) {
  let plan = null;
  let chosen = new Set();
  let filter = "all";
  let term = "";
  const summary = h("div", { class: "sec-install-summary" });
  const chips = h("div", { class: "chip-row" });
  const picks = h("div", { class: "sec-install-picks" });
  const list = h("ul", { class: "sec-install-list" });
  const search = searchInput({
    placeholder: "Filter apps",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paintList();
    },
  });
  const element = h("div", { class: "sec-install-plan" }, summary, h("div", { class: "sec-install-bar" }, chips, h("span", { class: "spacer" }), search.element), picks, list);
  const ready = () => plan.rows.filter((row) => row.reason === "ready");
  const picked = () => ready().filter((row) => chosen.has(keyOf(row)));

  function choose(keys) {
    chosen = new Set(keys);
    paintSummary();
    paintList();
    onChange();
  }

  function row(entry) {
    const able = entry.reason === "ready";
    const ticked = able && chosen.has(keyOf(entry));
    const [verdict, tone] = VERDICTS[entry.verdict];
    const text = h(
      "span",
      { class: "sec-install-text" },
      h("strong", {}, h("span", { text: entry.name }), entry.version && h("span", { class: "version", text: entry.version })),
      h("span", { text: able ? `Clean. None of ${plural(entry.verdict_engines, "engine")} flagged it.` : INSTALL_REASONS[entry.reason](entry) }),
    );
    const mark = able ? pill(entry.installed_at === null ? "New here" : "Replaces the one here", entry.installed_at === null ? "accent" : "") : pill(verdict, tone);
    if (!able) return h("li", { class: "sec-install-row skipped" }, h("i", { class: "sec-tick off" }, icon("close", 11)), avatar(entry.name, 34), text, mark);
    return h(
      "li",
      {},
      h(
        "button",
        {
          class: "sec-install-row", type: "button", role: "checkbox", "aria-checked": String(ticked), title: `Goes to ${entry.destination}`,
          onclick: () => choose(ticked ? [...chosen].filter((key) => key !== keyOf(entry)) : [...chosen, keyOf(entry)]),
        },
        h("i", { class: "sec-tick" }, icon("check", 12)),
        avatar(entry.name, 34),
        text,
        mark,
      ),
    );
  }

  function paintList() {
    const accepts = FILTERS.find(([id]) => id === filter)[2];
    const found = plan.rows.filter((entry) => accepts(entry) && `${entry.name} ${entry.file_name}`.toLowerCase().includes(term));
    list.replaceChildren(...(found.length ? found.map(row) : [h("li", { class: "sec-runs-none", text: term ? "No app matches that." : "No app is in this group." })]));
  }

  function paintSummary() {
    const able = ready();
    const going = picked();
    const replaced = going.filter((entry) => entry.installed_at !== null).length;
    const share = (count) => `--share:${plan.rows.length ? count / plan.rows.length : 0}`;
    summary.replaceChildren(
      ...(able.length === 0
        ? [nothingToInstall(plan, { onScanWithUpload })]
        : [
            h("span", { class: "sec-meter", title: `${going.length} chosen · ${able.length - going.length} not chosen · ${plan.rows.length - able.length} left alone` }, h("i", { class: "go", style: share(going.length) }), h("i", { class: "wait", style: share(able.length - going.length) })),
            h(
              "div",
              { class: "sec-install-counts" },
              h("span", {}, h("strong", { text: String(going.length) }), ` of ${able.length} chosen`),
              h("span", {}, h("strong", { text: String(replaced) }), replaced === 1 ? " replaces a file" : " replace a file"),
              h("span", {}, h("strong", { text: String(going.length - replaced) }), " new here"),
              h("span", {}, h("strong", { text: String(plan.rows.length - able.length) }), " left alone"),
            ),
            h("p", { class: "sec-install-where" }, "Each one is downloaded, checked against the fingerprint the scan recorded, and put in ", pathWord(plan.folder), "."),
          ]),
    );
    picks.replaceChildren(
      ...(able.length > 1
        ? [button({ label: `Choose all ${able.length}`, small: true, tone: "ghost", onclick: () => choose(able.map(keyOf)) }), button({ label: "Choose none", small: true, tone: "ghost", onclick: () => choose([]) })]
        : []),
    );
  }

  return {
    element,
    picked: () => (plan ? picked() : []),
    ready: () => (plan ? ready() : []),
    // `wanted` is the one app the view was opened for, or empty for every app that can be installed.
    show(next, wanted) {
      plan = next;
      const able = ready();
      const named = able.filter((entry) => keyOf(entry) === wanted.toLowerCase());
      chosen = new Set((named.length ? named : able).map(keyOf));
      filter = "all";
      chips.replaceChildren(
        ...FILTERS.map(([id, label, accepts]) =>
          h(
            "button",
            {
              class: "chip-button", type: "button", "aria-pressed": String(id === filter), "data-id": id,
              onclick: () => {
                filter = id;
                for (const chip of chips.children) chip.setAttribute("aria-pressed", String(chip.dataset.id === id));
                paintList();
              },
            },
            h("span", { text: label }),
            h("b", { text: String(plan.rows.filter(accepts).length) }),
          ),
        ),
      );
      paintSummary();
      paintList();
      onChange();
    },
  };
}
