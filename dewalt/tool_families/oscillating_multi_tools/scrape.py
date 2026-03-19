from __future__ import annotations

import argparse
from bs4 import BeautifulSoup
import json
from pathlib import Path
import re
from typing import Any

import requests

from dewalt.tool_families.drill_drivers.scrape import (
    PAGE_PATTERN,
    extract_section_items,
    extract_text_items,
    format_iso_now,
    get_soup_text,
    normalize_text,
    parse_bool_value,
    parse_canonical_url,
    parse_float_value,
    parse_int_value,
    parse_nominal_voltage_v,
    parse_power_source,
    parse_series,
    parse_specifications_table,
    parse_tool_length_in,
    parse_voltage_system,
    sku_looks_like_bare_tool,
)


CATALOG_URL = (
    "https://www.dewalt.com/products/power-tools/multi-function-tools/oscillating-multi-tools"
)
DATA_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "dewalt_oscillating_multi_tools.json"
)
SPEED_COUNT_PATTERN = re.compile(r"(\d+)\s*-\s*speed|(\d+)\s+speed", re.I)


def fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch a DEWALT page with retrying plain ``requests.get`` calls.

    Args:
        url: Fully qualified page URL to request.
        timeout: Maximum request time in seconds.

    Returns:
        The decoded HTML body as a string.
    """
    last_error: Exception | None = None
    for request_timeout in (timeout, timeout, timeout * 2):
        try:
            response = requests.get(url, timeout=request_timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Failed to fetch {url}")


def parse_speed_count(specs: dict[str, str], title: str) -> int | None:
    """Parse the number of speed settings from specs or the product title.

    Args:
        specs: Parsed specification label-value map.
        title: Product title string.

    Returns:
        The number of speed settings, or ``None`` when unavailable.
    """
    speed_count = parse_int_value(specs.get("Number of Speed Settings"))
    if speed_count is not None:
        return speed_count

    match = SPEED_COUNT_PATTERN.search(title)
    if not match:
        return None
    return int(match.group(1) or match.group(2))


def parse_weight_lbs(specs: dict[str, str]) -> float | None:
    """Parse the preferred bare-tool weight in pounds when available.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        The tool weight when available, otherwise the product weight.
    """
    for field_name in ("Tool Weight [lbs]", "Product Weight [lbs]"):
        value = parse_float_value(specs.get(field_name))
        if value is not None:
            return value
    return None


def parse_tool_free_accessory_change(specs: dict[str, str]) -> bool | None:
    """Parse whether the tool advertises tool-free accessory changes.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        ``True`` or ``False`` when the site publishes the value, otherwise ``None``.
    """
    for field_name in (
        "Has Tool-Free System™ Accessory Change?",
        "Has Tool-Free System Accessory Change?",
        "Has Keyless Accessory Change?",
    ):
        value = parse_bool_value(specs.get(field_name))
        if value is not None:
            return value
    return None


def should_exclude_product(title: str, description: str) -> bool:
    """Determine whether a listed product should be excluded from this family.

    Args:
        title: Product title string.
        description: Product overview string.

    Returns:
        ``True`` when the product is outside the intended oscillating multi-tool scope.
    """
    lowered = f"{title} {description}".lower()
    lowered_title = title.lower()
    if not title or title == "404 Page | DEWALT":
        return True
    if not any(
        keyword in lowered for keyword in ("multi-tool", "multi tool", "oscillating tool")
    ):
        return True
    for needle in ("blade", "sanding", "adapter", "pad", "scraper"):
        if needle in lowered_title:
            return True
    return False


def listing_card_is_candidate(card: dict[str, str]) -> bool:
    """Exclude obvious accessories before fetching product pages.

    Args:
        card: Listing-card dictionary with title and URL metadata.

    Returns:
        ``True`` when the listing card looks like an oscillating multi-tool.
    """
    return not should_exclude_product(card["title"], "")


def is_tool_only_cordless(sku: str, title: str, specs: dict[str, str]) -> bool:
    """Infer whether a cordless oscillating multi-tool listing is bare-tool.

    Args:
        sku: Product SKU string.
        title: Product title string.
        specs: Parsed specification label-value map.

    Returns:
        ``True`` when the product looks like a bare-tool cordless SKU.
    """
    return any(
        (
            "tool only" in title.lower(),
            parse_bool_value(specs.get("Is it a Set?")) is False,
            sku_looks_like_bare_tool(sku),
        )
    )


def is_supported_oscillating_multi_tool(row: dict[str, Any]) -> bool:
    """Apply the oscillating multi-tool product-scope rule for the dashboard.

    Args:
        row: Parsed oscillating multi-tool row.

    Returns:
        ``True`` for all corded tools and bare-tool cordless tools.
    """
    if row["power_source"] == "Cordless":
        return bool(row["tool_only"])
    return row["power_source"] == "Corded"


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse an oscillating multi-tool product page into a structured row.

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
    oscillations_per_min = parse_int_value(specs.get("Oscillations Per Minute"))
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    tool_only = power_source == "Cordless" and is_tool_only_cordless(sku, title, specs)

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Oscillating Multi-Tool",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": specs.get("Battery Type"),
        "battery_capacity_ah": parse_float_value(specs.get("Battery Capacity [Ah]")),
        "speed_count": parse_speed_count(specs, title),
        "oscillations_per_min": oscillations_per_min,
        "tool_length_in": parse_tool_length_in(specs),
        "weight_lbs": parse_weight_lbs(specs),
        "brushless": parse_bool_value(specs.get("Is Brushless?"))
        if specs.get("Is Brushless?") is not None
        else "brushless" in lowered,
        "variable_speed": parse_bool_value(specs.get("Has Variable Speed?")),
        "led_light": parse_bool_value(specs.get("Has LED Light?")),
        "lock_on_switch": parse_bool_value(specs.get("Has Lock On Switch?")),
        "tool_free_accessory_change": parse_tool_free_accessory_change(specs),
        "kit": (" kit" in title.lower())
        or title.lower().endswith("kit")
        or parse_bool_value(specs.get("Is it a Set?")) is True,
        "tool_only": tool_only,
        "battery_included": (
            (parse_int_value(specs.get("Battery Quantity")) or 0) > 0
            or any("battery" in item.lower() for item in includes)
        ),
        "charger_included": any("charger" in item.lower() for item in includes),
        "description": description,
        "features": primary_features,
        "additional_features": additional_features,
        "includes": includes,
        "applications": applications,
        "disclaimers": disclaimers,
    }


def fetch_listing_pages() -> dict[str, str]:
    """Fetch all paginated oscillating multi-tool catalog listing pages.

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


def collect_product_cards(listing_pages: dict[str, str]) -> list[dict[str, str]]:
    """Collect unique product cards from the oscillating multi-tool listing pages.

    Args:
        listing_pages: Mapping of listing-page URLs to HTML strings.

    Returns:
        A list of unique product-card dictionaries with URL, title, and SKU.
    """
    cards: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for html_text in listing_pages.values():
        soup = BeautifulSoup(html_text, "html.parser")
        for link in soup.select("a.card-link.product-title[href*='/product/']"):
            href = link.get("href")
            if not href:
                continue

            url = href.split("?", 1)[0]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title = get_soup_text(link)
            sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
            cards.append({"url": url, "title": title, "sku": sku})

    return cards


def build_snapshot_from_live_catalog() -> dict[str, Any]:
    """Build an oscillating multi-tool snapshot by scraping the live DEWALT catalog.

    Args:
        None.

    Returns:
        A JSON-serializable snapshot payload for oscillating multi-tools.
    """
    listing_pages = fetch_listing_pages()
    product_cards = collect_product_cards(listing_pages)
    candidate_cards = [card for card in product_cards if listing_card_is_candidate(card)]

    rows = []
    for card in candidate_cards:
        html_text = fetch_url(card["url"])
        parsed_row = parse_product_page(card["url"], html_text)
        if parsed_row and is_supported_oscillating_multi_tool(parsed_row):
            rows.append(parsed_row)

    rows.sort(key=lambda row: row["sku"])
    return {
        "scraped_at": format_iso_now(),
        "catalog_url": CATALOG_URL,
        "listing_page_count": len(listing_pages),
        "raw_product_count": len(product_cards),
        "product_count": len(rows),
        "excluded_product_count": len(product_cards) - len(rows),
        "rows": rows,
    }


def build_snapshot_from_directory(source_dir: Path) -> dict[str, Any]:
    """Build an oscillating multi-tool snapshot from cached product-page HTML files.

    Args:
        source_dir: Directory containing saved DEWALT product-page HTML files.

    Returns:
        A JSON-serializable snapshot payload for oscillating multi-tools.
    """
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_oscillating_multi_tool(parsed_row):
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
    """Persist an oscillating multi-tool snapshot to disk as formatted JSON.

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
    """Parse command-line arguments for the oscillating multi-tool scraper.

    Args:
        None.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Scrape DEWALT oscillating multi-tool product data."
    )
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
    """Run the oscillating multi-tool scraper CLI.

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
    print(f"Wrote {snapshot['product_count']} oscillating multi-tools to {args.output}")


if __name__ == "__main__":
    main()
