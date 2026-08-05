"""Tests for API catalog discovery."""

from equinix_docs_mcp_server.catalog_discovery import (
    CatalogEntry,
    configured_slugs,
    extract_slugs,
    propose_config_entries,
)
from equinix_docs_mcp_server.config import Config


def test_extract_slugs_dedupes_and_sorts():
    html = (
        '<a href="/api-catalog/fabricv4">Fabric</a>'
        '<a href="/api-catalog/metalv1">Metal</a>'
        '<a href="https://docs.equinix.com/api-catalog/fabricv4/openapi.yaml">spec</a>'
    )
    assert extract_slugs(html) == ["fabricv4", "metalv1"]


def test_configured_slugs_maps_to_families():
    config = Config.load("config/apis.yaml")
    slugs = configured_slugs(config)
    assert slugs.get("metalv1") == "metal"
    assert slugs.get("fabricv4") == "fabric"
    assert slugs.get("workvisitv1") == "workvisit"


def test_propose_config_entries():
    config = Config.load("config/apis.yaml")
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
