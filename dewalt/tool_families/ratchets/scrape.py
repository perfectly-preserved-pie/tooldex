from __future__ import annotations

import argparse
from bs4 import BeautifulSoup
import json
from pathlib import Path
import re
from typing import Any

import requests

from dewalt.tool_families.drill_drivers.scrape import (
    MAX_VOLTAGE_PATTERN,
    PAGE_PATTERN,
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
    parse_rpm_max,
    parse_series,
    parse_specifications_table,
    parse_tool_length_in,
    parse_voltage_system,
    sku_looks_like_bare_tool,
)


CATALOG_URL = "https://www.dewalt.com/products/power-tools/ratchets/ratchets"
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "dewalt_ratchets.json"
SIZE_PATTERN = re.compile(r"(\d+/\d+|\d+(?:\.\d+)?)\s*(?:in\.|\")", re.I)


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


def parse_power_source(specs: dict[str, str], title: str, all_text: str) -> str:
    """Parse the ratchet power-source classification.

    Args:
        specs: Parsed specification label-value map.
        title: Product title string.
        all_text: Combined product text used as a fallback source.

    Returns:
        A normalized power-source label.
    """
    raw_value = specs.get("Power Source")
    if raw_value:
        lowered = normalize_text(raw_value).lower()
        if lowered.startswith("cordless") or lowered == "battery":
            return "Cordless"
        if lowered.startswith("corded"):
            return "Corded"

    if MAX_VOLTAGE_PATTERN.search(title):
        return "Cordless"

    lowered = all_text.lower()
    if (
        specs.get("Battery Voltage [V]")
        or specs.get("Battery Type")
        or specs.get("Battery Chemistry")
        or "cordless" in lowered
        or "tool only" in lowered
    ):
        return "Cordless"
    return "Corded"


def parse_battery_type(specs: dict[str, str]) -> str | None:
    """Parse the ratchet battery chemistry label when present.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        The battery chemistry label, or ``None`` when unavailable.
    """
    value = specs.get("Battery Chemistry") or specs.get("Battery Type")
    if value and "v max" in value.lower():
        return None
    return value


def parse_drive_size_display(specs: dict[str, str], title: str, description: str) -> str | None:
    """Parse the displayed ratchet drive-size label.

    Args:
        specs: Parsed specification label-value map.
        title: Product title string.
        description: Product overview string.

    Returns:
        A display-ready drive-size string, or ``None`` when unavailable.
    """
    raw_value = specs.get("Anvil Size [in]") or specs.get("Drive Size [in]")
    if not raw_value:
        for source in (title, description):
            match = SIZE_PATTERN.findall(source)
            if match:
                raw_value = ", ".join(match)
                break

    if not raw_value:
        return None

    parts = [
        normalize_chuck_size_label(part)
        for part in re.split(r"\s*,\s*", raw_value)
        if part.strip()
    ]
    normalized_parts: list[str] = []
    for part in parts:
        if part and part not in normalized_parts:
            normalized_parts.append(part)
    if not normalized_parts:
        return None
    if len(normalized_parts) == 1:
        return f"{normalized_parts[0]} in."
    return " & ".join(f"{part} in." for part in normalized_parts)


def parse_head_type(specs: dict[str, str], title: str, all_text: str) -> str | None:
    """Parse the ratchet head style.

    Args:
        specs: Parsed specification label-value map.
        title: Product title string.
        all_text: Combined product text used as a fallback source.

    Returns:
        The head style label, or ``None`` when unavailable.
    """
    value = specs.get("Ratchet Head Type")
    if value:
        return value

    lowered = f"{title} {all_text}".lower()
    if "sealed head" in lowered:
        return "Sealed Head"
    if "ratchet" in lowered:
        return "Standard"
    return None


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


def parse_variable_speed(specs: dict[str, str], lowered_text: str) -> bool | None:
    """Parse whether the ratchet advertises variable-speed control.

    Args:
        specs: Parsed specification label-value map.
        lowered_text: Lower-cased combined product text.

    Returns:
        ``True`` or ``False`` when the value can be resolved, otherwise ``None``.
    """
    for field_name in ("Has Variable Speed Trigger?", "Has Variable Speed?"):
        value = parse_bool_value(specs.get(field_name))
        if value is not None:
            return value
    if "variable speed" in lowered_text:
        return True
    return None


def should_exclude_product(title: str, description: str) -> bool:
    """Determine whether a listed product should be excluded from this family.

    Args:
        title: Product title string.
        description: Product overview string.

    Returns:
        ``True`` when the product is outside the intended ratchet scope.
    """
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    if "ratchet" not in lowered:
        return True
    return False


def listing_card_is_candidate(card: dict[str, str]) -> bool:
    """Exclude obvious non-tool accessories before fetching product pages.

    Args:
        card: Listing-card dictionary with title and URL metadata.

    Returns:
        ``True`` when the listing card looks like a ratchet.
    """
    return not should_exclude_product(card["title"], "")


def is_tool_only_cordless(
    sku: str,
    title: str,
    description: str,
    specs: dict[str, str],
) -> bool:
    """Infer whether a cordless ratchet listing is the bare-tool SKU.

    Args:
        sku: Product SKU string.
        title: Product title string.
        description: Product overview string.
        specs: Parsed specification label-value map.

    Returns:
        ``True`` when the product looks like a bare-tool cordless SKU.
    """
    lowered = f"{title} {description}".lower()
    is_set = parse_bool_value(specs.get("Is it a Set?"))
    return any(
        (
            "tool only" in lowered,
            is_set is False,
            sku_looks_like_bare_tool(sku),
        )
    )


def is_supported_ratchet(row: dict[str, Any]) -> bool:
    """Apply the ratchet product-scope rule for the dashboard.

    Args:
        row: Parsed ratchet row.

    Returns:
        ``True`` for all corded ratchets and bare-tool cordless ratchets.
    """
    if row["power_source"] == "Cordless":
        return bool(row["tool_only"])
    return row["power_source"] == "Corded"


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse a ratchet product page into a structured row.

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

    power_source = parse_power_source(specs, title, all_text)
    voltage_system, max_voltage_v = parse_voltage_system(specs, power_source, all_text)
    no_load_speed = specs.get("No Load Speed [RPM]") or specs.get("RPM")
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    tool_only = power_source == "Cordless" and is_tool_only_cordless(
        sku,
        title,
        description,
        specs,
    )

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Ratchet",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": parse_battery_type(specs),
        "battery_capacity_ah": parse_float_value(specs.get("Battery Capacity [Ah]")),
        "drive_size_display": parse_drive_size_display(specs, title, description),
        "head_type": parse_head_type(specs, title, all_text),
        "no_load_speed": no_load_speed,
        "rpm_max": parse_rpm_max(no_load_speed),
        "max_torque_ft_lbs": parse_float_value(specs.get("Max. Torque [ft-lbs]")),
        "max_torque_nm": parse_float_value(specs.get("Max. Torque [Nm]")),
        "tool_length_in": parse_tool_length_in(specs),
        "weight_lbs": parse_weight_lbs(specs),
        "brushless": parse_bool_value(specs.get("Is Brushless?")),
        "variable_speed": parse_variable_speed(specs, lowered),
        "led_light": parse_bool_value(specs.get("Has LED Light?")),
        "fw_rev_switch": parse_bool_value(specs.get("Has FW / REV Switch?")),
        "extended_reach": "extended reach" in lowered,
        "kit": (" kit" in title.lower())
        or title.lower().endswith("kit")
        or parse_bool_value(specs.get("Is it a Set?")) is True,
        "tool_only": tool_only,
        "battery_included": parse_bool_value(specs.get("Is Battery Included?")),
        "charger_included": any("charger" in item.lower() for item in includes),
        "description": description,
        "features": primary_features,
        "additional_features": additional_features,
        "includes": includes,
        "applications": applications,
        "disclaimers": disclaimers,
    }


def fetch_listing_pages() -> dict[str, str]:
    """Fetch all paginated ratchet catalog listing pages.

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
    """Collect unique product cards from the ratchet listing pages.

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
    """Build a ratchet snapshot by scraping the live DEWALT catalog.

    Args:
        None.

    Returns:
        A JSON-serializable snapshot payload for ratchets.
    """
    listing_pages = fetch_listing_pages()
    product_cards = collect_product_cards(listing_pages)
    candidate_cards = [card for card in product_cards if listing_card_is_candidate(card)]

    rows = []
    for card in candidate_cards:
        html_text = fetch_url(card["url"])
        parsed_row = parse_product_page(card["url"], html_text)
        if parsed_row and is_supported_ratchet(parsed_row):
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
    """Build a ratchet snapshot from cached product-page HTML files.

    Args:
        source_dir: Directory containing saved DEWALT product-page HTML files.

    Returns:
        A JSON-serializable snapshot payload for ratchets.
    """
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_ratchet(parsed_row):
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
    """Persist a ratchet snapshot to disk as formatted JSON.

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
    """Parse command-line arguments for the ratchet scraper.

    Args:
        None.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Scrape DEWALT ratchet product data.")
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
    """Run the ratchet scraper CLI.

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
    print(f"Wrote {snapshot['product_count']} ratchets to {args.output}")


if __name__ == "__main__":
    main()
