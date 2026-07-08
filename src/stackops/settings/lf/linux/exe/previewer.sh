#!/bin/sh
set -eu

path=$1
width=$2
height=$3

case "$path" in
    *.md|*.markdown)
        CLICOLOR_FORCE=1 exec glow --width "$width" --style dark "$path"
        ;;
    *.csv)
        exec uvx --from rich-cli rich --force-terminal --csv --head "$height" --width "$width" "$path"
        ;;
    *.json)
        exec jq --color-output . -- "$path"
        ;;
    *.7z|*.bz2|*.gz|*.jar|*.rar|*.tar|*.tar.bz2|*.tar.gz|*.tar.xz|*.tar.zst|*.tgz|*.txz|*.xz|*.zip|*.zst)
        exec ouch list -- "$path"
        ;;
esac

mime_type=$(file --mime-type -Lb -- "$path")
case "$mime_type" in
    text/*)
        exec bat --color=always --style=plain --paging=never \
            --tabs 2 --terminal-width "$width" --line-range "1:$height" -- "$path"
        ;;
    image/*)
        exec chafa --size "${width}x${height}" -- "$path"
        ;;
    application/pdf)
        exec pdftotext -layout -nopgbrk -q -- "$path" -
        ;;
    *)
        exec file -Lb -- "$path"
        ;;
esac
