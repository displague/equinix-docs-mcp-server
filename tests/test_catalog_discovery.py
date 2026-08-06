"""Tests for API catalog discovery."""

from equinix_docs_mcp_server.catalog_discovery import (
    CatalogEntry,
    configured_slugs,
    extract_slugs,
    propose_config_entries,
)
from equinix_docs_mcp_server.config import APIConfig, Config, SpecSource


def make_config() -> Config:
    """A minimal config with one family, independent of the packaged file."""
    return Config(
        apis={
            "fabric": APIConfig(
                name="fabric",
                specs=[
                    SpecSource(
                        url="https://docs.equinix.com/api-catalog/fabricv4/openapi.yaml"
                    )
                ],
            )
        }
    )


def test_extract_slugs_dedupes_and_sorts():
    html = (
        '<a href="/api-catalog/fabricv4">Fabric</a>'
        '<a href="/api-catalog/metalv1">Metal</a>'
        '<a href="https://docs.equinix.com/api-catalog/fabricv4/openapi.yaml">spec</a>'
    )
    assert extract_slugs(html) == ["fabricv4", "metalv1"]


def test_configured_slugs_maps_to_families():
    config = Config.load()
    slugs = configured_slugs(config)
    assert slugs.get("metalv1") == "metal"
    assert slugs.get("fabricv4") == "fabric"
    assert slugs.get("workvisitv1") == "workvisit"


def test_propose_config_entries():
    config = make_config()
    entries = [
        CatalogEntry(
            slug="fabricv4",
            spec_url="https://docs.equinix.com/api-catalog/fabricv4/openapi.yaml",
            kind="openapi",
        ),
        CatalogEntry(
            slug="ordersv2",
            spec_url="https://docs.equinix.com/api-catalog/ordersv2/openapi.yaml",
            kind="openapi",
        ),
        CatalogEntry(slug="emgv1", kind="asyncapi"),
        CatalogEntry(
            slug="oldpagev1",
            spec_url="https://docs.equinix.com/api-catalog/newpagev2/openapi.yaml",
            kind="openapi",
            redirected_to="https://docs.equinix.com/api-catalog/newpagev2/openapi.yaml",
        ),
        CatalogEntry(slug="ghostv1"),
    ]

    report = propose_config_entries(config, entries)

    # Configured, asyncapi, redirected, and missing entries are not proposed
    assert "configured (family: fabric)" in report
    assert "AsyncAPI only" in report
    assert "redirects to" in report
    assert "no spec found" in report
    # The one genuinely new OpenAPI entry is proposed with a versionless family
    assert "  orders:\n" in report
    assert 'url: "https://docs.equinix.com/api-catalog/ordersv2/openapi.yaml"' in report


def test_apply_config_entries(tmp_path):
    """New families are appended into the apis: section with collision-safe names."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "apis.yaml"
    config_file.write_text(
        "apis:\n"
        "  billing:\n"
        '    auth_type: "client_credentials"\n'
        "    specs:\n"
        '      - url: "https://docs.equinix.com/api-catalog/billingv2/openapi.yaml"\n'
        "\n"
        "# Authentication configuration\n"
        "auth:\n"
        "  client_credentials:\n"
        '    token_url: "https://api.equinix.com/oauth2/v1/token"\n',
        encoding="utf-8",
    )
    config = Config.load(str(config_file))

    entries = [
        CatalogEntry(
            slug="billingv1",
            spec_url="https://docs.equinix.com/api-catalog/billingv1/openapi.yaml",
            kind="openapi",
        ),
        CatalogEntry(
            slug="ordersv2",
            spec_url="https://docs.equinix.com/api-catalog/ordersv2/openapi.yaml",
            kind="openapi",
        ),
        CatalogEntry(slug="emgv1", kind="asyncapi"),
    ]

    from equinix_docs_mcp_server.catalog_discovery import apply_config_entries

    added = apply_config_entries(config, entries)

    # billingv1's versionless name collides with the existing billing family
    assert added == ["billingv1", "orders"]

    updated = Config.load(str(config_file))
    assert set(updated.apis) == {"billing", "billingv1", "orders"}
    assert updated.auth.client_credentials["token_url"]

    # Re-running adds nothing
    assert apply_config_entries(updated, entries) == []
