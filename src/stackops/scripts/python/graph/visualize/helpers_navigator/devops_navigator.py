#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "stackops>=8.93",
#     "textual",
# ]
# ///

"""Textual TUI for navigating `stackops` command structure."""


def main() -> None:
    from stackops.scripts.python.graph.visualize.helpers_navigator.main_app import CommandNavigatorApp

    CommandNavigatorApp().run()


if __name__ == "__main__":
    main()
