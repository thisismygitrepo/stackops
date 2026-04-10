#!/usr/bin/env bash
# set -euo pipefail

repo_root="$HOME/code/machineconfig"
agents_dir="$repo_root/.ai/agents/updateInstallerData"

cd "$repo_root" || exit 1

uv run agents parallel create \
  --agent codex \
  --host local \
  --context-path "$repo_root/src/machineconfig/jobs/installer/installer_data.json" \
  --separator '    },\n    {' \
  --agent-load 10 \
  --prompt-path "$repo_root/scripts/assets/installer_data_update_prompt.md" \
  --job-name updateInstallerData \
  --output-path "$agents_dir/layout.json" \
  --agents-dir "$agents_dir"
