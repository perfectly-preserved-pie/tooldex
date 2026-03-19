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
    parse_power_source,
    parse_rpm_max,
    parse_series,
    parse_specifications_table,
    parse_tool_length_in,
    parse_voltage_system,
    sku_looks_like_bare_tool,
)


CATALOG_URL = "https://www.dewalt.com/products/power-tools/impact-drivers-wrenches/impact-drivers"
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "dewalt_impact_drivers.json"
CHUCK_SIZE_PATTERN = re.compile(r"(\d+/\d+|\d+(?:\.\d+)?)\s*(?:in\.|\")", re.I)
SPEED_COUNT_PATTERN = re.compile(r"(\d+)\s*-\s*speed|(\d+)\s+speed", re.I)


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


def parse_battery_type(specs: dict[str, str]) -> str | None:
    """Parse the impact-driver battery chemistry label when present."""
    value = specs.get("Battery Chemistry") or specs.get("Battery Type")
    if value and MAX_VOLTAGE_PATTERN.search(value):
        return None
    return value


def parse_chuck_size_label(specs: dict[str, str], title: str, description: str) -> str | None:
    """Parse the displayed drive-size label for an impact driver."""
    raw_value = specs.get("Chuck Size [in]")
    if raw_value:
        return normalize_chuck_size_label(raw_value)

    for source in (title, description):
        match = CHUCK_SIZE_PATTERN.search(source)
        if match:
            return normalize_chuck_size_label(match.group(1))

    lowered = f"{title} {description}".lower()
    if "impact" in lowered and "driver" in lowered and "wrench" not in lowered:
        return "1/4"
    return None


def parse_speed_count(specs: dict[str, str], title: str) -> int | None:
    """Parse the number of speed settings from specs or the product title."""
    speed_count = parse_int_value(specs.get("Number of Speed Settings"))
    if speed_count is not None:
        return speed_count

    match = SPEED_COUNT_PATTERN.search(title)
    if not match:
        return None
    return int(match.group(1) or match.group(2))


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


def is_supported_impact_driver(row: dict[str, Any]) -> bool:
    """Apply the impact-driver product-scope rule for the dashboard."""
    if row["power_source"] != "Cordless":
        return True
    return bool(row["tool_only"])


def should_exclude_product(title: str, description: str) -> bool:
    """Determine whether a listed product should be excluded from this family."""
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    if "impact wrench" in lowered:
        return True
    for needle in ("screwdriver", "impact chuck", "quick-connect impact chuck"):
        if needle in lowered:
            return True
    if "impact" not in lowered or "driver" not in lowered:
        return True
    return False


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse an impact-driver product page into a structured row."""
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
    chuck_size_label = parse_chuck_size_label(specs, title, description)
    no_load_speed = specs.get("No Load Speed [RPM]") or specs.get("RPM")
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    tool_only = power_source == "Cordless" and (
        "tool only" in title.lower() or sku_looks_like_bare_tool(sku)
    )

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Impact Driver",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": parse_battery_type(specs),
        "battery_capacity_ah": parse_float_value(specs.get("Battery Capacity [Ah]")),
        "chuck_size_label": chuck_size_label,
        "chuck_size_in": parse_float_value(chuck_size_label),
        "speed_count": parse_speed_count(specs, title),
        "no_load_speed": no_load_speed,
        "rpm_max": parse_rpm_max(no_load_speed),
        "impact_rate_bpm": parse_impact_rate_bpm(specs),
        "max_torque_in_lbs": parse_int_value(specs.get("Max. Torque [in-lbs]")),
        "max_torque_nm": parse_int_value(specs.get("Max. Torque [Nm]")),
        "power_watts": parse_int_value(
            specs.get("Power Output [W]") or specs.get("Power [W]")
        ),
        "tool_length_in": parse_tool_length_in(specs),
        "weight_lbs": parse_weight_lbs(specs),
        "brushless": parse_bool_value(specs.get("Is Brushless?"))
        if specs.get("Is Brushless?") is not None
        else "brushless" in lowered,
        "led_light": parse_bool_value(specs.get("Has LED Light?")),
        "hydraulic": "hydraulic" in lowered,
        "high_torque": "high torque" in lowered,
        "kit": " kit" in title.lower() or title.lower().endswith("kit"),
        "tool_only": tool_only,
        "battery_included": parse_bool_value(specs.get("Is Battery Included?"))
        if specs.get("Is Battery Included?") is not None
        else any("battery" in item.lower() for item in includes),
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
    """Fetch all paginated impact-driver catalog listing pages."""
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
    """Collect unique product cards from the impact-driver listing pages."""
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


def collect_product_urls(listing_pages: dict[str, str]) -> list[str]:
    """Collect unique product URLs from the impact-driver listing pages."""
    return sorted(card["url"] for card in collect_product_cards(listing_pages))


def listing_card_is_supported(card: dict[str, str]) -> bool:
    """Apply the repo's impact-driver scope using listing-card metadata only."""
    title = card["title"]
    lowered = title.lower()
    if should_exclude_product(title, ""):
        return False
    if "tool only" in lowered or "corded" in lowered:
        return True
    return sku_looks_like_bare_tool(card["sku"])


def build_snapshot_from_live_catalog() -> dict[str, Any]:
    """Build an impact-driver snapshot by scraping the live DEWALT catalog."""
    listing_pages = fetch_listing_pages()
    product_cards = collect_product_cards(listing_pages)
    candidate_cards = [card for card in product_cards if listing_card_is_supported(card)]

    rows = []
    for card in candidate_cards:
        html_text = fetch_url(card["url"])
        parsed_row = parse_product_page(card["url"], html_text)
        if parsed_row and is_supported_impact_driver(parsed_row):
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
    """Build an impact-driver snapshot from cached product-page HTML files."""
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_impact_driver(parsed_row):
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
    """Persist an impact-driver snapshot to disk as formatted JSON."""
    from dewalt.data import sanitize_snapshot_payload

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sanitize_snapshot_payload(snapshot), indent=2))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the impact-driver scraper."""
    parser = argparse.ArgumentParser(description="Scrape DEWALT impact-driver product data.")
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
    """Run the impact-driver scraper CLI."""
    args = parse_args()
    if args.source_dir:
        snapshot = build_snapshot_from_directory(args.source_dir)
    else:
        snapshot = build_snapshot_from_live_catalog()

    save_snapshot(snapshot, args.output)
    print(f"Wrote {snapshot['product_count']} impact drivers to {args.output}")


if __name__ == "__main__":
    main()
