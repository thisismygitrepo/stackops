

from textual.widgets import Input, Label

from stackops.scripts.python.graph.visualize.helpers_navigator.search_bar import SearchBar


def test_compose_yields_search_label_and_input() -> None:
    widgets = list(SearchBar().compose())

    assert len(widgets) == 2
    assert isinstance(widgets[0], Label)
    assert str(widgets[0].render()) == "🔍 Search: "
    assert isinstance(widgets[1], Input)
    assert widgets[1].id == "search-input"
    assert widgets[1].placeholder == "Type to search commands..."
