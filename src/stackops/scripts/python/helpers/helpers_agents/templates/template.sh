
#!/bin/bash
# set -e # Exit immediately if a command exits with a non-zero status.


STACKOPS_REPO_DIR="$HOME/code/stackops"
REPO_ROOT="$STACKOPS_REPO_DIR"

JOB_NAME="agentsTrial"
CONTEXT_PATH="$REPO_ROOT/.ai/agents/template/files.md"
PROMPT_PATH="$REPO_ROOT/.ai/agents/template/prompt.txt"
AGENTS_DIR="$REPO_ROOT/.ai/agents/template/$JOB_NAME"
rm -rfd "$AGENTS_DIR" || true

agents parallel create \
    --agent codex \
    --model gpt-5.3-codex \
    --provider openai \
    --agent-load 5 \
    --context-path $CONTEXT_PATH \
    --prompt-path $PROMPT_PATH \
    --job-name $JOB_NAME \
    --agents-dir $AGENTS_DIR \
    --separator $'\n'

terminal balance-load "$AGENTS_DIR/layout.json" \
    --max-threshold 4 \
    --breaking-method more-layouts \
    --threshold-type number \
    --output "$AGENTS_DIR/layout_balanced.json"

printf 'Please run like this `terminal run --custom-path "%s/layout_balanced.json" --kill-upon-completion`\n' "$AGENTS_DIR"
printf 'Then, do this `agents parallel collect "%s" "%s/.ai/agents/%s/collected.txt"`\n' "$AGENTS_DIR" "$REPO_ROOT" "$JOB_NAME"
