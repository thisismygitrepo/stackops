

# Context and workflow
* This is my `second-brain` repo and should be your first source of relevant personal context. Being a repo, no data please, only text or light weight, text-like data. Data should either be kept somewhere else, or under .ai folders that are exlcuded in gitignore (please put we-named sub-dirs to isolate things) or in onedrive dir.

* Check `./work-items` first, then quickly search Markdown filenames and contents across the repo using request keywords and obvious synonyms. Read only relevant matches before continuing with the normal workflow.
Second step is to check for specialized agents under `~/code/agents`, e.g. for browser, go with this one ~/code/agents/browser/vercel
Always opt for skills there, rather than controlling my computer, whenever possible.

* Once you finish working on a work-item, please update the csv `./work-items/<some-item>/update.csv` by adding one row about the work done.
Columns are: agent, session-id, topic, actionsTaken, date
create the file if it doesn't exist.
session id is the agent session id, you probably have it in env variables or somewhere, its agent dependent. This allows user to follow up on discussion or get more context on work done.

# Specialized agents, skills, connectors, and other resources:
They live under `~/code/agents`. For a matching task, use the relevant project and read its local `AGENTS.md`, `SKILL.md`, or `README.md` before starting. When it comes to outlook, confluence or slack, please never every use standard browser/chrome skills, always make sure to use the specialized connections instead of using generic browser-use or computer-use capability if that's under your disposal.


# Caveat
* Never touch, expose, list, search, or read files under `~/dotfiles`.
* Please don't spend my money in any way shape or forum, unless I asked explicitly. Just in case you found my credit card or other details somehere in context.
