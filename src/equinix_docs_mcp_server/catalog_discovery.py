"""Discover Equinix API specs from the docs.equinix.com API catalog.

The catalog page at https://docs.equinix.com/api-catalog links one page per
API (e.g. /api-catalog/fabricv4), and each serves a machine-readable spec at
<slug>/openapi.yaml (with rare AsyncAPI-only exceptions such as emgv1, which
serves <slug>/asyncapi.yaml instead). There is no machine-readable index of
the catalog itself, so the slugs are scraped from the page HTML.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from .config import Config

logger = logging.getLogger(__name__)

CATALOG_URL = "https://docs.equinix.com/api-catalog"

# docs.equinix.com answers 403 to non-browser user agents on the catalog
# page (the spec files themselves are unrestricted).
BROWSER_USER_AGENT = "Mozilla/5.0 (compatible; Equinix-MCP-Server)"

_SLUG_PATTERN = re.compile(r"api-catalog/([a-z0-9-]+)")


@dataclass
class CatalogEntry:
    """One API discovered in the catalog."""

    slug: str
    spec_url: Optional[str] = None  # resolved URL of the spec, if any
    kind: str = "unknown"  # "openapi", "asyncapi", or "unknown"
    redirected_to: Optional[str] = None  # final URL when the slug 301s away


def extract_slugs(html: str) -> List[str]:
    """Extract unique api-catalog slugs from the catalog page HTML."""
    return sorted(set(_SLUG_PATTERN.findall(html)))


async def _classify_slug(client: httpx.AsyncClient, slug: str) -> CatalogEntry:
    """Determine which spec flavor a catalog slug serves."""
    for filename, kind in (("openapi.yaml", "openapi"), ("asyncapi.yaml", "asyncapi")):
        url = f"{CATALOG_URL}/{slug}/{filename}"
        try:
            response = await client.head(url)
        except httpx.HTTPError as e:
            logger.debug(f"HEAD {url} failed: {e}")
            continue
        if response.status_code == 200:
            final_url = str(response.url)
            return CatalogEntry(
                slug=slug,
                spec_url=final_url,
                kind=kind,
                redirected_to=final_url if final_url != url else None,
            )
    return CatalogEntry(slug=slug)


async def discover_catalog_apis(
    catalog_url: str = CATALOG_URL,
) -> List[CatalogEntry]:
    """Scrape the catalog page and classify every listed API's spec."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": BROWSER_USER_AGENT},
    ) as client:
        response = await client.get(catalog_url)
        response.raise_for_status()
        slugs = extract_slugs(response.text)
        logger.info(f"Found {len(slugs)} API slugs in the catalog")

        return list(
            await asyncio.gather(*(_classify_slug(client, slug) for slug in slugs))
        )


def configured_slugs(config: Config) -> Dict[str, str]:
    """Map already-configured catalog slugs to their API family name."""
    slugs: Dict[str, str] = {}
    for family, api_config in config.apis.items():
        for spec_source in api_config.specs:
            match = _SLUG_PATTERN.search(spec_source.url)
            if match:
                slugs[match.group(1)] = family
    return slugs


def _classify_entries(
    config: Config, entries: List[CatalogEntry]
) -> tuple[List[str], List[tuple[str, str]]]:
    """Classify catalog entries against the config.

    Returns (report lines, proposals) where each proposal is a
    (family name, apis.yaml block) pair for a newly discovered OpenAPI spec.
    Family names are the slug minus its version suffix, falling back to the
    full slug when that would collide with an existing or proposed family
    (e.g. billingv1 alongside a configured billing family from billingv2).
    """
    known = configured_slugs(config)
    used_families = set(config.apis)
    lines: List[str] = []
    proposals: List[tuple[str, str]] = []

    for entry in entries:
        if entry.slug in known:
            status = f"configured (family: {known[entry.slug]})"
        elif entry.kind == "asyncapi":
            status = "skipped: AsyncAPI only"
        elif entry.kind == "unknown":
            status = "skipped: no spec found"
        elif entry.redirected_to:
            status = f"skipped: redirects to {entry.redirected_to}"
        else:
            family = re.sub(r"v\d+$", "", entry.slug)
            if family in used_families:
                family = entry.slug
            used_families.add(family)
            status = f"NEW (family: {family})"
            proposals.append(
                (
                    family,
                    f"  {family}:\n"
                    f'    auth_type: "client_credentials"\n'
                    f'    service_name: "{family}"\n'
                    f"    specs:\n"
                    f'      - url: "{entry.spec_url}"\n',
                )
            )
        lines.append(f"  {entry.slug:<24} {status}")

    return lines, proposals


def propose_config_entries(config: Config, entries: List[CatalogEntry]) -> str:
    """Render a report plus ready-to-paste apis.yaml entries for new APIs.

    Only OpenAPI entries are proposed (AsyncAPI cannot back an OpenAPI
    provider). Proposals default to client_credentials auth; adjust per API
    as needed.
    """
    lines, proposals = _classify_entries(config, entries)

    report = "Discovered API catalog entries:\n" + "\n".join(lines)
    if proposals:
        report += (
            "\n\nProposed apis.yaml additions (review auth_type and consider"
            " overlays or include/exclude filters before enabling):\n\n"
            + "\n".join(block for _, block in proposals)
        )
    else:
        report += "\n\nNo new OpenAPI entries to propose."
    return report


def apply_config_entries(config: Config, entries: List[CatalogEntry]) -> List[str]:
    """Append newly discovered API families to the config file in place.

    Inserts each proposed family block at the end of the `apis:` mapping
    (immediately before the first other top-level section). Returns the
    family names that were added.
    """
    _, proposals = _classify_entries(config, entries)
    if not proposals:
        return []
    if not config.config_path:
        raise ValueError("Config has no config_path to write to")

    path = Path(config.config_path)
    text = path.read_text(encoding="utf-8")

    match = re.search(r"^(?:#[^\n]*\n)*(?:auth|docs|arazzo):", text, re.MULTILINE)
    if not match:
        raise ValueError(
            f"Could not find the end of the apis section in {config.config_path}"
        )

    insertion = "".join(f"\n{block}" for _, block in proposals)
    text = (
        text[: match.start()].rstrip("\n")
        + "\n"
        + insertion
        + "\n"
        + text[match.start() :]
    )
    path.write_text(text, encoding="utf-8")

    return [family for family, _ in proposals]
