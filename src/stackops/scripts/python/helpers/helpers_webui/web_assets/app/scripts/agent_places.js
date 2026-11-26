// What "Ask an agent" says of each page it stands on (agent_brief.js describes a place). The words are for the agent, so they say what a page is
// made of and where its settings are kept, which a page's own heading does not.
const SECRETS_NOTE = "The vault files hold passwords, tokens and keys. Do not open them or print what they hold. Work through `stackops devops vault` commands that report names and counts, and when a value has to be typed, tell the person which command to run themselves.";

export const PLACES = {
  home: {
    title: "Home", commands: ["devops config", "devops self status"],
    about: "How this machine stands at a glance, and StackOps' own settings: the settings files it reads, the guided setup, the setup scripts and the files it ships.",
    ideas: ["What is not set up on this machine yet?"],
  },
  apps: {
    title: "Apps", commands: ["devops software"], settings: "software",
    about: "The catalog of software StackOps can install, what is installed here and what has a newer version. A person's own additions live in their catalog file.",
    ideas: ["Add an app to my catalog: …", "Install …"],
  },
  projects: {
    title: "Projects", commands: ["devops repos"], settings: "repos",
    about: "The repositories StackOps tracks on this machine: where each lives, whether it has changes, and how it is synced, through its Git remotes or, for a guarded one, as an encrypted copy in cloud storage.",
    ideas: ["Add the repository at … to my projects"],
  },
  sessions: {
    title: "Sessions", commands: ["terminal", "devops config terminal"], settings: "layouts",
    about: "Saved layouts (named sets of tabs and panes that start in one go), the terminal sessions running now, and how the terminal is set up: multiplexer, shell profile and themes.",
    ideas: ["Make a layout that opens …"],
  },
  scripts: {
    title: "Scripts", commands: ["devops scripts"],
    about: "Small programs kept to hand: the person's own, this project's, and the ones StackOps ships. Each can be read, run and edited.",
    ideas: ["Write me a script that …"],
  },
  dotfiles: {
    title: "Dotfiles", commands: ["devops config dotfiles"], settings: "dotfiles",
    about: "Settings files kept in one dotfiles folder and linked or copied to where each program reads them. A list, the mapper, says which file belongs where.",
    ideas: ["Start managing my settings for …"],
  },
  data: {
    title: "Data", commands: ["devops data", "cloud"], settings: "data",
    about: "The files and folders StackOps backs up to cloud storage through rclone, kept on a backup list, and tools to encrypt, copy, sync and mount cloud storage.",
    ideas: ["Back up the folder … to my cloud"],
  },
  network: {
    title: "Network", commands: ["devops network"],
    about: "This machine's addresses, ways to share files and terminals with other devices, and remote access: SSH, port forwards, Wi-Fi, Cloudflare WARP and tunnels.",
    ideas: ["Let my other machine sign in here over SSH"],
  },
  machine: {
    title: "Machine", commands: ["utils machine", "devops self"],
    about: "What this computer is and what runs on it: processes, startup programs, disks and mounts, windows, environment variables, disk cleanup and StackOps' own updates.",
    ideas: ["What is using the most memory right now?"],
  },
  security: {
    title: "Security", commands: ["devops security", "devops data encrypt", "devops data decrypt"],
    about: "VirusTotal scans of the apps installed here and of single files, the record of past scans, and tools to export a scan, install from one, and lock files with a password or a GPG key. A scan sends files to VirusTotal and uses the account's quota, so never start one unasked.",
    ideas: ["What does the last scan say I should worry about?"],
  },
  vault: {
    title: "Vault", commands: ["devops vault"], notes: [SECRETS_NOTE],
    about: "The logins, keys and tokens StackOps keeps in a vault file, the person's own and one per project, and its bridge to Bitwarden.",
    ideas: ["How do I load a secret into a terminal?"],
  },
};

// What each kind of settings file holds and the commands that read it, by the name `devops config` gives the kind. The vault's kind is
// not here: `filePlace` gives it the Vault page's place.
const SETTINGS = {
  config: ["StackOps' own defaults: the cloud, coding agent, multiplexers and email address a command uses when none is named.", "devops config setup"],
  layouts: ["The saved terminal layouts: named sets of tabs and panes, each pane with the folder it opens in and the command it starts.", "terminal"],
  dotfiles: ["The dotfiles list, or mapper: which file in the dotfiles folder belongs where on a machine, and whether it is linked or copied there.", "devops config dotfiles"],
  data: ["The backup list: the files and folders backed up to cloud storage, in groups, with how each one is packed and encrypted.", "devops data"],
  repos: ["The project list: the repositories tracked on this machine and how each one is synced.", "devops repos"],
  software: ["The person's own app catalog: installers added to the ones StackOps ships.", "devops software"],
  prompts: ["The saved prompts: named pieces of context and instructions that are handed to coding agents.", "agents run-prompt"],
  mcp: ["The MCP server catalog: the servers that can be installed into coding agents.", "agents add-mcp"],
};

// The place of a file a page offers to edit, from what its Edit button is given (space_kit.js). `more` adds what the page knows beyond that,
// such as what its check found wrong.
export function filePlace({ title, kind, path }, more = {}) {
  const files = path ? [{ label: title, path }] : [];
  const named = { title: title.charAt(0).toUpperCase() + title.slice(1), files };
  // What a vault file holds is not for an agent to read: its place names no file and passes on nothing the page says of it, only the Vault's own words.
  if (kind === "secrets") return { ...PLACES.vault, title: named.title, ideas: ["What is wrong with my vault file, and how do I put it right myself?"] };
  if (!Object.hasOwn(SETTINGS, kind)) return { ...named, ...more };
  const [about, reader] = SETTINGS[kind];
  return { ...named, about, settings: kind, commands: [reader, "devops config edit"], ...more };
}
