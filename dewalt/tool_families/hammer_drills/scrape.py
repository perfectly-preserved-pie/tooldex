from __future__ import annotations

import argparse
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from dewalt.tool_families.drill_drivers.scrape import (
    MAX_VOLTAGE_PATTERN,
    NOMINAL_VOLTAGE_PATTERN,
    PAGE_PATTERN,
    PRODUCT_URL_PATTERN,
    RPM_PATTERN,
    extract_section_items,
    extract_text_items,
    format_iso_now,
    get_soup_text,
    normalize_chuck_size_label,
    normalize_text,
    parse_bool_value,
    parse_canonical_url,
    parse_float_value,
    parse_int_value,
    parse_nominal_voltage_v,
    parse_power_source,
    parse_rpm_max,
    parse_series,
    parse_specifications_table,
    parse_tool_length_in,
    parse_voltage_system,
    sku_looks_like_bare_tool,
)


CATALOG_URL = "https://www.dewalt.com/products/power-tools/drills/hammer-drills"
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "dewalt_hammer_drills.json"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}
SESSION = requests.Session()
SESSION.headers.update(REQUEST_HEADERS)
SESSION.mount("http://", HTTPAdapter(max_retries=3))
SESSION.mount("https://", HTTPAdapter(max_retries=3))


def fetch_url(url: str, timeout: int = 45) -> str:
    """Fetch a DEWALT page with ``requests`` and decode it as text.

    Args:
        url: Fully qualified page URL to request.
        timeout: Socket timeout in seconds for the request.

    Returns:
        The decoded HTML body as a string.
    """
    response = SESSION.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_impact_rate_bpm(specs: dict[str, str]) -> int | None:
    """Parse the hammer impact rate from the specification map when present.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        The highest impact-rate value, or ``None`` when unavailable.
    """
    raw_value = (
        specs.get("Impact Rate per Min.")
        or specs.get("Blows/Min")
        or specs.get("Blows Per Minute")
        or specs.get("Impacts/Min")
    )
    if raw_value:
        return parse_int_value(raw_value)
    return None


def should_exclude_product(title: str, description: str) -> bool:
    """Determine whether a listed product should be excluded from this family.

    Args:
        title: Product title string.
        description: Product overview string.

    Returns:
        ``True`` when the product is outside the intended hammer-drill scope.
    """
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    if "hammer drill" not in lowered and "hammerdrill" not in lowered:
        return True
    if "combo kit" in lowered:
        return True
    return False


def is_supported_hammer_drill(row: dict[str, Any]) -> bool:
    """Apply the hammer-drill product-scope rule for the dashboard.

    Args:
        row: Parsed hammer-drill row.

    Returns:
        ``True`` for all corded hammer drills and bare-tool cordless hammer drills.
    """
    if row["power_source"] != "Cordless":
        return True
    return bool(row["tool_only"])


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse a hammer-drill product page into a structured row.

    Args:
        url: Canonical product URL.
        html_text: Raw HTML for the product page.

    Returns:
        A parsed row dictionary, or ``None`` when the product is out of scope.
    """
    soup = BeautifulSoup(html_text, "html.parser")

    title_node = soup.select_one("h1.coh-heading.title.coh-style-h4---display")
    title = get_soup_text(title_node)
    if not title:
        og_title = soup.find("meta", attrs={"property": "og:title"})
        title = normalize_text(og_title.get("content", "")) if og_title else ""

    description_node = soup.select_one("div.coh-inline-element.description")
    description = get_soup_text(description_node)
    if not description:
        og_description = soup.find("meta", attrs={"property": "og:description"})
        description = (
            normalize_text(og_description.get("content", "")) if og_description else ""
        )

    if should_exclude_product(title, description):
        return None

    primary_features = extract_text_items(soup, "li.feature-list-li")
    additional_features = extract_text_items(soup, "li.additional-feature-list-li")
    includes = extract_section_items(soup, "product-includes-accordion")
    applications = extract_section_items(soup, "product-applications-data")
    disclaimers = extract_section_items(soup, "disclaimer")
    specs = parse_specifications_table(soup)

    all_text_parts = [
        title,
        description,
        *primary_features,
        *additional_features,
        *includes,
        *applications,
        *disclaimers,
        *specs.keys(),
        *specs.values(),
    ]
    all_text = " ".join(part for part in all_text_parts if part)
    lowered = all_text.lower()

    power_source = parse_power_source(specs, all_text)
    voltage_system, max_voltage_v = parse_voltage_system(specs, power_source, all_text)
    no_load_speed = (
        specs.get("No Load Speed [RPM]")
        or specs.get("Speed [rpm]")
        or specs.get("RPM")
    )
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    tool_only = power_source == "Cordless" and (
        "tool only" in title.lower() or sku_looks_like_bare_tool(sku)
    )

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Hammer Drill",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": specs.get("Battery Type") or specs.get("Battery Chemistry"),
        "battery_capacity_ah": parse_float_value(specs.get("Battery Capacity [Ah]")),
        "amp_rating": parse_float_value(specs.get("Amps [A]")),
        "chuck_size_label": normalize_chuck_size_label(specs.get("Chuck Size [in]")),
        "chuck_size_in": parse_float_value(specs.get("Chuck Size [in]")),
        "chuck_type": specs.get("Chuck Type"),
        "speed_count": parse_int_value(specs.get("Number of Speed Settings")),
        "clutch_positions": parse_int_value(specs.get("Number of Clutch Positions")),
        "no_load_speed": no_load_speed,
        "rpm_max": parse_rpm_max(no_load_speed),
        "impact_rate_bpm": parse_impact_rate_bpm(specs),
        "max_watts_out": parse_int_value(
            specs.get("Max. Watts Out [W]") or specs.get("Max. Power [MWO]")
        ),
        "power_output_watts": parse_int_value(specs.get("Power Output [W]")),
        "tool_length_in": parse_tool_length_in(specs),
        "weight_lbs": parse_float_value(specs.get("Product Weight [lbs]")),
        "brushless": parse_bool_value(specs.get("Is Brushless?"))
        if specs.get("Is Brushless?") is not None
        else "brushless" in lowered,
        "variable_speed": parse_bool_value(specs.get("Has Variable Speed?"))
        if specs.get("Has Variable Speed?") is not None
        else "variable speed" in lowered,
        "led_light": parse_bool_value(specs.get("Has LED Light?")),
        "lock_on_switch": parse_bool_value(specs.get("Has Lock On Switch?")),
        "secondary_handle": parse_bool_value(specs.get("Has Secondary Handle?")),
        "kit": " kit" in title.lower() or title.lower().endswith("kit"),
        "tool_only": tool_only,
        "battery_included": parse_bool_value(specs.get("Is Battery Included?"))
        if specs.get("Is Battery Included?") is not None
        else any("battery" in item.lower() for item in includes),
        "charger_included": any("charger" in item.lower() for item in includes),
        "tool_connect_ready": "tool connect" in lowered,
        "description": description,
        "features": primary_features,
        "additional_features": additional_features,
        "includes": includes,
        "applications": applications,
        "disclaimers": disclaimers,
    }


def fetch_listing_pages() -> dict[str, str]:
    """Fetch all paginated hammer-drill catalog listing pages.

    Args:
        None.

    Returns:
        A mapping of listing-page URL to HTML body text.
    """
    pages = {CATALOG_URL: fetch_url(CATALOG_URL)}
    page_numbers = {0}
    page_numbers.update(int(match) for match in PAGE_PATTERN.findall(pages[CATALOG_URL]))

    for page_number in sorted(page_numbers):
        if page_number == 0:
            continue
        url = f"{CATALOG_URL}?page={page_number}"
        pages[url] = fetch_url(url)
    return pages


def collect_product_urls(listing_pages: dict[str, str]) -> list[str]:
    """Collect unique product URLs from the hammer-drill listing pages.

    Args:
        listing_pages: Mapping of listing-page URLs to HTML strings.

    Returns:
        A sorted list of unique DEWALT product URLs.
    """
    urls: list[str] = []
    for html_text in listing_pages.values():
        urls.extend(PRODUCT_URL_PATTERN.findall(html_text))
    return sorted(set(urls))


def build_snapshot_from_live_catalog() -> dict[str, Any]:
    """Build a hammer-drill snapshot by scraping the live DEWALT catalog.

    Args:
        None.

    Returns:
        A JSON-serializable snapshot payload for hammer drills.
    """
    listing_pages = fetch_listing_pages()
    product_urls = collect_product_urls(listing_pages)

    rows = []
    for product_url in product_urls:
        html_text = fetch_url(product_url)
        parsed_row = parse_product_page(product_url, html_text)
        if parsed_row and is_supported_hammer_drill(parsed_row):
            rows.append(parsed_row)

    rows.sort(key=lambda row: row["sku"])
    return {
        "scraped_at": format_iso_now(),
        "catalog_url": CATALOG_URL,
        "listing_page_count": len(listing_pages),
        "raw_product_count": len(product_urls),
        "product_count": len(rows),
        "excluded_product_count": len(product_urls) - len(rows),
        "rows": rows,
    }


def build_snapshot_from_directory(source_dir: Path) -> dict[str, Any]:
    """Build a hammer-drill snapshot from cached product-page HTML files.

    Args:
        source_dir: Directory containing saved DEWALT product-page HTML files.

    Returns:
        A JSON-serializable snapshot payload for hammer drills.
    """
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_hammer_drill(parsed_row):
            rows.append(parsed_row)

    rows.sort(key=lambda row: row["sku"])
    return {
        "scraped_at": format_iso_now(),
        "catalog_url": CATALOG_URL,
        "listing_page_count": None,
        "raw_product_count": len(html_files),
        "product_count": len(rows),
        "excluded_product_count": len(html_files) - len(rows),
        "rows": rows,
    }


def save_snapshot(snapshot: dict[str, Any], output_path: Path) -> None:
    """Persist a hammer-drill snapshot to disk as formatted JSON.

    Args:
        snapshot: Snapshot payload to serialize.
        output_path: Destination JSON path.

    Returns:
        None. The snapshot is written to disk as a side effect.
    """
    from dewalt.data import sanitize_snapshot_payload

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sanitize_snapshot_payload(snapshot), indent=2))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the hammer-drill scraper.

    Args:
        None.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Scrape DEWALT hammer-drill product data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_PATH,
        help=f"Output JSON path (default: {DATA_PATH})",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Optional directory of cached DEWALT product page HTML files.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the hammer-drill scraper CLI.

    Args:
        None.

    Returns:
        None. The scraper writes a snapshot to disk.
    """
    args = parse_args()
    if args.source_dir:
        snapshot = build_snapshot_from_directory(args.source_dir)
    else:
        snapshot = build_snapshot_from_live_catalog()

    save_snapshot(snapshot, args.output)
    print(f"Wrote {snapshot['product_count']} hammer drills to {args.output}")


if __name__ == "__main__":
    main()
