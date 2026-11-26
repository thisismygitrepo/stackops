import { state } from "/assets/scripts/state.js";
import { SPACES } from "./catalog.js";
import { blurbOf, friendlyText, titleOf } from "./words.js";

// A place is what an "Ask an agent" button stands beside (agent_ask.js), and all of it is optional:
//   title     what the place is called on the page; left out, it is the name of the first command
//   about     one or two sentences on what the place is; left out, it is what the first command says of itself
//   commands  the command paths the place is built on, without the leading `stackops`; a group stands for everything in it
//   settings  the kind of StackOps settings file behind it, as `devops config` names it
//   files     other files behind it, each { label, path }
//   notes     what else is worth knowing before the first question: what is selected, what the page says is wrong
//   ideas     requests to start from, offered in the box; one that ends in "…" is to be finished by the person
const RULES = [
  "For a question, answer in plain words with the short answer first, and name the page of the web UI that shows it when there is one.",
  "For a change, say in a sentence what you will change and where, then make it: with a StackOps command where one does the job, by editing the file where none does. Leave alone whatever the request is not about.",
  "After a change, run the command that checks what you changed (most settings files have a `validate`) and say what it reported. The page they came from reads everything again when they put this panel away.",
  "Ask before anything that deletes or overwrites their data, sends something off this machine, or costs money.",
  "Never open, print or copy a password, token or key. Name a secret; do not show it.",
];

const known = (place) => (place.commands ?? []).map((path) => state.nodes.get(path)).filter(Boolean);

// What the box and the task call a place, and where in the app it is: the page in the address, then the place when it is not that whole page.
export function describePlace(place) {
  const [first] = known(place);
  const title = place.title ?? (first ? titleOf(first) : "StackOps");
  const about = place.about ?? (first ? blurbOf(first) : "");
  const address = location.hash.replace(/^#\/?/, "");
  const page = (SPACES.find((space) => space.id === address.split("/")[0]) ?? SPACES[0]).title;
  return { title, about, where: page.toLowerCase() === title.toLowerCase() ? page : `${page} › ${title}`, address: `#/${address}` };
}

// What the agent is told before the person's own words: where the button was pressed and what lies behind that place, then how to find out
// about everything else. The place narrows what a short request means; StackOps' own guide is what lets the agent answer one about any
// other part of the app.
export function briefingFor(place) {
  const { about, where, address } = describePlace(place);
  const { boot, settings } = state;
  const list = (heading, rows) => (rows.length > 0 ? [heading, ...rows.map((row) => `- ${row}`)] : []);
  return [
    `You were started by the "Ask an agent" button in the StackOps web UI (\`stackops webui\`). The person looking at that page typed the request under "# Prompt". They would rather ask you than edit a settings file or learn a command, so explain what they ask about, or make the change for them. This is a live chat in their browser: they read what you write and can answer or ask more.`,
    "",
    "## Where they pressed the button",
    `Place: ${where} (address ${address} in the web UI)`,
    ...(about ? [`What it is: ${about}`] : []),
    ...list("Commands behind it:", known(place).map((node) => `\`stackops ${node.path}\`${node.kind === "command" ? "" : " (a group; `--help` lists what is in it)"}: ${friendlyText(node.summary)}`)),
    ...(place.settings ? [`Settings behind it: the \`${place.settings}\` settings file. \`stackops devops config path ${place.settings}\` prints where it is, and \`stackops devops config validate ${place.settings}\` checks it.`] : []),
    ...list("Files behind it:", (place.files ?? []).map((file) => `${file.label}: ${file.path}`)),
    ...list("On the page now:", place.notes ?? []),
    "",
    `Read a short or vague request ("add one", "why is this red?") as being about this place. A question about any other part of StackOps is just as welcome.`,
    "",
    "## Finding your way",
    "For anything the lines above do not already answer, and before any change, run `stackops --skill`. It prints StackOps' guide for agents and the folder of its references: what each command does, which settings file or schema owns a behaviour, and how to change one. `stackops <command> --help` describes any command, and many print JSON with `--json`.",
    `This machine is ${boot.host} (${boot.platform}), with StackOps ${boot.version}. You are in ${settings.workingDirectory}, the folder the web UI works in.`,
    "",
    "## How to work",
    ...RULES.map((rule) => `- ${rule}`),
  ].join("\n");
}
