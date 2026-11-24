const WIZARD_COMMAND = "devops config interactive";
const FETCHERS = /\b(curl|wget|irm|iwr|Invoke-WebRequest|Invoke-RestMethod)\b/;
const unique = (items) => [...new Set(items)];

// What a setup script would do, read off its text without running anything: what it downloads, which files it loads, the folders it adds to
// the program search path, the commands it defines, the programs it switches on, and what it ends on. It reads bash, zsh and PowerShell the
// way StackOps' own scripts are written, and says nothing about a line it does not recognise: the text itself is shown beside this.
export function explainScript(text) {
  const lines = text.split("\n").map((line) => line.trim()).filter((line) => line !== "" && !line.startsWith("#"));
  const fetched = unique(lines.filter((line) => FETCHERS.test(line)).flatMap((line) => line.match(/https?:\/\/[^\s"'<>)]+/g) ?? []));
  const loaded = unique(lines.flatMap((line) => line.match(/^(?:\[[^\]]*\]\s*&&\s*)?(?:\.|source)\s+"?([^\s"<(][^\s"]*)/)?.slice(1) ?? []));
  // The folders of a path helper are written one to a line, each in quotes, after the helper's name.
  const pathFolders = /add_to_path|\bPATH\b/.test(text) ? lines.filter((line) => /^"[^"]+"\s*\\?$/.test(line)).length : 0;
  const commands = [];
  lines.forEach((line, index) => {
    // A loop that makes one alias for each name it is given.
    const loop = line.match(/^for\s+(\w+)\s+in\s+([^;]+);\s*do$/);
    if (loop && lines.slice(index + 1, index + 3).some((next) => next.includes(`alias "$${loop[1]}=`))) commands.push(...loop[2].trim().split(/\s+/));
    const aliases = line.match(/^alias\s+(.+)/);
    if (aliases) commands.push(...[...aliases[1].matchAll(/(?:^|\s)([\w-]+)=/g)].map((match) => match[1]));
    const made = line.match(/^(?:function\s+([\w-]+)|([\w-]+)\s*\(\)\s*\{|Set-Alias\s+(?:-Name\s+)?([\w-]+))/);
    if (made) commands.push(made[1] ?? made[2] ?? made[3]);
  });
  const last = lines.at(-1) ?? "";
  return {
    lineCount: text.replace(/\n$/, "").split("\n").length,
    fetched, loaded, pathFolders,
    // A plain lower-case name is something to type; the rest are the script's own helpers.
    commands: unique(commands.filter((name) => /^[a-z][a-z0-9]*$/.test(name))),
    switchedOn: unique(lines.flatMap((line) => line.match(/\$\((\w+) init\b/)?.slice(1) ?? [])),
    endsWith: /^(devops|stackops|cloud|agents|terminal)\s/.test(last) ? last : "",
    startsWizard: last === WIZARD_COMMAND,
  };
}
