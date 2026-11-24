import { h, icon, toast } from "/assets/scripts/dom.js";
import { createCombo } from "../../../combo.js";
import { confirmAction } from "../../../overlays.js";
import { button } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { quietRun } from "../model.js";

// A step kept in the defaults file offers nothing while that file fails its check: the CLI refuses to write to it until it is fixed.
const UNREAD = "This cannot be read or set while the StackOps defaults file fails its check.";
const pageLink = (href, label) => h("a", { class: "settings-step-link", href }, h("span", { text: label }), icon("arrow", 13));

// The default coding agent, picked from the list the CLI takes and saved with one more click. The box and the button are made once and
// outlive each reading, so a pick that is not saved yet stays. `propose` is for a name handed over by whoever opened the tool.
export function createAgentPicker({ activity }) {
  let current = { agent: "", agent_in_use: "", agents: [] };
  let picked = "";
  const combo = createCombo({
    label: "Default coding agent", readOnly: true, emptyText: "No agents to choose from",
    suggest: () => current.agents.map((name) => ({ value: name, label: name, hint: name === current.agent ? "Your choice now" : name === current.agent_in_use ? "In use now, not chosen" : "" })),
    onPick(option) {
      picked = option.value;
      sync();
    },
  });
  const save = button({ label: "Save", small: true, tone: "primary", onclick: store });
  save.dataset.action = "main";

  function sync() {
    combo.input.placeholder = current.agent ? `Yours: ${current.agent}` : `Default: ${current.agent_in_use}`;
    combo.setValue(picked);
    save.disabled = picked === "" || picked === current.agent;
  }

  async function store() {
    const name = picked;
    save.disabled = true;
    try {
      if (await quietRun(activity, { title: `Make ${name} the default agent`, emoji: "🤖", runArguments: ["devops", "config", "setup", "agent", "--agent", name] })) {
        picked = "";
        toast(`${name} is now the default coding agent.`, "info");
      }
    } catch (error) {
      toast(error.message);
    }
    sync();
  }

  return {
    element: h("div", { class: "settings-step-pick" }, combo.element, save),
    paint(value) {
      current = value;
      sync();
    },
    propose(name) {
      picked = name;
      sync();
    },
  };
}

// What one step says and offers: `state` is where it stands, `about` what it is for, `problem` why a list cannot be read, `actions` its buttons.
// The first button of a step carries `data-action="main"`, which is where the keyboard lands when the step is opened by name.
export function describeStep(step, { value, done, activity, tools, agentPicker }) {
  const unread = done[step.id] === null;
  const main = (control) => {
    control.dataset.action = "main";
    return control;
  };
  const guided = (label, title, hint) =>
    main(
      button({
        label, small: true, tone: done[step.id] ? "plain" : "primary", title: hint,
        onclick: () => activity.start({ title, emoji: step.emoji, arguments: step.path.split(" "), interactive: true, reveal: true }).catch((error) => toast(error.message)),
      }),
    );
  const listed = (list, word, empty, none) => (list.problem ? "" : !list.exists ? none : list.count === 0 ? empty : `${plural(list.count, word)} on your list.`);

  switch (step.id) {
    case "cloud":
      return {
        about: "Where backups go when a command names no cloud. StackOps keeps the name of one of your rclone remotes, and the sign-in stays with rclone.",
        state: unread ? UNREAD : value.cloud ? `Backups go to ${value.cloud}.` : "No cloud chosen. Backing up asks which one every time.",
        actions: unread ? [] : [main(button({ label: value.cloud ? "Change" : "Choose a cloud", small: true, tone: value.cloud ? "plain" : "primary", onclick: () => tools.open(step.path) })), pageLink("#/data", "Data")],
      };
    case "email": {
      const half = value.email_profile || value.email_address;
      return {
        about: "The address StackOps writes to when a long job ends, and the mail account it sends from.",
        state: unread ? UNREAD : done.email ? `Notifications go to ${value.email_address}, sent through ${value.email_profile}.` : half ? "Half set up: it needs both a mail account and an address." : "Not set up.",
        actions: unread
          ? []
          : [
              guided(done.email ? "Change" : "Set up email", "Set up email notifications", "Asks its questions in the activity panel. A mail password is typed there and stays hidden."),
              button({ label: "All options", small: true, tone: "ghost", title: "The command's own form: name a mail account and an address without the questions", onclick: () => tools.open(step.path, { plain: true }) }),
            ],
      };
    }
    case "agent":
      return {
        about: "The coding agent that agent commands start when you name none.",
        state: unread ? UNREAD : value.agent ? `${value.agent} is your choice.` : `Not chosen. Commands use ${value.agent_in_use} until you pick one.`,
        actions: unread ? [] : [agentPicker.element, pageLink("#/agents", "Agents")],
      };
    case "multiplexer": {
      const role = (chosen, used, what) => (chosen ? `${used} for ${what} is your choice` : `${used} for ${what} is the built-in default`);
      return {
        about: "The program that holds your terminal sessions, and the one agents are looked for in.",
        state: unread ? UNREAD : `${role(value.session_multiplexer, value.session_multiplexer_in_use, "sessions")}; ${role(value.agent_multiplexer, value.agent_multiplexer_in_use, "agents")}.`,
        actions: unread ? [] : [main(h("a", { class: `btn small ${done.multiplexer ? "plain" : "primary"}`, href: "#/sessions/multiplexer" }, h("span", { text: done.multiplexer ? "Change" : "Choose" })))],
      };
    }
    case "data":
      return {
        about: "Files and folders StackOps keeps a copy of in your cloud storage.",
        state: listed(value.backups, "backup", "Your backup list is empty.", "No backup list yet."), problem: value.backups.problem,
        actions: [guided("Add one, step by step", "Add a backup, step by step", "Asks what to back up and where, in the activity panel"), pageLink("#/data", "Data")],
      };
    case "dotfiles":
      return {
        about: "Settings files of your tools, kept in your dotfiles folder and linked back to where each tool looks.",
        state: listed(value.dotfiles, "file", "Your dotfiles list is empty.", "No dotfiles list yet."), problem: value.dotfiles.problem,
        actions: [guided("Add one, step by step", "Add a dotfile, step by step", "Asks which file to take in, in the activity panel"), pageLink("#/dotfiles", "Dotfiles")],
      };
    case "layouts": {
      const install = async (overwrite) => {
        const sure = !overwrite || (await confirmAction({
          title: "Replace your layouts?", confirm: "Replace them", tone: "danger",
          body: `Your layouts file${value.layouts.count ? ` and the ${plural(value.layouts.count, "layout")} in it` : ""} are overwritten with the starter layouts StackOps ships. There is no undo.`,
        }));
        if (!sure) return;
        const went = await quietRun(activity, { title: "Install the starter layouts", emoji: step.emoji, runArguments: [...step.path.split(" "), ...(overwrite ? ["--overwrite"] : [])] }).catch((error) => toast(error.message));
        if (went) toast("The starter layouts are in your layouts file.", "info");
      };
      return {
        about: "Ready-made terminal workspaces to start from. Edit them or add your own on Sessions.",
        state: value.layouts.problem ? "" : value.layouts.exists ? `${plural(value.layouts.count, "layout")} in your file.` : "No layouts file yet.", problem: value.layouts.problem,
        actions: [
          value.layouts.exists
            ? main(button({ label: "Replace with the starters", small: true, title: "Overwrites your layouts file. Asks first.", onclick: () => install(true) }))
            : main(button({ label: "Install starter layouts", small: true, tone: "primary", onclick: () => install(false) })),
          pageLink("#/sessions", "Sessions"),
        ],
      };
    }
    default:
      return {
        about: "Logins and keys StackOps can hand to the commands that need them. Only you can read the file.",
        state: value.logins.problem ? "" : value.logins.exists ? `${plural(value.logins.count, "login")} saved.` : "No vault yet.", problem: value.logins.problem,
        actions: [
          value.logins.exists
            ? main(h("a", { class: "btn small plain", href: "#/vault" }, h("span", { text: "Open the vault" })))
            : guided("Create it, step by step", "Create the vault", "Asks for a first login in the activity panel. What you type for a secret stays hidden."),
        ],
      };
  }
}
