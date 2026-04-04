from pathlib import Path


def test_hierarchy_page_embeds_checked_in_sunburst_asset() -> None:
    hierarchy_path = Path("docs/hierarchy.md")
    hierarchy_text = hierarchy_path.read_text(encoding="utf-8")

    assert 'src="../assets/devops-self-explore/sunburst.html"' in hierarchy_text
    assert "plotly-preview-frame" in hierarchy_text
    assert "devops self build-assets regenerate-charts" in hierarchy_text
