import { h, icon } from "/assets/scripts/dom.js";
import { rise } from "../../motion.js";
import { linkCard, viewHead } from "../../space_kit.js";
import { button, emojiTile, sectionHead, skeleton } from "../../widgets.js";
import { plural } from "../../words.js";
import { assets, files, reasonOf, setup } from "./model.js";
import { ASSETS_HASH, ASSET_SETS, FILES, FILES_HASH, SCRIPTS, SCRIPTS_HASH, SETUP_HASH, STEPS, WIZARD_PATH, WIZARD_TITLE, needsAttention, standingOf, stepsDone } from "./words.js";

const ELSEWHERE = [
  { href: "#/dotfiles", emoji: "📂", name: "devops config dotfiles", title: "Dotfiles", blurb: "Sync, collect and move the settings files of your tools." },
  { href: "#/sessions", emoji: "🐚", name: "devops config terminal", title: "Terminal setup", blurb: "Shell profile, multiplexer and themes, at the foot of Sessions." },
  { href: "#/tools/devops/config", emoji: "🧰", name: "devops config", title: "Every settings tool", blurb: "The whole group as plain forms, in the Toolbox." },
];

// A card that says where one part of Settings stands and opens that part. `visual` is drawn anew with each reading.
function capsule({ href, onclick, emoji, name, title }) {
  const line = h("p", { text: "Reading this machine…" });
  const visual = h("div", { class: "settings-ov-visual" });
  const properties = { class: "settings-ov-card lit", ...(href ? { href } : { type: "button", onclick }) };
  return { line, visual, element: h(href ? "a" : "button", properties, h("header", {}, emojiTile(emoji, name, 42), h("strong", { text: title }), icon("arrow", 15)), visual, line) };
}

// Settings, at #/settings: where the settings files, the guided setup and the packaged files stand, each on a card that opens its own view.
export function createOverview({ tools }) {
  const filesLine = h("p", { text: "Reading this machine…" });
  const filesMap = h("div", { class: "settings-ov-map" }, skeleton(9, "row"));
  const filesBoard = h(
    "section",
    { class: "settings-ov-files" },
    h(
      "header",
      {},
      emojiTile("🗂️", "settings files", 46),
      h("div", { class: "settings-ov-title" }, h("h2", { text: "Settings files" }), filesLine),
      h("a", { class: "btn", href: FILES_HASH }, h("span", { text: "Open" }), icon("arrow", 15)),
    ),
    filesMap,
  );
  const steps = capsule({ href: SETUP_HASH, emoji: "🧭", name: "devops config setup", title: "Guided setup" });
  const packaged = capsule({ href: ASSETS_HASH, emoji: "📋", name: "devops config copy-assets", title: "Packaged files" });
  const scripts = capsule({ href: SCRIPTS_HASH, emoji: "🚀", name: "devops config init-script", title: "Setup scripts" });
  const wizard = capsule({ onclick: () => tools.open(WIZARD_PATH), emoji: "🤖", name: WIZARD_PATH, title: WIZARD_TITLE });
  scripts.visual.append(h("ul", { class: "settings-ov-chips" }, SCRIPTS.map((script) => h("li", { text: script.title }))));
  scripts.line.textContent = "Read what each one does before anything runs.";
  wizard.visual.append(h("ul", { class: "settings-ov-chips" }, ["Apps", "Shell profile", "Settings", "Projects", "Data"].map((word) => h("li", { text: word }))));
  wizard.line.textContent = "One guided run for a new machine. You tick what you want in a checklist.";

  const again = button({ label: "Check again", glyph: "refresh", title: "Read the files on this machine and check each one again", onclick: () => [files, setup, assets].forEach((reading) => reading.reload()) });
  again.classList.add("settings-again");
  const element = h(
    "div",
    { class: "settings-ov" },
    viewHead({ title: "Settings", lede: "The files that tell StackOps how to work on this machine, and the ways to set them up.", actions: [again] }),
    filesBoard,
    rise(h("div", { class: "settings-ov-grid" }, steps.element, packaged.element, scripts.element, wizard.element)),
    h("section", { class: "block" }, sectionHead("Kept on other pages"), h("div", { class: "tool-grid" }, ELSEWHERE.map(linkCard))),
  );
  const unread = (target, error) => (target.textContent = `This could not be read. ${reasonOf(error)}`);
  const spin = () => element.classList.toggle("loading", [files, setup, assets].some((reading) => reading.reading.loading));

  files.watch(element, ({ value, failure }) => {
    spin();
    if (failure) {
      filesMap.replaceChildren();
      return unread(filesLine, failure);
    }
    if (!value) return;
    const standings = value.files.map((file) => [file, standingOf(file, value.checks.get(file.kind))]);
    const count = (test) => standings.filter(([, standing]) => test(standing)).length;
    const waiting = count((standing) => standing.id === "checking");
    const trouble = count(needsAttention);
    filesLine.textContent = [
      `${count((standing) => !["missing", "unavailable"].includes(standing.id))} of ${standings.length} on this machine`,
      waiting ? "checking them now" : `${count((standing) => standing.id === "valid")} pass their check`,
      trouble > 0 && `${trouble} ${trouble === 1 ? "needs" : "need"} attention`,
    ].filter(Boolean).join(" · ");
    filesMap.replaceChildren(
      ...standings.map(([file, standing]) =>
        h(
          "a",
          { class: `settings-ov-file ${standing.id}`, href: `${FILES_HASH}/${file.kind}` },
          emojiTile(FILES[file.kind].emoji, file.kind, 34),
          h("span", { class: "settings-ov-file-text" }, h("strong", { text: FILES[file.kind].title }), h("span", { text: standing.label })),
          h("i", { class: `settings-dot ${standing.id}` }),
        ),
      ),
    );
  });

  setup.watch(element, ({ value, failure }) => {
    spin();
    if (failure) return unread(steps.line, failure);
    if (!value) return;
    const done = stepsDone(value);
    const finished = STEPS.filter((step) => done[step.id]).length;
    const next = STEPS.find((step) => done[step.id] === false);
    steps.visual.replaceChildren(h("div", { class: "settings-ov-steps" }, STEPS.map((step) => h("i", { class: done[step.id] ? "done" : done[step.id] === null ? "unknown" : "", title: step.title }))));
    steps.line.textContent = value.settings_problem
      ? "The StackOps defaults file does not pass its check, so some steps cannot be read."
      : next ? `${finished} of ${STEPS.length} set up. Next: ${next.title.toLowerCase()}.` : `All ${STEPS.length} are set up.`;
  });

  assets.watch(element, ({ value, failure }) => {
    spin();
    if (failure) return unread(packaged.line, failure);
    if (!value) return;
    if (!value.supported) return void (packaged.line.textContent = "StackOps has no packaged files for this system.");
    const groups = value.sets.flatMap((set) => set.groups);
    const total = (key) => groups.reduce((sum, group) => sum + group[key], 0);
    const parts = [["same", total("same")], ["changed", total("changed")], ["missing", total("missing")], ["extra", total("extra")]];
    packaged.visual.replaceChildren(h("div", { class: "settings-bar" }, parts.filter(([, amount]) => amount > 0).map(([key, amount]) => h("i", { class: key, style: `flex-grow:${amount}` }))));
    const differs = [total("changed") && `${total("changed")} changed here`, total("missing") && `${total("missing")} not copied yet`, total("extra") && `${total("extra")} only on this machine`].filter(Boolean);
    packaged.line.textContent = `${plural(total("offered"), "file")} for ${Object.values(ASSET_SETS).map((set) => set.title.toLowerCase()).join(" and ")}. ${differs.length ? `${differs.join(", ")}.` : "The copies here match what StackOps ships."}`;
  });

  return { element, show: () => [files, setup, assets].forEach((reading) => reading.sync()) };
}
