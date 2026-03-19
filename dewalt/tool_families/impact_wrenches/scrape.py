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


CATALOG_URL = "https://www.dewalt.com/products/power-tools/impact-drivers-wrenches/impact-wrenches"
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "dewalt_impact_wrenches.json"
SIZE_PATTERN = re.compile(r"(\d+/\d+|\d+(?:\.\d+)?)\s*(?:in\.|\")", re.I)


def fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch a DEWALT page with retrying plain ``requests.get`` calls."""
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
    """Parse the wrench power-source classification."""
    raw_value = specs.get("Power Source")
    if raw_value:
        lowered = normalize_text(raw_value).lower()
        if lowered.startswith("cordless") or lowered == "battery":
            return "Cordless"
        if lowered.startswith("corded"):
            return "Corded"
        if "pneumatic" in lowered or "air" in lowered:
            return "Pneumatic"

    if MAX_VOLTAGE_PATTERN.search(title):
        return "Cordless"

    lowered = all_text.lower()
    if (
        specs.get("Battery Voltage [V]")
        or specs.get("Battery Type")
        or specs.get("Battery Chemistry")
        or "cordless" in lowered
        or "battery sold separately" in lowered
        or "battery & charger sold separately" in lowered
        or "battery and charger sold separately" in lowered
        or "tool only" in lowered
    ):
        return "Cordless"
    if "pneumatic" in lowered or "air impact wrench" in lowered:
        return "Pneumatic"
    return "Corded"


def parse_battery_type(specs: dict[str, str]) -> str | None:
    """Parse the impact-wrench battery chemistry label when present."""
    value = specs.get("Battery Chemistry") or specs.get("Battery Type")
    if value and "v max" in value.lower():
        return None
    return value


def parse_drive_size_label(specs: dict[str, str], title: str, description: str) -> str | None:
    """Parse the displayed square-drive or chuck size for an impact wrench."""
    for field_name in ("Anvil Size [in]", "Drive Size [in]", "Chuck Size [in]"):
        raw_value = specs.get(field_name)
        if raw_value:
            return normalize_chuck_size_label(raw_value)

    for source in (title, description):
        match = SIZE_PATTERN.search(source)
        if match:
            return normalize_chuck_size_label(match.group(1))
    return None


def parse_anvil_type(specs: dict[str, str], all_text: str) -> str | None:
    """Parse the wrench anvil or retention type."""
    value = specs.get("Anvil Type")
    if value:
        return value

    lowered = all_text.lower()
    if "detent pin" in lowered:
        return "Detent Pin"
    if "hog ring" in lowered:
        return "Hog Ring"
    if "quick release" in lowered:
        return "Quick Release"
    return None


def parse_torque_class(title: str) -> str | None:
    """Parse the marketing torque class from the product title."""
    lowered = title.lower()
    if "high torque" in lowered:
        return "High Torque"
    if "mid-range" in lowered or "mid range" in lowered or "mid-torque" in lowered:
        return "Mid-Range"
    if "compact" in lowered:
        return "Compact"
    return None


def parse_impact_rate_bpm(specs: dict[str, str]) -> int | None:
    """Parse the highest published impact rate from the specifications map."""
    raw_value = (
        specs.get("Impact Rate per Min.")
        or specs.get("Impacts/Min")
        or specs.get("Blows Per Minute")
        or specs.get("Blows/Min")
    )
    if not raw_value:
        return None
    return parse_rpm_max(raw_value)


def parse_weight_lbs(specs: dict[str, str]) -> float | None:
    """Parse the preferred bare-tool weight in pounds when available."""
    for field_name in (
        "Weight (w/o Battery) [lbs]",
        "Product Weight [lbs]",
        "Weight (Including Battery) [lbs]",
    ):
        value = parse_float_value(specs.get(field_name))
        if value is not None:
            return value
    return None


def parse_variable_speed(specs: dict[str, str], lowered_text: str) -> bool | None:
    """Parse whether the wrench advertises variable-speed control."""
    for field_name in ("Has Variable Speed?", "Has Variable Speed Trigger?"):
        value = parse_bool_value(specs.get(field_name))
        if value is not None:
            return value
    if "variable speed" in lowered_text:
        return True
    return None


def parse_brushless(specs: dict[str, str], lowered_text: str) -> bool | None:
    """Parse whether the wrench is brushless, with a text fallback for bad specs."""
    value = parse_bool_value(specs.get("Is Brushless?"))
    if value is False and "brushless" in lowered_text:
        return True
    if value is not None:
        return value
    if "brushless" in lowered_text:
        return True
    return None


def should_exclude_product(title: str, description: str) -> bool:
    """Determine whether a listed product should be excluded from this family."""
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    for needle in ("protective rubber boot", "rubber boot", "cover", "guard"):
        if needle in lowered:
            return True
    if "impact wrench" not in lowered and "detent pin anvil" not in lowered:
        return True
    return False


def listing_card_is_candidate(card: dict[str, str]) -> bool:
    """Exclude obvious non-tool accessories before fetching product pages."""
    return not should_exclude_product(card["title"], "")


def is_tool_only_cordless(
    sku: str,
    title: str,
    description: str,
    specs: dict[str, str],
) -> bool:
    """Infer whether a cordless wrench listing is the bare-tool SKU."""
    lowered = f"{title} {description}".lower()
    is_set = parse_bool_value(specs.get("Is it a Set?"))
    battery_quantity = parse_int_value(
        specs.get("Battery Quantity") or specs.get("Number of Batteries Included")
    )
    return any(
        (
            "tool only" in lowered,
            "battery sold separately" in lowered,
            "battery & charger sold separately" in lowered,
            "battery and charger sold separately" in lowered,
            "charger sold separately" in lowered,
            is_set is False,
            battery_quantity == 0,
            sku_looks_like_bare_tool(sku),
        )
    )


def is_supported_impact_wrench(row: dict[str, Any]) -> bool:
    """Apply the impact-wrench product-scope rule for the dashboard."""
    if row["power_source"] == "Cordless":
        return bool(row["tool_only"])
    return row["power_source"] == "Corded"


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse an impact-wrench product page into a structured row."""
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
    drive_size_label = parse_drive_size_label(specs, title, description)
    no_load_speed = specs.get("No Load Speed [RPM]") or specs.get("RPM")
    max_torque_ft_lbs = parse_float_value(specs.get("Max. Torque [ft-lbs]"))
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    tool_only = power_source == "Cordless" and is_tool_only_cordless(
        sku, title, description, specs
    )

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Impact Wrench",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": parse_battery_type(specs),
        "battery_capacity_ah": parse_float_value(specs.get("Battery Capacity [Ah]")),
        "drive_size_label": drive_size_label,
        "drive_size_in": parse_float_value(drive_size_label),
        "anvil_type": parse_anvil_type(specs, all_text),
        "torque_class": parse_torque_class(title),
        "no_load_speed": no_load_speed,
        "rpm_max": parse_rpm_max(no_load_speed),
        "impact_rate_bpm": parse_impact_rate_bpm(specs),
        "max_fastening_torque_ft_lbs": parse_float_value(
            specs.get("Max. Fastening Torque [ft-lbs]")
        )
        or max_torque_ft_lbs,
        "max_breakaway_torque_ft_lbs": parse_float_value(
            specs.get("Max. Breakaway Torque [ft-lbs]")
            or specs.get("Breakaway Torque [ft-lbs]")
        ),
        "tool_length_in": parse_tool_length_in(specs),
        "weight_lbs": parse_weight_lbs(specs),
        "brushless": parse_brushless(specs, lowered),
        "variable_speed": parse_variable_speed(specs, lowered),
        "led_light": parse_bool_value(specs.get("Has LED Light?")),
        "precision_wrench": "precision wrench" in lowered,
        "kit": (" kit" in title.lower())
        or title.lower().endswith("kit")
        or parse_bool_value(specs.get("Is it a Set?")) is True,
        "tool_only": tool_only,
        "battery_included": (
            parse_int_value(specs.get("Battery Quantity")) or 0
        )
        > 0,
        "charger_included": any("charger" in item.lower() for item in includes),
        "tool_connect_ready": "tool connect" in lowered,
        "lanyard_ready": "lanyard ready" in lowered,
        "description": description,
        "features": primary_features,
        "additional_features": additional_features,
        "includes": includes,
        "applications": applications,
        "disclaimers": disclaimers,
    }


def fetch_listing_pages() -> dict[str, str]:
    """Fetch all paginated impact-wrench catalog listing pages."""
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
    """Collect unique product cards from the impact-wrench listing pages."""
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
    """Build an impact-wrench snapshot by scraping the live DEWALT catalog."""
    listing_pages = fetch_listing_pages()
    product_cards = collect_product_cards(listing_pages)
    candidate_cards = [card for card in product_cards if listing_card_is_candidate(card)]

    rows = []
    for card in candidate_cards:
        html_text = fetch_url(card["url"])
        parsed_row = parse_product_page(card["url"], html_text)
        if parsed_row and is_supported_impact_wrench(parsed_row):
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
    """Build an impact-wrench snapshot from cached product-page HTML files."""
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_impact_wrench(parsed_row):
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
    """Persist an impact-wrench snapshot to disk as formatted JSON."""
    from dewalt.data import sanitize_snapshot_payload

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sanitize_snapshot_payload(snapshot), indent=2))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the impact-wrench scraper."""
    parser = argparse.ArgumentParser(description="Scrape DEWALT impact-wrench product data.")
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
    """Run the impact-wrench scraper CLI."""
    args = parse_args()
    if args.source_dir:
        snapshot = build_snapshot_from_directory(args.source_dir)
    else:
        snapshot = build_snapshot_from_live_catalog()

    save_snapshot(snapshot, args.output)
    print(f"Wrote {snapshot['product_count']} impact wrenches to {args.output}")


if __name__ == "__main__":
    main()
