StackOps: Digital Life Manager
==============================

This introduction follows the original Digital Life Manager presentation in
the README and homepage at ``41aae8d08^``, using the user's current wording:
"99% of your digital footprint." The story centers on that breadth and the
transformation from a bare machine to a familiar digital life.

The before/after images are the original README assets. Diagrams illustrate
the concept; they are not recordings of an automated setup. The one-command,
five-minute line presents the original setup goal. Narration uses Kokoro's
synthetic Sarah voice.

Render on macOS with Node.js, uv, the Xcode command line tools,
``rsvg-convert``, and FFmpeg with ``libx264`` on your PATH. Set ``FFMPEG`` to an
executable path if needed. Download the public Kokoro model assets once::

    cd /path/to/stackops
    mkdir -p .ai/tmp_scripts/stackops-video
    curl -fL https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx -o .ai/tmp_scripts/stackops-video/kokoro-v1.0.onnx
    curl -fL https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin -o .ai/tmp_scripts/stackops-video/voices-v1.0.bin
    node docs/video/render.mjs

``uv`` manages the narrator's isolated Python 3.13 dependencies from its script
metadata. Each ``Focus`` / ``Say`` pair is one visual beat and its spoken
caption. ``Card`` fields use ``title | detail``; ``|`` in other text makes a
line break.

The outputs are ``docs/video/stackops-concept.mp4`` and matching
``stackops-concept.vtt`` captions. The MP4 is ignored by Git. Intermediate
artwork, audio, timing metadata, and previews go under
``.ai/tmp_scripts/stackops-video/``. Rendering uses no personal configuration.

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
:Say: The applications you use.
:Focus: configuration
:Say: The way you configure them.
:Focus: secrets
:Say: Your secrets and credentials.
:Focus: data
:Say: Your files and data.
:Focus: code
:Say: Your code and repositories.
:Focus: processes
:Say: And the processes you run.
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

Scene 03. What makes up that footprint
-------------------------------------

:Layout: scope
:Eyebrow: THE WHOLE PICTURE
:Title: Your tools. Your settings.|Your data. Your code.
:Subtitle: The pieces that make a machine feel like yours.
:Card: Applications | Install the tools you rely on
:Card: Configuration | Bring back public and private settings
:Card: Secrets | Manage credentials and passwords
:Card: Data | Back up, synchronize, and retrieve files
:Card: Repositories | Map out your code for backup and retrieval
:Takeaway: The software, the personal setup, and the work itself.
:Focus: software
:Say: Installing the software is only one part of it.
:Focus: personal
:Say: The personal setup matters too: public and private configurations, dotfiles, credentials, and passwords.
:Focus: work
:Say: Then there are your files and data, and the repositories you've mapped out for backup and retrieval.
:Source: README.md at 41aae8d08^; docs/index.md at 41aae8d08^; docs/guide/configuration.md; docs/guide/data-sync.md

Scene 04. All wrapped into one solution
--------------------------------------

:Layout: unified
:Eyebrow: ONE SOLUTION
:Title: Set it up.|Keep it in sync. Put it to work.
:Subtitle: Installation, configuration, synchronization, and orchestration.
:Card: Install | Applications and tools
:Card: Configure | Settings, dotfiles, and secrets
:Card: Synchronize | Data and code
:Card: Launch | Commands, files, and workspaces
:Card: Orchestrate | Processes and parallel work
:Takeaway: Setup, maintenance, and everyday work belong together.
:Focus: setup
:Say: StackOps brings package installation, configuration, secrets, and data and code synchronization into one solution.
:Focus: run
:Say: It also launches commands and orchestrates processes, so the same system helps you put that environment to work.
:Focus: together
:Say: Setup, maintenance, and the work you do every day, all connected.
:Source: README.md at 41aae8d08^; README.md CLI overview; docs/cli/fire.md; docs/cli/terminal.md; docs/cli/agents.md

Scene 05. The stack you are comfortable with
-------------------------------------------

:Layout: familiar
:Eyebrow: YOUR STACK
:Title: The stack you are|comfortable with.
:Subtitle: StackOps manages the stack you are comfortable with.
:Card: Linux | Your tools and configuration
:Card: macOS | Your tools and configuration
:Card: Windows | Your tools and configuration
:Takeaway: A cross-platform approach to managing your digital life.
:Focus: glue
:Say: StackOps doesn't reinvent the wheel. It glues together the best open-source tools.
:Focus: yours
:Say: Keep the stack you're comfortable with. StackOps manages the tools and settings that make it yours.
:Focus: platforms
:Say: It brings that approach across Linux, macOS, and Windows through a command-line interface.
:Source: docs/index.md at 41aae8d08^; README.md at 41aae8d08^; docs/installation.md

Scene 06. Your digital life, sorted
----------------------------------

:Layout: closing
:Eyebrow: STACKOPS
:Title: Your digital life.|Sorted.
:Subtitle: StackOps · Digital Life Manager
:Takeaway: 99% of your digital footprint. One solution.
:Link: thisismygitrepo.github.io/stackops/
:Focus: life
:Say: That's StackOps. Your digital life, sorted.
:Focus: explore
:Say: Bring the setup you've spent years building to the machine in front of you.
:Focus: docs
:Say: Explore the documentation to get started.
:Focus: platforms
:Say: All of it, OS-agnostic. Linux, macOS, and Windows.
:Source: User's current 99% wording; README.md at 41aae8d08^; docs/index.md at 41aae8d08^
