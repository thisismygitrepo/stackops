

from stackops.scripts.python.helpers.helpers_sessions import _zellij_backend_layout as layout_backend


def test_parse_kdl_attrs_reads_quoted_and_bare_values() -> None:
    attrs = layout_backend.parse_kdl_attrs('pane name="editor \\"main\\"" cwd=/tmp/project count=3')

    assert attrs == {"name": 'editor "main"', "cwd": "/tmp/project", "count": "3"}


def test_summarize_layout_ignores_plugins_and_formats_tabs() -> None:
    summary = layout_backend.summarize_layout(
        """
        // comment
        tab name="Main" {
            pane name="Editor" command="/usr/bin/nvim" cwd="/tmp/project"
            args "--clean" "/tmp/project/app.py"
            pane plugin location="zellij:tab-bar"
        }
        tab {
        }
        """
    )

    assert summary == "\n".join(["tabs: 2", "[1] Main", "  - Editor: nvim --clean app.py [/tmp/project]", "[2] Tab #2", "  - shell"])


def test_summarize_layout_falls_back_on_invalid_args() -> None:
    summary = layout_backend.summarize_layout(
        """
        tab name="Broken" {
            pane command="python"
            args "unterminated token
        }
        """
    )

    assert summary is not None
    assert 'python "unterminated token' in summary
