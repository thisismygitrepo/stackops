StackOps introduction
=====================

This video explains StackOps commands with synthetic narration and captions.
The diagrams use public documentation examples and invented project names.
They illustrate the commands without running them.

Edit the scene fields below, then render on macOS with Node.js, the Xcode command
line tools, and ``rsvg-convert`` installed::

    cd /path/to/stackops
    node docs/video/render.mjs

The renderer reads this file. ``Say`` fields supply speech and captions.
``Card`` fields use ``title | detail``. ``Title`` uses ``|`` for a line break.
Git tracks this file and the rendering tools. It ignores the output at
``docs/video/stackops-concept.mp4``. The renderer writes temporary files to
``.ai/tmp_scripts/stackops-video/`` and needs no personal configuration.

Scene 01. What StackOps does
---------------------------

:Layout: intro
:Eyebrow: OVERVIEW
:Title: StackOps
:Subtitle: Install developer tools and manage their configuration.
:Card: Packages | Install tools by name
:Card: Configuration | Copy or link settings
:Card: Repositories | Clone listed projects
:Card: Data | Back up named files
:Card: Terminals | Open saved layouts
:Card: Coding agents | Run prompts in parallel
:Say: StackOps is a Python package with commands for setting up a development machine.
:Say: It can install tools, sync configuration files, and open terminal sessions from a saved layout.
:Source: README.md; docs/index.md

Scene 02. Install tools
----------------------

:Layout: packages
:Eyebrow: PACKAGES
:Title: Install developer|tools
:Subtitle: Use devops install to select a tool or package group.
:Card: By name | Install a program such as Television
:Card: From a menu | Select the programs to install
:Card: By group | Install a set such as the search tools
:Command: devops install tv --source library
:Footnote: This installs Television. Available installers depend on the operating system.
:Say: This command installs Television, a terminal search tool, using the installer included with StackOps.
:Say: You can choose other programs by name, select them from a menu, or install a package group.
:Source: docs/quickstart.md; docs/guide/packages.md; docs/api/jobs/installer.md

Scene 03. Sync configuration files
---------------------------------

:Layout: config
:Eyebrow: CONFIGURATION
:Title: Sync configuration|files
:Subtitle: A mapping records the source file and its destination.
:Card: Stored file | settings/editor.toml
:Card: Sync method | Copy the file or create a symlink
:Card: Destination | ~/.config/editor/config.toml
:Command: devops config sync --help
:Footnote: Illustrative paths. Select the files, direction, sync method, and conflict policy.
:Say: A configuration mapping records a file and where it belongs on your machine.
:Say: StackOps can copy the file or create a symlink.
:Say: You select the files and decide what happens if a destination already exists.
:Source: docs/guide/configuration.md; docs/quickstart.md; docs_fragments/cli/devops/_config.md

Scene 04. Open a saved terminal layout
-------------------------------------

:Layout: terminal
:Eyebrow: TERMINALS
:Title: Open a saved|terminal layout
:Subtitle: layout.json stores tab names, directories, and commands.
:Card: editor | hx .
:Card: server | python -m http.server 8000
:Card: shell | bash
:Command: terminal run layout.json --backend tmux
:Footnote: This example requires a layout.json file and tmux.
:Say: Put the tab names, working directories, and commands in a layout file.
:Say: This example opens an editor, a local server, and a shell in tmux.
:Say: Run the same layout when you need those terminals again.
:Source: docs/cli/terminal.md; docs/api/cluster/layouts.md; docs/api/cluster/sessions.md

Scene 05. Repositories and data
------------------------------

:Layout: movement
:Eyebrow: REPOSITORIES AND DATA
:Title: Repositories and data
:Subtitle: Separate commands for repository lists, backups, and direct transfers.
:Card: devops repos | Clone the projects listed in repos.json
:Card: devops data | Back up files registered by name
:Card: cloud | Copy files between a source and destination
:Command: cloud copy ./report.pdf remote:reports/report.pdf
:Footnote: Example paths. The cloud command requires a configured remote.
:Say: A repos.json file lists the repositories to clone and where to put them.
:Say: For backups, register files or directories by name, then sync those entries to your configured cloud storage.
:Say: For a direct transfer, cloud copy takes a source and destination.
:Source: docs_fragments/cli/devops/_repos.md; docs/guide/data-sync.md; docs/cli/cloud.md

Scene 06. Coding agents
----------------------

:Layout: agents
:Eyebrow: CODING AGENTS
:Title: Set up and run|coding agents
:Subtitle: Configure supported agents and run prompts with context.
:Card: agents add-config | Create agent configuration files
:Card: agents run-prompt | Run a prompt with supplied context
:Card: agents parallel | Prepare jobs and collect outputs
:Command: agents parallel --help
:Footnote: Check each command's help for supported agents and backends.
:Say: The agents commands install configuration, skills, and MCP server entries for supported coding agents.
:Say: You can run a prompt with a context file, or prepare parallel jobs and collect their outputs.
:Source: docs/cli/agents.md; README.md

Scene 07. File commands
----------------------

:Layout: helpers
:Eyebrow: FILE COMMANDS
:Title: Search and run files
:Subtitle: StackOps also includes these standalone commands.
:Card: seek | Search files, text, and symbols
:Card: preview | Open a file in a preview tool
:Card: fire | Run files, functions, notebooks, and apps
:Card: utils | Merge PDFs and inspect databases
:Say: Seek searches files, text, and symbols.
:Say: Preview opens files in a preview tool, such as VisiData for a CSV file.
:Say: Fire runs files, functions, notebooks, and apps.
:Say: Utils includes commands to merge PDFs and inspect local databases.
:Source: docs/cli/seek.md; docs/cli/preview.md; docs/cli/fire.md; docs/cli/utils.md

Scene 08. Install StackOps
-------------------------

:Layout: closing
:Eyebrow: INSTALLATION
:Title: Install StackOps
:Subtitle: Requires uv. The documentation includes installation instructions.
:Command: uv tool install --upgrade --python 3.14 stackops
:Command: stackops --help
:Footnote: thisismygitrepo.github.io/stackops/
:Say: Install StackOps with uv, then run StackOps help to see the available commands.
:Say: Each command has its own help page. The documentation includes setup instructions and examples.
:Source: README.md; docs/installation.md; docs/quickstart.md

Sources
-------

The scene sources identify the documentation behind each example. The package
README, guides, CLI references, and API documentation describe more commands
than this introduction covers. Examples follow this checkout. Installed
releases can differ.

The data-sync guide matches the current implementation in
``src/stackops/scripts/python/helpers/helpers_devops/cli_backup_retrieve.py``.
Data sync performs transfers. The older CLI fragment that describes printing
scripts is stale.
