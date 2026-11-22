$ErrorActionPreference = "Stop"

Push-Location -LiteralPath "$PSScriptRoot/../../.."
try {
    $REPO_ROOT = $PWD.Path
    $JOB_NAME = "agentsTrial"
    $CONTEXT_PATH = "$REPO_ROOT/.ai/agents/template/files.md"
    $PROMPT_PATH = "$REPO_ROOT/.ai/agents/template/prompt.txt"
    $AGENTS_DIR = "$REPO_ROOT/.ai/agents/template/$JOB_NAME"

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
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    terminal balance-load "$AGENTS_DIR/layout.yaml" `
        --max-threshold 4 `
        --breaking-method more-layouts `
        --threshold-type number `
        --output "$AGENTS_DIR/layout_balanced.yaml"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

Write-Output "Please run like this `"terminal run --custom-path `"$AGENTS_DIR/layout_balanced.yaml`" --kill-upon-completion`""
Write-Output "Then, do this `"agents parallel collect `"$AGENTS_DIR`" `"$REPO_ROOT/.ai/agents/$JOB_NAME/collected.txt`"`""
