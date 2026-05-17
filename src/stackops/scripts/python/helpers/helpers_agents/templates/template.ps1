$ErrorActionPreference = "Stop"

$REPO_ROOT = "$HOME/code/stackops"
$JOB_NAME = "agentsTrial"
$CONTEXT_PATH = "$REPO_ROOT/.ai/agents/template/files.md"
$PROMPT_PATH = "$REPO_ROOT/.ai/agents/template/prompt.txt"
$AGENTS_DIR = "$REPO_ROOT/.ai/agents/template/$JOB_NAME"

if (Test-Path -LiteralPath $AGENTS_DIR) {
    Remove-Item -LiteralPath $AGENTS_DIR -Recurse -Force
}

agents parallel create `
    --agent codex `
    --model gpt-5.3-codex `
    --provider openai `
    --agent-load 5 `
    --context-path $CONTEXT_PATH `
    --prompt-path $PROMPT_PATH `
    --job-name $JOB_NAME `
    --agents-dir $AGENTS_DIR `
    --separator "\n"

sessions balance-load "$AGENTS_DIR/layout.json" `
    --max-threshold 4 `
    --breaking-method moreLayouts `
    --threshold-type number `
    --output-path "$AGENTS_DIR/layout_balanced.json"

Write-Output "Please run like this `"sessions run --layouts-file `"$AGENTS_DIR/layout_balanced.json`" --kill-upon-completion`""
Write-Output "Then, do this `"agents parallel collect $AGENTS_DIR `"$REPO_ROOT/.ai/agents/$JOB_NAME/collected.txt`"`""
