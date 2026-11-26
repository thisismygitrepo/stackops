import { h, icon, toast } from "/assets/scripts/dom.js";
import { agentButton } from "../../agent_ask.js";
import { openSheet } from "../../overlays.js";
import { button, callout, emojiTile } from "../../widgets.js";
import { setup } from "./model.js";
import { ASSETS_HASH, WIZARD_PATH, WIZARD_TITLE } from "./words.js";

// What the wizard's checklist offers, in its order, with what each choice does and where the same thing is done by itself.
// `needsDotfiles` marks the ones that stop to ask for your dotfiles folder when it is not on this machine.
const CHOICES = [
  { emoji: "🐍", title: "Install the StackOps commands", does: "Installs StackOps with uv, so its commands work in every terminal.", where: ["#/machine/update", "Update StackOps"] },
  { emoji: "📥", title: "Install the basics", does: "A package manager first, then git and bun.", where: ["#/apps", "Apps"] },
  { emoji: "⚡", title: "Install terminal essentials", does: "The command-line apps StackOps builds on, as one bundle.", where: ["#/apps", "Apps"] },
  { emoji: "🐚", title: "Set up the shell profile", does: "Adds StackOps' line to your shell profile, then copies the packaged settings of every tool into place, over what is there.", where: ["#/sessions/shell-profile", "Shell profile"] },
  { emoji: "🔗", title: "Link the packaged settings", does: "Copies the packaged settings to this machine and points each tool at them, replacing the settings a tool has now.", where: [ASSETS_HASH, "Packaged files"] },
  { emoji: "🧷", title: "Link your own dotfiles", does: "Points each tool at the file your dotfiles list names for it, replacing what is there.", where: ["#/dotfiles", "Dotfiles"], advanced: true, needsDotfiles: true },
  { emoji: "📚", title: "Retrieve repositories", does: "Clones every project on your projects list.", where: ["#/projects", "Projects"], advanced: true, needsDotfiles: true },
  { emoji: "💾", title: "Retrieve data", does: "Downloads everything on your backup list from your cloud storage.", where: ["#/data", "Data"], advanced: true, needsDotfiles: true },
];

// The full guided route, `devops config interactive`. A sheet and not a page: there is nothing to explore, only what the wizard offers and one
// button. The wizard itself runs in the activity panel, because it is a checklist in a terminal.
export function open({ activity }) {
  const sheet = openSheet({ label: WIZARD_TITLE, wide: true });
  const note = h("div");
  sheet.body.append(
    h(
      "header",
      { class: "tool-head" },
      emojiTile("🤖", WIZARD_PATH, 56),
      h("div", {}, h("span", { class: "overline", text: "Settings" }), h("h1", { text: WIZARD_TITLE }), h("p", { text: "One guided run for a new machine. It opens a checklist in the activity panel with nothing ticked. Tick what you want with Space, press Enter, and it does those in turn." })),
    ),
    note,
    h(
      "ol",
      { class: "settings-wizard-list" },
      CHOICES.map((choice) =>
        h(
          "li",
          {},
          emojiTile(choice.emoji, choice.title, 38),
          h("div", {}, h("strong", {}, choice.title, choice.advanced && h("em", { text: "Advanced" })), h("p", { text: choice.does })),
          h("a", { class: "settings-step-link", href: choice.where[0], title: "Do only this, on its own page" }, h("span", { text: choice.where[1] }), icon("arrow", 13)),
        ),
      ),
    ),
    h("p", { class: "dim settings-wizard-foot", text: "Each page named on the right does one of these by itself, with more to see before it runs. When the wizard ends it loads your shell profile again." }),
  );

  // Where the dotfiles folder stands decides what the three advanced choices do first, so the sheet says it once that is known.
  const paintNote = ({ value }) => {
    if (!value || !note.isConnected) return;
    note.replaceChildren(
      value.dotfiles_folder
        ? callout({ tone: "", title: "Your dotfiles folder is on this machine", text: "The three advanced choices read their lists from it." })
        : callout({ tone: "warn", title: "Your dotfiles folder is not on this machine yet", text: "The three advanced choices need it. Tick one and the wizard first offers to fetch the folder from another machine, over the local network or SSH." }),
    );
  };
  sheet.closed.then(setup.watch(note, paintNote));
  paintNote(setup.reading);
  setup.sync();

  let starting = false;
  sheet.foot.hidden = false;
  sheet.foot.append(
    agentButton(activity, { commands: [WIZARD_PATH] }),
    h("span", { class: "dim", text: "Nothing changes until you tick something there." }),
    h("span", { class: "spacer" }),
    button({ label: "Close", tone: "ghost", onclick: () => sheet.close() }),
    button({
      label: "Start the wizard", glyph: "play", tone: "primary",
      async onclick() {
        if (starting) return;
        starting = true;
        try {
          await activity.start({ title: WIZARD_TITLE, emoji: "🤖", arguments: WIZARD_PATH.split(" "), interactive: true, reveal: true, wide: true });
          sheet.close();
        } catch (error) {
          starting = false;
          toast(error.message);
        }
      },
    }),
  );
}
