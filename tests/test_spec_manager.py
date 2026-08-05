"""Test spec manager functionality."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from equinix_docs_mcp_server.config import Config
from equinix_docs_mcp_server.spec_manager import SpecManager


@pytest.fixture
def config():
    """Load test configuration."""
    return Config.load("config/apis.yaml")


@pytest.fixture
def spec_manager(config):
    """Create spec manager instance."""
    return SpecManager(config)


def test_spec_manager_init(spec_manager):
    """Test SpecManager initialization."""
    assert spec_manager is not None
    assert spec_manager.config is not None
    assert spec_manager.overlay_manager is not None


@pytest.mark.asyncio
async def test_create_overlay_template(spec_manager, tmp_path):
    """Test overlay template creation."""
    overlay_path = tmp_path / "test_overlay.yaml"

    await spec_manager.overlay_manager.create_overlay_template(
        str(overlay_path), "metal", "metal"
    )

    assert overlay_path.exists()

    # Check content
    with open(overlay_path) as f:
        content = f.read()
        assert "Metal" in content
        assert "overlay: 1.0.0" in content


def test_apply_simple_overlay(spec_manager):
    """Test applying a simple overlay."""
    spec = {
        "info": {"title": "Original Title"},
        "servers": [{"url": "https://old.example.com"}],
    }

    overlay = {
        "actions": [
            {"target": "$.info.title", "update": "New Title"},
            {"target": "$.servers", "update": [{"url": "https://new.example.com"}]},
        ]
    }

    result = spec_manager.overlay_manager.apply(spec, "test", overlay)

    assert result["info"]["title"] == "New Title"
    assert result["servers"] == [{"url": "https://new.example.com"}]


def test_overlay_files_exist(config):
    """Test that overlay files exist for all configured APIs."""
    for api_name in config.get_api_names():
        api_config = config.get_api_config(api_name)
        if not api_config.specs:
            continue
        for spec in api_config.specs:
            if spec.overlay:
                overlay_path = Path(spec.overlay)
                assert (
                    overlay_path.exists()
                ), f"Overlay file missing for {api_name}: {overlay_path}"


def test_apply_autogen_operation_ids(spec_manager):
    """Operations lacking operationIds get deterministic generated names."""
    spec = {
        "paths": {
            "/workvisits": {
                "get": {"responses": {}},
                "post": {"responses": {}},
            },
            "/workvisits/{id}": {
                "get": {"responses": {}},
                "delete": {"responses": {}},
            },
            "/keep": {
                "get": {"operationId": "customName", "responses": {}},
            },
        }
    }

    spec_manager._apply_autogen_operation_ids(spec)

    paths = spec["paths"]
    assert paths["/workvisits"]["get"]["operationId"] == "listWorkvisits"
    assert paths["/workvisits"]["post"]["operationId"] == "postWorkvisits"
    assert paths["/workvisits/{id}"]["get"]["operationId"] == "getWorkvisits"
    assert paths["/workvisits/{id}"]["delete"]["operationId"] == "deleteWorkvisits"
    # Existing operationIds are untouched
    assert paths["/keep"]["get"]["operationId"] == "customName"


def test_apply_autogen_operation_ids_uniqueness(spec_manager):
    """Generated names that collide with existing ones get numeric suffixes."""
    spec = {
        "paths": {
            "/things": {"get": {"operationId": "listThings", "responses": {}}},
            "/other/things": {"get": {"responses": {}}},
        }
    }

    spec_manager._apply_autogen_operation_ids(spec)

    assert spec["paths"]["/other/things"]["get"]["operationId"] == "listThings2"
