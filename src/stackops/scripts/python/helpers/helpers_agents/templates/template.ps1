$ErrorActionPreference = "Stop"

$STACKOPS_REPO_DIR = "$HOME/code/stackops"
$REPO_ROOT = $STACKOPS_REPO_DIR
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

terminal balance-load "$AGENTS_DIR/layout.json" `
    --max-threshold 4 `
    --breaking-method more-layouts `
    --threshold-type number `
    --output "$AGENTS_DIR/layout_balanced.json"

Write-Output "Please run like this `"terminal run `"$AGENTS_DIR/layout_balanced.json`" --kill-upon-completion`""
Write-Output "Then, do this `"agents parallel collect $AGENTS_DIR `"$REPO_ROOT/.ai/agents/$JOB_NAME/collected.txt`"`""
