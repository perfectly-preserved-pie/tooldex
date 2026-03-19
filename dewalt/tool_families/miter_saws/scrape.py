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


CATALOG_URL = "https://www.dewalt.com/products/power-tools/saws/miter-saws"
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "dewalt_miter_saws.json"
MEASUREMENT_PATTERN = re.compile(r"\d+(?:-\d+/\d+|\s+\d+/\d+)|\d+/\d+|\d+(?:\.\d+)?")
INCH_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\s+\d+/\d+)|\d+/\d+|\d+(?:\.\d+)?)\s*(?:in\.|\")",
    re.I,
)
AMP_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*amp", re.I)
RPM_CONTEXT_PATTERN = re.compile(r"(\d[\d,]*)\s*rpm", re.I)
HORIZONTAL_CAPACITY_PATTERN = re.compile(
    r"cut up to\s+(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*in\.\s*horizontally",
    re.I,
)
BASEBOARD_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*in\.\s*base(?:board)?\s*vertically",
    re.I,
)
CROWN_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*in\.\s*crown(?: molding)?\s*nested",
    re.I,
)
CROSSCUT_DIMENSION_PATTERN = re.compile(
    r"\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+\s*in\.\s*x\s*(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*in\.",
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
        A normalized string such as ``"12"`` or ``"7-1/4"``, or ``None``.
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
    """Normalize an inch-based size label for miter-saw measurements.

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
    """Parse the miter-saw battery chemistry label when present.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        The battery type label, or ``None`` when unavailable.
    """
    value = specs.get("Battery Chemistry") or specs.get("Battery Type")
    if value and MAX_VOLTAGE_PATTERN.search(value):
        return None
    return value


def parse_saw_motion(title: str) -> str:
    """Parse whether the miter saw is sliding or fixed.

    Args:
        title: Product title string.

    Returns:
        ``"Sliding"`` when the title says so, otherwise ``"Fixed"``.
    """
    return "Sliding" if "sliding" in title.lower() else "Fixed"


def parse_bevel_type(title: str) -> str | None:
    """Parse the miter-saw bevel style from the title.

    Args:
        title: Product title string.

    Returns:
        ``"Single Bevel"``, ``"Double Bevel"``, or ``None`` when unavailable.
    """
    lowered = title.lower()
    if "double bevel" in lowered or "double-bevel" in lowered:
        return "Double Bevel"
    if "single bevel" in lowered or "single-bevel" in lowered:
        return "Single Bevel"
    return None


def parse_blade_diameter_label(specs: dict[str, str], title: str) -> str | None:
    """Parse and normalize the published blade diameter.

    Args:
        specs: Parsed specification label-value map.
        title: Product title string used as a fallback source.

    Returns:
        A normalized blade-diameter label, or ``None`` when unavailable.
    """
    raw_value = (
        specs.get("Blade Diameter [in]")
        or specs.get("Cutter/Saw Wheel Diameter [in]")
        or specs.get("Disc Diameter [in]")
    )
    if raw_value:
        return normalize_size_label(raw_value)

    match = INCH_PATTERN.search(title)
    if match:
        return normalize_size_label(match.group(1))
    return None


def parse_amp_rating(specs: dict[str, str], title: str) -> float | None:
    """Parse the published amp rating when present.

    Args:
        specs: Parsed specification label-value map.
        title: Product title string used as a fallback source.

    Returns:
        The amp rating, or ``None`` when unavailable.
    """
    value = parse_float_value(specs.get("Amps [A]"))
    if value is not None:
        return value

    match = AMP_PATTERN.search(title)
    if match:
        return float(match.group(1))
    return None


def parse_rpm_max(specs: dict[str, str], all_text: str) -> int | None:
    """Parse the highest published blade speed.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        The maximum RPM value, or ``None`` when unavailable.
    """
    value = parse_int_value(
        specs.get("No Load Speed [RPM]")
        or specs.get("Blade Speed [rpm]")
        or specs.get("Speed [rpm]")
        or specs.get("Rotation Speed [rpm]")
    )
    if value is not None:
        return value

    matches = [int(token.replace(",", "")) for token in RPM_CONTEXT_PATTERN.findall(all_text)]
    return max(matches) if matches else None


def parse_cross_cut_capacity(specs: dict[str, str], all_text: str) -> float | None:
    """Parse the primary horizontal cross-cut capacity in inches.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        The cross-cut capacity in inches, or ``None`` when unavailable.
    """
    value = parse_measurement_value(specs.get("Cutting Capacity [in]"))
    if value is not None:
        return value

    for field_name in (
        "Max. Cutting Capacity (90°/90°) [in]",
        "Max. Cutting Capacity (90 degrees /90 degrees ) [in]",
    ):
        raw_value = specs.get(field_name)
        if not raw_value:
            continue
        dimension_matches = INCH_PATTERN.findall(raw_value)
        if dimension_matches:
            return parse_measurement_value(dimension_matches[-1])

    match = HORIZONTAL_CAPACITY_PATTERN.search(all_text)
    if match:
        return parse_measurement_value(match.group(1))

    if "cross cut capacity" in all_text.lower():
        second_dimension = re.search(
            r"\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+\s*in\.\s*x\s*(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*in\.",
            all_text,
            re.I,
        )
        if second_dimension:
            return parse_measurement_value(second_dimension.group(1))
    return None


def parse_capacity_from_text(pattern: re.Pattern[str], all_text: str) -> float | None:
    """Parse a capacity value from narrative feature text.

    Args:
        pattern: Regular-expression pattern for the target capacity.
        all_text: Combined product text used for matching.

    Returns:
        The parsed capacity value, or ``None`` when unavailable.
    """
    match = pattern.search(all_text)
    if not match:
        return None
    return parse_measurement_value(match.group(1))


def parse_baseboard_capacity(all_text: str) -> float | None:
    """Parse the supported baseboard capacity in inches.

    Args:
        all_text: Combined product text used for matching.

    Returns:
        The baseboard capacity in inches, or ``None`` when unavailable.
    """
    return parse_capacity_from_text(BASEBOARD_PATTERN, all_text)


def parse_crown_capacity(all_text: str) -> float | None:
    """Parse the supported nested crown capacity in inches.

    Args:
        all_text: Combined product text used for matching.

    Returns:
        The crown capacity in inches, or ``None`` when unavailable.
    """
    return parse_capacity_from_text(CROWN_PATTERN, all_text)


def parse_weight_lbs(specs: dict[str, str], all_text: str) -> float | None:
    """Parse the preferred tool weight in pounds.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        Tool weight in pounds, or ``None`` when unavailable.
    """
    for field_name in ("Weight (Including Battery) [lbs]", "Product Weight [lbs]", "Weight [lbs]"):
        value = parse_float_value(specs.get(field_name))
        if value is not None:
            return value

    match = re.search(r"only\s+(\d+(?:\.\d+)?)\s*lb", all_text, re.I)
    if match:
        return float(match.group(1))
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
        ``True`` when the product is outside the intended miter-saw scope.
    """
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    return "miter saw" not in lowered


def is_tool_only_cordless(
    sku: str,
    title: str,
    description: str,
    specs: dict[str, str],
) -> bool:
    """Infer whether a cordless miter-saw listing is the bare-tool SKU.

    Args:
        sku: Product SKU string.
        title: Product title string.
        description: Product overview string.
        specs: Parsed specification label-value map.

    Returns:
        ``True`` when the cordless listing appears to be bare-tool.
    """
    lowered = f"{title} {description}".lower()
    if " kit" in lowered or lowered.endswith("kit"):
        return False
    is_set = parse_bool_value(specs.get("Is it a Set?"))
    battery_quantity = parse_int_value(
        specs.get("Battery Quantity") or specs.get("Number of Batteries Included")
    )
    return any(
        (
            "tool only" in lowered,
            "battery sold separately" in lowered,
            "charger sold separately" in lowered,
            "battery and charger sold separately" in lowered,
            is_set is False,
            battery_quantity == 0,
            sku_looks_like_bare_tool(sku),
        )
    )


def is_supported_miter_saw(row: dict[str, Any]) -> bool:
    """Apply the miter-saw product-scope rule for the dashboard.

    Args:
        row: Parsed miter-saw row.

    Returns:
        ``True`` for all corded miter saws and bare-tool cordless miter saws.
    """
    if row["power_source"] != "Cordless":
        return True
    return bool(row["tool_only"])


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse a miter-saw product page into a structured row.

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
    blade_diameter_label = parse_blade_diameter_label(specs, title)
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
        "category": "Miter Saw",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": parse_battery_type(specs),
        "battery_capacity_ah": parse_float_value(specs.get("Battery Capacity [Ah]")),
        "saw_motion": parse_saw_motion(title),
        "bevel_type": parse_bevel_type(title),
        "blade_diameter_label": blade_diameter_label,
        "blade_diameter_in": parse_measurement_value(blade_diameter_label),
        "amp_rating": parse_amp_rating(specs, title),
        "rpm_max": parse_rpm_max(specs, all_text),
        "cross_cut_capacity_in": parse_cross_cut_capacity(specs, all_text),
        "baseboard_capacity_in": parse_baseboard_capacity(all_text),
        "crown_capacity_in": parse_crown_capacity(all_text),
        "tool_length_in": parse_tool_length_in(specs),
        "weight_lbs": parse_weight_lbs(specs, all_text),
        "brushless": parse_bool_feature(specs, "Is Brushless?", lowered, ("brushless",)),
        "dust_extraction": parse_bool_feature(
            specs,
            "Has Dust Extraction?",
            lowered,
            ("dust collection", "dust capture", "dust port", "dust extractor"),
        ),
        "led_light": parse_bool_feature(
            specs,
            "Has LED Light?",
            lowered,
            ("led light",),
        ),
        "cutline_system": any(
            needle in lowered for needle in ("cutline", "cut line", "xps")
        ),
        "wireless_tool_control": "wireless tool control" in lowered,
        "regenerative_braking": any(
            needle in lowered for needle in ("regenerative braking", "cut.capture.charge")
        ),
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
    """Fetch all paginated miter-saw catalog listing pages.

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
    """Collect unique product cards from the miter-saw listing pages.

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
    """Build a miter-saw snapshot by scraping the live DEWALT catalog.

    Args:
        None.

    Returns:
        A JSON-serializable snapshot payload for miter saws.
    """
    listing_pages = fetch_listing_pages()
    product_cards = collect_product_cards(listing_pages)

    rows = []
    for card in product_cards:
        html_text = fetch_url(card["url"])
        parsed_row = parse_product_page(card["url"], html_text)
        if parsed_row and is_supported_miter_saw(parsed_row):
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
    """Build a miter-saw snapshot from cached product-page HTML files.

    Args:
        source_dir: Directory containing saved DEWALT product-page HTML files.

    Returns:
        A JSON-serializable snapshot payload for miter saws.
    """
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_miter_saw(parsed_row):
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
    """Persist a miter-saw snapshot to disk as formatted JSON.

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
    """Parse command-line arguments for the miter-saw scraper.

    Args:
        None.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Scrape DEWALT miter-saw product data.")
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
    """Run the miter-saw scraper CLI.

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
    print(f"Wrote {snapshot['product_count']} miter saws to {args.output}")


if __name__ == "__main__":
    main()
