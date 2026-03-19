from __future__ import annotations

import argparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from fractions import Fraction
import json
from pathlib import Path
import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter

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
    parse_rpm_max,
    parse_series,
    parse_specifications_table,
    parse_voltage_system,
    sku_looks_like_bare_tool,
)


CATALOG_URL = (
    "https://www.dewalt.com/products/power-tools/rotary-demolition-hammers/rotary-hammers"
)
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "dewalt_rotary_hammers.json"
SESSION = requests.Session()
SESSION.mount("http://", HTTPAdapter(max_retries=3))
SESSION.mount("https://", HTTPAdapter(max_retries=3))
MEASUREMENT_PATTERN = re.compile(r"\d+(?:[- ]\d+/\d+)|\d+/\d+|\d+(?:\.\d+)?")


def fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch a DEWALT page with ``requests`` and decode it as text.

    Args:
        url: Fully qualified page URL to request.
        timeout: Socket timeout in seconds for the request.

    Returns:
        The decoded HTML body as a string.
    """
    last_error: Exception | None = None
    for request_timeout in (timeout, timeout * 2):
        try:
            response = SESSION.get(url, timeout=request_timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Failed to fetch {url}")


def parse_measurement_value(raw_value: str | None) -> float | None:
    """Parse a decimal, simple fraction, or mixed fraction measurement.

    Args:
        raw_value: Raw measurement string from the specification table.

    Returns:
        The parsed numeric value, or ``None`` when no numeric token exists.
    """
    if not raw_value:
        return None

    for token in MEASUREMENT_PATTERN.findall(raw_value):
        cleaned = token.strip().replace('"', "")
        if re.fullmatch(r"\d+(?:[- ]\d+/\d+)", cleaned):
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
    """Format a measurement value as a compact fractional label.

    Args:
        value: Numeric measurement value in inches.

    Returns:
        A normalized string such as ``"5/8"`` or ``"1-1/8"``, or ``None``.
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


def normalize_chuck_size_label(raw_value: str | None) -> str | None:
    """Normalize a rotary-hammer chuck-size label for display.

    Args:
        raw_value: Raw chuck-size string from specs or the title.

    Returns:
        A fractional label such as ``"1"`` or ``"1-1/8"``, or ``None``.
    """
    numeric_value = parse_measurement_value(raw_value)
    if numeric_value is not None:
        return format_fraction_label(numeric_value)
    if raw_value:
        return normalize_text(raw_value)
    return None


def parse_chuck_type(specs: dict[str, str], lowered_text: str) -> str | None:
    """Parse and normalize the hammer chuck type.

    Args:
        specs: Parsed specification label-value map.
        lowered_text: Lower-cased combined product text.

    Returns:
        A normalized chuck-type label, or ``None``.
    """
    raw_value = specs.get("Chuck Type")
    source = normalize_text(raw_value).lower() if raw_value else lowered_text
    if "sds max" in source:
        return "SDS Max"
    if "sds+" in source or "sds plus" in source:
        return "SDS Plus"
    if "spline" in source:
        return "Spline"
    if raw_value:
        return normalize_text(raw_value)
    return None


def parse_handle_style(title: str, lowered_text: str) -> str | None:
    """Parse the hammer handle style from product text.

    Args:
        title: Product title string.
        lowered_text: Lower-cased combined product text.

    Returns:
        A normalized handle-style label, or ``None`` when unavailable.
    """
    lowered_title = title.lower()
    if "d-handle" in lowered_title or "d handle" in lowered_text:
        return "D-Handle"
    if "l-shape" in lowered_title or "l-shape" in lowered_text or "l shape" in lowered_text:
        return "L-Shape"
    if "inline" in lowered_text:
        return "Inline"
    return None


def parse_impact_rate_bpm(specs: dict[str, str]) -> int | None:
    """Parse the highest published blows-per-minute value.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        The maximum BPM value, or ``None`` when unavailable.
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


def parse_impact_energy_j(specs: dict[str, str]) -> float | None:
    """Parse the published impact energy in joules.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        Impact energy in joules, or ``None`` when unavailable.
    """
    return parse_float_value(specs.get("Impact Energy (J) EPTA Value"))


def parse_tool_length_in(specs: dict[str, str]) -> float | None:
    """Parse the preferred tool-length measurement in inches.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        Tool length in inches, with millimeters converted as a fallback.
    """
    length_in = parse_float_value(specs.get("Tool Length [in]")) or parse_float_value(
        specs.get("Product Length [in]")
    )
    if length_in is not None:
        return length_in

    length_mm = parse_float_value(specs.get("Product Length [mm]"))
    if length_mm is not None:
        return round(length_mm / 25.4, 2)
    return None


def parse_weight_lbs(specs: dict[str, str]) -> float | None:
    """Parse the preferred tool weight in pounds.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        Tool weight in pounds, with kilograms converted as a fallback.
    """
    for field_name in (
        "Weight (w/o Battery) [lbs]",
        "Product Weight [lbs]",
        "Weight [lbs]",
    ):
        value = parse_float_value(specs.get(field_name))
        if value is not None:
            return value

    weight_kg = parse_float_value(
        specs.get("Product Weight [Kg]") or specs.get("Weight [Kg]")
    )
    if weight_kg is not None:
        return round(weight_kg * 2.20462, 2)
    return None


def parse_hammer_type(specs: dict[str, str], lowered_text: str) -> str | None:
    """Parse the DEWALT hammer subtype.

    Args:
        specs: Parsed specification label-value map.
        lowered_text: Lower-cased combined product text.

    Returns:
        ``"Combination"`` or ``"Rotary"``, or ``None`` when unclear.
    """
    used_for_chipping = parse_bool_value(specs.get("Used for Chipping?"))
    if "combination hammer" in lowered_text or used_for_chipping is True:
        return "Combination"
    if "rotary hammer" in lowered_text:
        return "Rotary"
    return None


def parse_brushless(specs: dict[str, str], lowered_text: str) -> bool | None:
    """Parse whether the hammer is brushless.

    Args:
        specs: Parsed specification label-value map.
        lowered_text: Lower-cased combined product text.

    Returns:
        ``True``, ``False``, or ``None`` when unavailable.
    """
    value = parse_bool_value(specs.get("Is Brushless?"))
    if value is not None:
        return value
    if "brushless" in lowered_text:
        return True
    return None


def parse_led_light(specs: dict[str, str], lowered_text: str) -> bool | None:
    """Parse whether the hammer advertises an LED light.

    Args:
        specs: Parsed specification label-value map.
        lowered_text: Lower-cased combined product text.

    Returns:
        ``True``, ``False``, or ``None`` when unavailable.
    """
    value = parse_bool_value(specs.get("Has LED Light?"))
    if value is not None:
        return value
    if "led light" in lowered_text:
        return True
    return None


def parse_active_vibration_control(lowered_text: str) -> bool | None:
    """Parse whether the hammer advertises active vibration control.

    Args:
        lowered_text: Lower-cased combined product text.

    Returns:
        ``True`` when the feature is present, otherwise ``None``.
    """
    if "active vibration control" in lowered_text:
        return True
    return None


def parse_shocks_system(specs: dict[str, str], lowered_text: str) -> bool | None:
    """Parse whether the hammer advertises the SHOCKS system.

    Args:
        specs: Parsed specification label-value map.
        lowered_text: Lower-cased combined product text.

    Returns:
        ``True`` when the SHOCKS system is present, otherwise ``None``.
    """
    system = normalize_text(specs.get("System", "")).lower()
    if "shock" in system or "shocks system" in lowered_text:
        return True
    return None


def parse_anti_rotation(lowered_text: str) -> bool | None:
    """Parse whether the hammer advertises anti-rotation control.

    Args:
        lowered_text: Lower-cased combined product text.

    Returns:
        ``True`` when anti-rotation language is present, otherwise ``None``.
    """
    if "anti-rotation" in lowered_text or "e-clutch" in lowered_text:
        return True
    return None


def parse_used_for_chipping(specs: dict[str, str], hammer_type: str | None) -> bool | None:
    """Parse whether the hammer supports chipping mode.

    Args:
        specs: Parsed specification label-value map.
        hammer_type: Parsed hammer subtype label.

    Returns:
        ``True`` or ``False`` when the mode can be inferred, otherwise ``None``.
    """
    value = parse_bool_value(specs.get("Used for Chipping?"))
    if value is not None:
        return value
    if hammer_type == "Combination":
        return True
    if hammer_type == "Rotary":
        return False
    return None


def should_exclude_product(title: str, description: str) -> bool:
    """Determine whether a listed product should be excluded from this family.

    Args:
        title: Product title string.
        description: Product overview string.

    Returns:
        ``True`` when the product is outside the intended rotary-hammer scope.
    """
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    if "construction jack" in lowered or "dust extraction system" in lowered:
        return True
    if "rotary hammer" not in lowered and "combination hammer" not in lowered:
        return True
    return False


def listing_card_is_candidate(card: dict[str, str]) -> bool:
    """Exclude obvious non-tool cards before fetching product pages.

    Args:
        card: Listing-card metadata with ``title`` and ``sku`` values.

    Returns:
        ``True`` when the listing card looks like a valid rotary-hammer tool.
    """
    return not should_exclude_product(card["title"], "")


def is_tool_only_cordless(
    sku: str,
    title: str,
    description: str,
    specs: dict[str, str],
) -> bool:
    """Infer whether a cordless hammer listing is the bare-tool SKU.

    Args:
        sku: Product SKU string.
        title: Product title string.
        description: Product overview string.
        specs: Parsed specification label-value map.

    Returns:
        ``True`` when the cordless listing appears to be bare-tool.
    """
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


def is_supported_rotary_hammer(row: dict[str, Any]) -> bool:
    """Apply the rotary-hammer product-scope rule for the dashboard.

    Args:
        row: Parsed rotary-hammer row.

    Returns:
        ``True`` for all corded hammers and bare-tool cordless hammers.
    """
    if row["power_source"] != "Cordless":
        return True
    return bool(row["tool_only"])


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse a rotary-hammer product page into a structured row.

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
    hammer_type = parse_hammer_type(specs, lowered)
    chuck_size_raw = specs.get("Chuck Size [in]")
    chuck_size_label = normalize_chuck_size_label(chuck_size_raw)
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    tool_only = power_source == "Cordless" and is_tool_only_cordless(
        sku, title, description, specs
    )

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Rotary Hammer",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": specs.get("Battery Type") or specs.get("Battery Chemistry"),
        "battery_capacity_ah": parse_float_value(specs.get("Battery Capacity [Ah]")),
        "amp_rating": parse_float_value(specs.get("Amps [A]")),
        "hammer_type": hammer_type,
        "chuck_size_label": chuck_size_label,
        "chuck_size_in": parse_measurement_value(chuck_size_raw),
        "chuck_type": parse_chuck_type(specs, lowered),
        "handle_style": parse_handle_style(title, lowered),
        "rpm_max": parse_rpm_max(specs.get("No Load Speed [RPM]") or specs.get("RPM")),
        "impact_rate_bpm": parse_impact_rate_bpm(specs),
        "impact_energy_j": parse_impact_energy_j(specs),
        "tool_length_in": parse_tool_length_in(specs),
        "weight_lbs": parse_weight_lbs(specs),
        "brushless": parse_brushless(specs, lowered),
        "led_light": parse_led_light(specs, lowered),
        "anti_rotation": parse_anti_rotation(lowered),
        "active_vibration_control": parse_active_vibration_control(lowered),
        "shocks_system": parse_shocks_system(specs, lowered),
        "used_for_chipping": parse_used_for_chipping(specs, hammer_type),
        "kit": (" kit" in title.lower())
        or title.lower().endswith("kit")
        or parse_bool_value(specs.get("Is it a Set?")) is True,
        "tool_only": tool_only,
        "battery_included": (parse_int_value(specs.get("Battery Quantity")) or 0) > 0,
        "charger_included": any("charger" in item.lower() for item in includes),
        "description": description,
        "features": primary_features,
        "additional_features": additional_features,
        "includes": includes,
        "applications": applications,
        "disclaimers": disclaimers,
    }


def fetch_listing_pages() -> dict[str, str]:
    """Fetch all paginated rotary-hammer catalog listing pages.

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
    """Collect unique product cards from the rotary-hammer listing pages.

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


def fetch_candidate_row(card: dict[str, str]) -> dict[str, Any] | None:
    """Fetch and parse a single candidate rotary-hammer product page.

    Args:
        card: Listing-card metadata containing the product URL.

    Returns:
        A parsed row dictionary when the product remains in scope, otherwise ``None``.
    """
    html_text = fetch_url(card["url"])
    parsed_row = parse_product_page(card["url"], html_text)
    if parsed_row and is_supported_rotary_hammer(parsed_row):
        return parsed_row
    return None


def build_snapshot_from_live_catalog() -> dict[str, Any]:
    """Build a rotary-hammer snapshot by scraping the live DEWALT catalog.

    Args:
        None.

    Returns:
        A JSON-serializable snapshot payload for rotary hammers.
    """
    listing_pages = fetch_listing_pages()
    product_cards = collect_product_cards(listing_pages)
    candidate_cards = [card for card in product_cards if listing_card_is_candidate(card)]

    rows = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {
            executor.submit(fetch_candidate_row, card): card["sku"] for card in candidate_cards
        }
        for future in as_completed(future_map):
            parsed_row = future.result()
            if parsed_row:
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
    """Build a rotary-hammer snapshot from cached product-page HTML files.

    Args:
        source_dir: Directory containing saved DEWALT product-page HTML files.

    Returns:
        A JSON-serializable snapshot payload for rotary hammers.
    """
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_rotary_hammer(parsed_row):
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
    """Persist a rotary-hammer snapshot to disk as formatted JSON.

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
    """Parse command-line arguments for the rotary-hammer scraper.

    Args:
        None.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Scrape DEWALT rotary-hammer product data.")
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
    """Run the rotary-hammer scraper CLI.

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
    print(f"Wrote {snapshot['product_count']} rotary hammers to {args.output}")


if __name__ == "__main__":
    main()
