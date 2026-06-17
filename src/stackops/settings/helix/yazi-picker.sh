#!/usr/bin/env bash
set -euo pipefail

if ! command -v yazi >/dev/null 2>&1; then
  printf 'yazi-picker: yazi is not installed or not on PATH\n' >&2
  exit 127
fi

chooser_file="$(mktemp "${TMPDIR:-/tmp}/helix-yazi-picker.XXXXXX")"
trap 'rm -f "$chooser_file"' EXIT

start_path="${1:-}"
if [[ -n "$start_path" && -e "$start_path" ]]; then
  if [[ -f "$start_path" ]]; then
    start_path="$(dirname -- "$start_path")"
  fi
else
  start_path=""
fi

run_yazi() {
  if [[ -n "$start_path" ]]; then
    yazi "$start_path" --chooser-file="$chooser_file"
    return
  fi
  yazi --chooser-file="$chooser_file"
}

if [[ -w /dev/tty ]]; then
  run_yazi >/dev/tty
else
  run_yazi
fi

if [[ -s "$chooser_file" ]]; then
  sed -n '1p' "$chooser_file"
fi
