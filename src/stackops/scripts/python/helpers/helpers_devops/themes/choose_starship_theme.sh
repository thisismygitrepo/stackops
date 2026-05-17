#!/bin/bash

# Ensure UTF-8 encoding for symbols and CLI tools
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export LC_CTYPE=C.UTF-8
export PYTHONIOENCODING=utf-8

if ! command -v starship &> /dev/null; then
    echo "Error: 'starship' not found."
    exit 1
fi

if ! input_data=$(starship preset --list); then
    echo "Error: failed to list Starship presets."
    exit 1
fi

if [ -z "$input_data" ]; then
    echo "Error: no Starship presets found."
    exit 1
fi

preview_config="${TMPDIR:-/tmp}/starship_preview.toml"
preview_cmd="preset=\$(printf '%s' '{}'); starship preset \"\$preset\" > \"$preview_config\" && LANG=C.UTF-8 LC_ALL=C.UTF-8 STARSHIP_CONFIG=\"$preview_config\" STARSHIP_SHELL=fish starship prompt"

if command -v tv &> /dev/null; then
    # tv requires input from stdin if no source-command is given
    selected_line=$(printf "%s" "$input_data" | LANG=C.UTF-8 LC_ALL=C.UTF-8 tv --ansi --preview-command "$preview_cmd" --preview-size 50)
elif command -v fzf &> /dev/null; then
    selected_line=$(printf "%s" "$input_data" | LANG=C.UTF-8 LC_ALL=C.UTF-8 fzf --ansi --preview "$preview_cmd" --preview-window bottom:30%)
else
    echo "Error: 'tv' or 'fzf' not found."
    exit 1
fi

if [ -n "$selected_line" ]; then
    selected_preset="$selected_line"
    echo "Applying $selected_preset..."
    starship preset "$selected_preset" -o ~/.config/starship.toml
    echo "Done!"
fi
