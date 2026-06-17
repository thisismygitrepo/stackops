import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.mcp_install import (
    MCP_PREVIEW_SIZE_PERCENT,
    build_mcp_selection_preview_mapping,
    choose_requested_mcp_names,
)
from stackops.scripts.python.helpers.helpers_agents.mcp_types import McpCatalogLocation
from stackops.utils.options_utils import tv_options


def _write_mcp_catalog(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "alpha": {
                        "command": "uvx",
                        "args": ["alpha-mcp"],
                        "env": {"SECRET_TOKEN": "super-secret-value"},
                        "description": "Alpha MCP",
                    },
                    "beta": {
                        "url": "https://example.test/mcp",
                        "headers": {"Authorization": "Bearer $BETA_TOKEN"},
                        "description": "Beta MCP",
                    },
                }
            }
        ),
        encoding="utf-8",
    )


def test_mcp_selection_preview_sanitizes_env_and_header_values(tmp_path: Path) -> None:
    catalog_path = tmp_path / "mcp.json"
    _write_mcp_catalog(catalog_path)
    locations: tuple[McpCatalogLocation, ...] = ({"scope": "repo", "path": catalog_path},)

    preview_mapping = build_mcp_selection_preview_mapping(locations=locations)

    assert {"alpha", "beta"} == set(preview_mapping)
    assert "SECRET_TOKEN" in preview_mapping["alpha"]
    assert "super-secret-value" not in preview_mapping["alpha"]
    assert "Authorization" in preview_mapping["beta"]
    assert "Bearer $BETA_TOKEN" not in preview_mapping["beta"]


def test_choose_requested_mcp_names_uses_multi_preview_picker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    catalog_path = tmp_path / "mcp.json"
    _write_mcp_catalog(catalog_path)
    locations: tuple[McpCatalogLocation, ...] = ({"scope": "repo", "path": catalog_path},)

    def fake_choose_from_dict_with_preview(
        options_to_preview_mapping: dict[str, object], extension: str | None, multi: bool, preview_size_percent: float
    ) -> list[str]:
        assert {"alpha", "beta", "agent-browser"} <= set(options_to_preview_mapping)
        assert extension == "json"
        assert multi is True
        assert preview_size_percent == MCP_PREVIEW_SIZE_PERCENT
        return ["alpha", "beta"]

    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", fake_choose_from_dict_with_preview)

    assert choose_requested_mcp_names(locations=locations) == ("alpha", "beta")
