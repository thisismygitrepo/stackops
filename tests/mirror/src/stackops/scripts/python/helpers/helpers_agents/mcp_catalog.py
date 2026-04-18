from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

from stackops.scripts.python.helpers.helpers_agents import mcp_catalog as module
from stackops.scripts.python.helpers.helpers_agents.mcp_types import McpCatalogLocation


CatalogScope = Literal["private", "public", "library"]


def _location(scope: CatalogScope, path: Path) -> McpCatalogLocation:
    return {"scope": scope, "path": path}


def _write_catalog(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_parse_requested_mcp_names_trims_and_preserves_order() -> None:
    assert module.parse_requested_mcp_names(" alpha , beta , gamma ") == ("alpha", "beta", "gamma")


@pytest.mark.parametrize(
    ("raw_value", "message"),
    [
        ("", "Provide at least one MCP server name"),
        ("alpha,,beta", "without empty entries"),
        ("alpha,beta,alpha", "Duplicate MCP server names are not allowed"),
    ],
)
def test_parse_requested_mcp_names_rejects_invalid_lists(raw_value: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        module.parse_requested_mcp_names(raw_value)


def test_ensure_mcp_catalog_exists_creates_template_only_for_missing_non_library_catalog(tmp_path: Path) -> None:
    private_location = _location("private", tmp_path / "private" / "mcp.json")

    assert module.ensure_mcp_catalog_exists(private_location) is True
    assert private_location["path"].read_text(encoding="utf-8") == """{\n  \"mcpServers\": {}\n}\n"""
    assert module.ensure_mcp_catalog_exists(private_location) is False

    library_location = _location("library", tmp_path / "library" / "mcp.json")
    assert module.ensure_mcp_catalog_exists(library_location) is False
    assert not library_location["path"].exists()


def test_load_mcp_catalog_accepts_supported_fields_and_rejects_unknown_ones(tmp_path: Path) -> None:
    valid_path = tmp_path / "valid.json"
    _write_catalog(
        valid_path,
        {
            "mcpServers": {
                "stdio": {"command": "uvx", "args": ["demo"], "env": {"TOKEN": "value"}},
                "http": {
                    "url": "https://example.com",
                    "headers": {"Authorization": "Bearer $TOKEN"},
                    "enabled": False,
                },
            }
        },
    )

    catalog = module._load_mcp_catalog(valid_path)
    assert set(catalog["mcpServers"]) == {"stdio", "http"}
    assert catalog["mcpServers"]["stdio"]["args"] == ["demo"]
    assert catalog["mcpServers"]["http"]["enabled"] is False

    invalid_path = tmp_path / "invalid.json"
    _write_catalog(
        invalid_path,
        {"mcpServers": {"bad": {"command": "uvx", "bogus": "value"}}},
    )

    with pytest.raises(ValueError, match="unsupported field"):
        module._load_mcp_catalog(invalid_path)


def test_normalize_server_definition_applies_transport_rules(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"

    stdio_definition = module._normalize_server_definition(
        {"command": "uvx", "args": ["demo"], "env": {"TOKEN": "value"}},
        server_name="stdio",
        path=catalog_path,
    )
    assert stdio_definition == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["demo"],
        "env": {"TOKEN": "value"},
        "url": None,
        "headers": {},
        "cwd": None,
        "description": None,
        "enabled": True,
    }

    http_definition = module._normalize_server_definition(
        {
            "url": "https://example.com",
            "headers": {"Authorization": "Bearer $TOKEN"},
            "enabled": False,
        },
        server_name="http",
        path=catalog_path,
    )
    assert http_definition["transport"] == "http"
    assert http_definition["url"] == "https://example.com"
    assert http_definition["headers"] == {"Authorization": "Bearer $TOKEN"}
    assert http_definition["enabled"] is False

    with pytest.raises(ValueError, match="exactly one of 'command' or 'url'"):
        module._normalize_server_definition(
            {"command": "uvx", "url": "https://example.com"},
            server_name="broken",
            path=catalog_path,
        )


def test_resolve_requested_mcp_servers_prefers_earlier_catalog_locations(tmp_path: Path) -> None:
    private_path = tmp_path / "private.json"
    public_path = tmp_path / "public.json"
    _write_catalog(
        private_path,
        {"mcpServers": {"shared": {"url": "https://private.example.com"}, "local": {"command": "uvx"}}},
    )
    _write_catalog(
        public_path,
        {
            "mcpServers": {
                "shared": {"url": "https://public.example.com"},
                "public-only": {"command": "python", "args": ["-m", "demo"]},
            }
        },
    )

    locations = (_location("private", private_path), _location("public", public_path))
    resolved = module.resolve_requested_mcp_servers(("shared", "public-only"), locations=locations)

    assert [server["scope"] for server in resolved] == ["private", "public"]
    assert resolved[0]["definition"]["url"] == "https://private.example.com"
    assert resolved[1]["definition"]["command"] == "python"
    assert module.format_resolved_mcp_servers(resolved) == "shared (private), public-only (public)"


def test_resolve_requested_mcp_servers_reports_missing_catalogs_and_servers(tmp_path: Path) -> None:
    missing_location = _location("public", tmp_path / "missing.json")
    with pytest.raises(ValueError, match="No MCP catalog files were found"):
        module.resolve_requested_mcp_servers(("alpha",), locations=(missing_location,))

    existing_path = tmp_path / "existing.json"
    _write_catalog(existing_path, {"mcpServers": {"alpha": {"command": "uvx"}}})
    with pytest.raises(ValueError, match="MCP servers not found: beta"):
        module.resolve_requested_mcp_servers(("beta",), locations=(_location("public", existing_path),))


def test_collect_available_mcp_names_deduplicates_names_in_location_order(tmp_path: Path) -> None:
    private_path = tmp_path / "private.json"
    public_path = tmp_path / "public.json"
    _write_catalog(
        private_path,
        {"mcpServers": {"shared": {"command": "uvx"}, "alpha": {"command": "python"}}},
    )
    _write_catalog(
        public_path,
        {"mcpServers": {"shared": {"url": "https://example.com"}, "beta": {"url": "https://example.org"}}},
    )

    names = module.collect_available_mcp_names(
        locations=(_location("private", private_path), _location("public", public_path))
    )

    assert names == ("shared", "alpha", "beta")


def test_edit_mcp_catalog_fails_when_no_supported_editor_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)

    with pytest.raises(ValueError, match="No supported editor found"):
        module.edit_mcp_catalog(tmp_path / "mcp.json")
