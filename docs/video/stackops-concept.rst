StackOps: Digital Life Manager
==============================

This introduction follows the original Digital Life Manager presentation in
the README and homepage at ``41aae8d08^``, using the user's current wording:
"99% of your digital footprint." The story centers on that breadth and the
transformation from a bare machine to a familiar digital life.

The before/after images are the original README assets. Diagrams illustrate
the concept; they are not recordings of an automated setup. The one-command,
five-minute line presents the original setup goal. Narration uses OpenAI's
``gpt-live-1`` model with the AI-generated Marin voice.

Render on macOS with Node.js, uv, the Xcode command line tools,
``rsvg-convert``, and FFmpeg with ``libx264`` on your PATH. Set ``FFMPEG`` to an
executable path if needed. Export ``OPENAI_API_KEY`` before rendering::

    cd /path/to/stackops
    node docs/video/render.mjs

``uv`` manages the narrator's isolated Python 3.13 dependencies from its script
metadata. Each ``Focus`` / ``Say`` pair is one visual beat and its spoken
caption. ``Card`` fields use ``title | detail``; ``|`` in other text makes a
line break.

The output is ``docs/video/stackops-concept-live.mp4`` with matching VTT
captions. MP4 files are ignored
by Git. Intermediate
artwork, audio, timing metadata, and previews go under
``.ai/tmp_scripts/stackops-video/``. Narration sends the script to OpenAI.

Scene 01. Your digital life
--------------------------

:Layout: footprint
:Eyebrow: DIGITAL LIFE MANAGER
:Title: StackOps
:Subtitle: 99% of your|digital footprint.
:Opening: Your stack is awesome,|but you need a way to manage it.
:Card: Applications | The software you use
:Card: Configuration | Public and private settings
:Card: Secrets | Credentials and passwords
:Card: Data | Your files and directories
:Card: Code | Your repositories
:Card: Processes | The work you run
:Takeaway: Your digital life, managed together.
:Focus: opening
:Say: Your stack is awesome, but you need a way to manage it.
:Focus: identity
:Say: StackOps is your OS-agnostic digital life manager. It covers 99% of your digital footprint.
:Focus: applications
:Say: Applications.
:Focus: configuration
:Say: Configuration.
:Focus: secrets
:Say: Your secrets.
:Focus: data
:Say: Your files.
:Focus: code
:Say: Your repositories.
:Focus: processes
:Say: Processes.
:Focus: together
:Say: All wrapped into one solution.
:Source: User's current 99% wording; README.md at 41aae8d08^; docs/index.md at 41aae8d08^

Scene 02. A fresh machine, your familiar world
--------------------------------------------

:Layout: transformation
:Eyebrow: THE PROMISE
:Title: A fresh machine.|Ten years of making it yours.
:Subtitle: From a bare system to your familiar digital life.
:Takeaway: Bring years of customization to a fresh machine in minutes.
:Focus: bare
:Say: Start with a fresh, bare machine.
:Focus: familiar
:Say: Now bring back the environment you've spent ten years making your own.
:Focus: minutes
:Say: That's the goal: one command, five minutes, and your familiar digital life ready to use.
:Source: README.md at 41aae8d08^; docs/index.md at 41aae8d08^; docs/assets/before.png; docs/assets/after.png

Scene 03. While casually inspecting a machine
--------------------------------------------

:Layout: store
:Eyebrow: IN THE STORE
:Title: Literally.
:Statement: You can install and configure your entire dev environment while casually inspecting a machine in the store.
:Payoff: By the time they notice something is unusual, we are done.
:Note: (This config is based on public setup, and ignores private setup and files.)
:Takeaway: Your dev environment, ready while you browse.
:Focus: browsing
:Say: Literally, you can install and configure your entire dev environment while casually inspecting a machine in the store.
:Focus: done
:Say: By the time they notice you are doing something unusual, your setup is done.
:Focus: public
:Say: This config is based on public setup, and ignores private setup and files.
:Source: AI-generated JB Hi-Fi scene (GPT Image 2.5 Sunburst), option 01 with cmatrix; user-provided wording; docs/assets/stackops.jpeg

Scene 04. The stack you are comfortable with
-------------------------------------------

:Layout: familiar
:Eyebrow: YOUR STACK
:Title: The stack you are|comfortable with.
:Subtitle: StackOps doesn't reinvent the wheel.
:Role: Configurator
:Role: Package manager
:Role: Dotfile manager
:Role: Data sync solution
:Role: Digital life manager
:Platform: Linux
:Platform: macOS
:Platform: Windows
:Takeaway: A cross-platform approach to managing your digital life.
:Focus: intro
:Say: StackOps doesn't reinvent the wheel. It glues together the best open-source tools.
:Focus: configurator
:Say: It's a configurator,
:Focus: package-manager
:Say: a package manager,
:Focus: dotfile-manager
:Say: a dotfile manager,
:Focus: data-sync
:Say: a data sync solution,
:Focus: digital-life
:Say: a digital life manager.
:Focus: platforms
:Say: One experience, across all operating systems.
:Source: User-provided description; docs/index.md at 41aae8d08^; README.md at 41aae8d08^; docs/installation.md

Scene 05. The command hierarchy
-------------------------------

:Layout: sunburst
:Eyebrow: THE COMMAND HIERARCHY
:Title: One CLI.|A command hierarchy.
:Takeaway: Setup, maintenance, and everyday work under one CLI.
:Focus: overview
:Say: One CLI covers setup, cloud, terminals, agents, and everyday tools.
:Focus: devops
:Say: DevOps handles installation, configuration, networking, and security.
:Focus: config
:Say: Restore public and private settings, dotfiles, and terminal profiles.
:Focus: back
:Say: Back up, sync, and retrieve your repositories and data.
:Focus: root
:Say: Launch workspaces and orchestrate everyday processes.
:Source: src/stackops/scripts/python/graph/cli_graph.json; animated command hierarchy; docs/guide/configuration.md; docs/guide/data-sync.md; docs/cli/fire.md; docs/cli/terminal.md; docs/cli/agents.md

Scene 06. Your digital life, sorted
----------------------------------

:Layout: closing
:Eyebrow: STACKOPS
:Title: Your digital life.|Sorted.
:Subtitle: StackOps · Digital Life Manager
:Recipe: Think of it as a Dockerfile.
:Recipe-detail: A recipe for reproducing your computer.
:Takeaway: 99% of your digital footprint. One solution.
:Link: thisismygitrepo.github.io/stackops/
:Focus: life
:Say: That's StackOps. Your digital life, sorted.
:Focus: recipe
:Say: Think of it as a Dockerfile: a recipe for how to reproduce your computer.
:Source: User's current 99% wording and Dockerfile analogy; README.md at 41aae8d08^; docs/index.md at 41aae8d08^
