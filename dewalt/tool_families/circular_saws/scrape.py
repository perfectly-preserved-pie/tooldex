from __future__ import annotations

import argparse
from bs4 import BeautifulSoup
from fractions import Fraction
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


CATALOG_URL = "https://www.dewalt.com/products/power-tools/saws/circular-saws"
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "dewalt_circular_saws.json"
MEASUREMENT_PATTERN = re.compile(r"\d+(?:-\d+/\d+|\s+\d+/\d+)|\d+/\d+|\d+(?:\.\d+)?")
INCH_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\s+\d+/\d+)|\d+/\d+|\d+(?:\.\d+)?)\s*(?:in\.|\")",
    re.I,
)
RPM_CONTEXT_PATTERN = re.compile(r"(\d[\d,]*)\s*rpm", re.I)
MWO_PATTERN = re.compile(r"(\d[\d,]*)\s*mwo", re.I)
BEVEL_PATTERN = re.compile(r"bevel capacity(?: of)?\s*(\d+(?:\.\d+)?)", re.I)
RANGE_BEVEL_PATTERN = re.compile(r"0\s*-\s*(\d+(?:\.\d+)?)\s*°?\s*bevel capacity", re.I)
DEPTH_90_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*in\.\s*at\s+a?\s*90",
    re.I,
)
DEPTH_45_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*in\.\s*at\s+a?\s*45",
    re.I,
)
GENERIC_DEPTH_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*in\.\s+depth of cut",
    re.I,
)


def fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch a DEWALT page with retrying plain ``requests.get`` calls.

    Args:
        url: Fully qualified page URL to request.
        timeout: Socket timeout in seconds for the request.

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


def parse_measurement_value(raw_value: str | None) -> float | None:
    """Parse a decimal, fraction, or mixed fraction measurement into a float.

    Args:
        raw_value: Raw measurement string.

    Returns:
        The parsed measurement value, or ``None`` when unavailable.
    """
    if not raw_value:
        return None

    for token in MEASUREMENT_PATTERN.findall(raw_value):
        cleaned = token.strip().replace('"', "")
        if re.fullmatch(r"\d+(?:-\d+/\d+|\s+\d+/\d+)", cleaned):
            whole_part, fraction_part = re.split(r"[- ]", cleaned, maxsplit=1)
            return int(whole_part) + float(Fraction(fraction_part))
        if re.fullmatch(r"\d+/\d+", cleaned):
            return float(Fraction(cleaned))
        try:
            return float(cleaned)
        except ValueError:
            continue
    return None


def format_fraction_label(value: float | None) -> str | None:
    """Format an inch measurement as a compact fractional label.

    Args:
        value: Numeric measurement value.

    Returns:
        A normalized string such as ``"7-1/4"`` or ``"5/8"``, or ``None``.
    """
    if value is None:
        return None

    fraction = Fraction(value).limit_denominator(16)
    whole_part = fraction.numerator // fraction.denominator
    remainder = fraction.numerator % fraction.denominator

    if remainder == 0:
        return str(whole_part)
    if whole_part == 0:
        return f"{remainder}/{fraction.denominator}"
    return f"{whole_part}-{remainder}/{fraction.denominator}"


def normalize_size_label(raw_value: str | None) -> str | None:
    """Normalize an inch-based size label for saw measurements.

    Args:
        raw_value: Raw measurement string.

    Returns:
        A normalized fractional label, or ``None`` when unavailable.
    """
    numeric_value = parse_measurement_value(raw_value)
    if numeric_value is not None:
        return format_fraction_label(numeric_value)
    if raw_value:
        return normalize_text(raw_value)
    return None


def parse_battery_type(specs: dict[str, str]) -> str | None:
    """Parse the circular-saw battery chemistry label when present.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        The battery type label, or ``None`` when unavailable.
    """
    value = specs.get("Battery Chemistry") or specs.get("Battery Type")
    if value and MAX_VOLTAGE_PATTERN.search(value):
        return None
    return value


def parse_saw_type(title: str) -> str:
    """Parse the circular-saw subtype from the product title.

    Args:
        title: Product title string.

    Returns:
        A normalized saw-type label.
    """
    lowered = title.lower()
    if "metal cutting" in lowered:
        return "Metal Cutting"
    if "worm drive" in lowered:
        return "Worm Drive"
    return "Circular Saw"


def parse_size_label(
    specs: dict[str, str],
    field_name: str,
    title: str,
) -> str | None:
    """Parse and normalize a size label from specs or the title.

    Args:
        specs: Parsed specification label-value map.
        field_name: Specification field to prefer.
        title: Product title string used as a fallback source.

    Returns:
        A normalized inch-based size label, or ``None`` when unavailable.
    """
    raw_value = specs.get(field_name)
    if raw_value:
        return normalize_size_label(raw_value)

    if field_name != "Blade Diameter [in]":
        return None

    match = INCH_PATTERN.search(title)
    if match:
        return normalize_size_label(match.group(1))
    return None


def parse_bevel_capacity(specs: dict[str, str], all_text: str) -> float | None:
    """Parse the maximum bevel capacity in degrees.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        The maximum bevel-capacity value, or ``None`` when unavailable.
    """
    value = parse_float_value(specs.get("Bevel Capacity [deg]"))
    if value is not None:
        return value

    for pattern in (RANGE_BEVEL_PATTERN, BEVEL_PATTERN):
        match = pattern.search(all_text)
        if match:
            return float(match.group(1))
    return None


def parse_depth_from_text(pattern: re.Pattern[str], all_text: str) -> float | None:
    """Parse a cut-depth value from narrative feature text.

    Args:
        pattern: Regular-expression pattern for the target depth.
        all_text: Combined product text used for matching.

    Returns:
        The parsed cut-depth value, or ``None`` when unavailable.
    """
    match = pattern.search(all_text)
    if not match:
        return None
    return parse_measurement_value(match.group(1))


def parse_depth_cut_90(specs: dict[str, str], all_text: str) -> float | None:
    """Parse the maximum depth of cut at 90 degrees.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        The parsed cut-depth value, or ``None`` when unavailable.
    """
    for field_name in (
        "Max. Depth of Cut at 90 degrees [in]",
        "Max. Depth of Cut at 90° [in]",
        "Max. Cutting/Sawing Depth [in]",
        "Cutting Capacity [in]",
    ):
        value = parse_measurement_value(specs.get(field_name))
        if value is not None:
            return value

    return parse_depth_from_text(DEPTH_90_PATTERN, all_text) or parse_depth_from_text(
        GENERIC_DEPTH_PATTERN,
        all_text,
    )


def parse_depth_cut_45(specs: dict[str, str], all_text: str) -> float | None:
    """Parse the maximum depth of cut at 45 degrees.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        The parsed cut-depth value, or ``None`` when unavailable.
    """
    for field_name in (
        "Max. Depth of Cut at 45 degrees [in]",
        "Max. Depth of Cut at 45° [in]",
    ):
        value = parse_measurement_value(specs.get(field_name))
        if value is not None:
            return value

    return parse_depth_from_text(DEPTH_45_PATTERN, all_text)


def parse_rpm_max(specs: dict[str, str], all_text: str) -> int | None:
    """Parse the highest published no-load speed value.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        The maximum RPM value, or ``None`` when unavailable.
    """
    value = parse_int_value(specs.get("No Load Speed [RPM]") or specs.get("Speed [rpm]"))
    if value is not None:
        return value

    matches = [int(token.replace(",", "")) for token in RPM_CONTEXT_PATTERN.findall(all_text)]
    return max(matches) if matches else None


def parse_max_watts_out(specs: dict[str, str], all_text: str) -> int | None:
    """Parse the maximum published power output in watts.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        The maximum watts-out value, or ``None`` when unavailable.
    """
    for field_name in ("Max. Watts Out [W]", "Max. Power [MWO]", "Power [W]"):
        value = parse_int_value(specs.get(field_name))
        if value is not None:
            return value

    matches = [int(token.replace(",", "")) for token in MWO_PATTERN.findall(all_text)]
    return max(matches) if matches else None


def parse_weight_lbs(specs: dict[str, str]) -> float | None:
    """Parse the preferred tool weight in pounds.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        Tool weight in pounds, with kilograms converted as a fallback.
    """
    for field_name in ("Weight (w/o Battery) [lbs]", "Product Weight [lbs]", "Weight [lbs]"):
        value = parse_float_value(specs.get(field_name))
        if value is not None:
            return value

    weight_kg = parse_float_value(specs.get("Product Weight [Kg]"))
    if weight_kg is not None:
        return round(weight_kg * 2.20462, 2)
    return None


def parse_bool_feature(
    specs: dict[str, str],
    field_name: str,
    lowered_text: str,
    needles: tuple[str, ...],
) -> bool | None:
    """Parse a boolean feature from specs or keyword fallbacks.

    Args:
        specs: Parsed specification label-value map.
        field_name: Preferred spec field name.
        lowered_text: Lower-cased combined product text.
        needles: Keyword substrings that imply the feature is present.

    Returns:
        ``True``, ``False``, or ``None`` when the feature is unavailable.
    """
    value = parse_bool_value(specs.get(field_name))
    if value is not None:
        return value
    if any(needle in lowered_text for needle in needles):
        return True
    return None


def should_exclude_product(title: str, description: str) -> bool:
    """Determine whether a listed product should be excluded from this family.

    Args:
        title: Product title string.
        description: Product overview string.

    Returns:
        ``True`` when the product is outside the intended circular-saw scope.
    """
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    if "track saw" in lowered or "blade" in lowered:
        return True
    return not any(
        needle in lowered for needle in ("circular saw", "worm drive saw", "metal cutting circular saw")
    )


def listing_card_is_supported(card: dict[str, str]) -> bool:
    """Apply the circular-saw scope using listing-card metadata only.

    Args:
        card: Listing-card metadata containing title and SKU values.

    Returns:
        ``True`` when the listing card should be fetched and parsed.
    """
    title = card["title"]
    lowered = title.lower()
    if should_exclude_product(title, ""):
        return False
    if "tool only" in lowered or "corded" in lowered:
        return True
    return sku_looks_like_bare_tool(card["sku"])


def is_supported_circular_saw(row: dict[str, Any]) -> bool:
    """Apply the circular-saw product-scope rule for the dashboard.

    Args:
        row: Parsed circular-saw row.

    Returns:
        ``True`` for all corded saws and bare-tool cordless saws.
    """
    if row["power_source"] != "Cordless":
        return True
    return bool(row["tool_only"])


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse a circular-saw product page into a structured row.

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
    blade_diameter_label = parse_size_label(specs, "Blade Diameter [in]", title)
    arbor_size_label = parse_size_label(specs, "Arbor Size [in]", title)
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    tool_only = power_source == "Cordless" and (
        "tool only" in title.lower() or sku_looks_like_bare_tool(sku)
    )

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Circular Saw",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": parse_battery_type(specs),
        "battery_capacity_ah": parse_float_value(specs.get("Battery Capacity [Ah]")),
        "saw_type": parse_saw_type(title),
        "blade_diameter_label": blade_diameter_label,
        "blade_diameter_in": parse_measurement_value(blade_diameter_label),
        "arbor_size_label": arbor_size_label,
        "arbor_size_in": parse_measurement_value(arbor_size_label),
        "bevel_capacity_deg": parse_bevel_capacity(specs, all_text),
        "depth_cut_90_in": parse_depth_cut_90(specs, all_text),
        "depth_cut_45_in": parse_depth_cut_45(specs, all_text),
        "rpm_max": parse_rpm_max(specs, all_text),
        "max_watts_out": parse_max_watts_out(specs, all_text),
        "tool_length_in": parse_tool_length_in(specs),
        "weight_lbs": parse_weight_lbs(specs),
        "brushless": parse_bool_feature(specs, "Is Brushless?", lowered, ("brushless",)),
        "led_light": parse_bool_feature(specs, "Has LED Light?", lowered, (" led ", "onboard led", "integrated led")),
        "electric_brake": parse_bool_feature(
            specs,
            "Has Electronic Brake?",
            lowered,
            ("electric brake", "electronic brake", "blade brake"),
        ),
        "dust_extraction": parse_bool_feature(
            specs,
            "Has Dust Extraction?",
            lowered,
            ("dust port", "dust extraction", "airlock", "chip collector"),
        ),
        "rafter_hook": parse_bool_feature(
            specs,
            "Has Rafter Hook?",
            lowered,
            ("rafter hook", "hang hook"),
        ),
        "tool_connect_ready": "tool connect" in lowered or "chip ready" in lowered,
        "power_detect": "power detect" in lowered,
        "kit": (" kit" in title.lower())
        or title.lower().endswith("kit")
        or parse_bool_value(specs.get("Is it a Set?")) is True,
        "tool_only": tool_only,
        "battery_included": parse_bool_value(specs.get("Is Battery Included?"))
        if specs.get("Is Battery Included?") is not None
        else any("battery" in item.lower() for item in includes),
        "charger_included": any("charger" in item.lower() for item in includes),
        "description": description,
        "features": primary_features,
        "additional_features": additional_features,
        "includes": includes,
        "applications": applications,
        "disclaimers": disclaimers,
    }


def fetch_listing_pages() -> dict[str, str]:
    """Fetch all paginated circular-saw catalog listing pages.

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
    """Collect unique product cards from the circular-saw listing pages.

    Args:
        listing_pages: Mapping of listing-page URLs to HTML strings.

    Returns:
        A list of deduplicated listing-card dictionaries.
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
    """Build a circular-saw snapshot by scraping the live DEWALT catalog.

    Args:
        None.

    Returns:
        A JSON-serializable snapshot payload for circular saws.
    """
    listing_pages = fetch_listing_pages()
    product_cards = collect_product_cards(listing_pages)
    candidate_cards = [card for card in product_cards if listing_card_is_supported(card)]

    rows = []
    for card in candidate_cards:
        html_text = fetch_url(card["url"])
        parsed_row = parse_product_page(card["url"], html_text)
        if parsed_row and is_supported_circular_saw(parsed_row):
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
    """Build a circular-saw snapshot from cached product-page HTML files.

    Args:
        source_dir: Directory containing saved DEWALT product-page HTML files.

    Returns:
        A JSON-serializable snapshot payload for circular saws.
    """
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_circular_saw(parsed_row):
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
    """Persist a circular-saw snapshot to disk as formatted JSON.

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
    """Parse command-line arguments for the circular-saw scraper.

    Args:
        None.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Scrape DEWALT circular-saw product data.")
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
    """Run the circular-saw scraper CLI.

    Args:
        None.

    Returns:
        None. The generated snapshot is written to disk and summarized on stdout.
    """
    args = parse_args()
    if args.source_dir:
        snapshot = build_snapshot_from_directory(args.source_dir)
    else:
        snapshot = build_snapshot_from_live_catalog()

    save_snapshot(snapshot, args.output)
    print(f"Wrote {snapshot['product_count']} circular saws to {args.output}")


if __name__ == "__main__":
    main()
