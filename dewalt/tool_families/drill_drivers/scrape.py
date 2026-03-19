from __future__ import annotations

import argparse
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter


CATALOG_URL = "https://www.dewalt.com/products/power-tools/drills/drill-drivers"
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "dewalt_drill_drivers.json"
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

PAGE_PATTERN = re.compile(r'href="\?page=(\d+)"')
PRODUCT_URL_PATTERN = re.compile(r"https://www\.dewalt\.com/product/[^\"?]+")
MAX_VOLTAGE_PATTERN = re.compile(r"(\d{2,3})\s*v\s*max", re.I)
NOMINAL_VOLTAGE_PATTERN = re.compile(r"nominal voltage is\s*(\d+(?:\.\d+)?)", re.I)
RPM_PATTERN = re.compile(r"(\d[\d,]*)")
FLOAT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")


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


def normalize_text(raw_text: str) -> str:
    """Normalize scraped HTML text into a compact ASCII-friendly string.

    Args:
        raw_text: Unprocessed text extracted from a page.

    Returns:
        Normalized text with collapsed whitespace and cleaned punctuation.
    """
    text = raw_text
    replacements = {
        "\xa0": " ",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2122": "",
        "\u00ae": "",
        "\u2212": "-",
        "\u00b0": " degrees ",
        "\u00b2": "^2",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def unique_preserving_order(values: list[str]) -> list[str]:
    """Remove duplicate strings while preserving first-seen order.

    Args:
        values: Ordered list of candidate strings.

    Returns:
        A deduplicated list that keeps the original order.
    """
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def get_soup_text(node: Any) -> str:
    """Extract normalized text from a BeautifulSoup node.

    Args:
        node: Optional BeautifulSoup node.

    Returns:
        The normalized text content, or an empty string when the node is missing.
    """
    if not node:
        return ""
    return normalize_text(node.get_text("\n", strip=True))


def extract_text_items(soup: BeautifulSoup, selector: str) -> list[str]:
    """Extract deduplicated text items from a CSS selector.

    Args:
        soup: Parsed page DOM.
        selector: CSS selector that targets repeated text items.

    Returns:
        A deduplicated list of normalized text strings.
    """
    items = [get_soup_text(node) for node in soup.select(selector)]
    return unique_preserving_order(items)


def extract_section_items(soup: BeautifulSoup, section_id: str) -> list[str]:
    """Extract list items from a named accordion section.

    Args:
        soup: Parsed page DOM.
        section_id: DOM ``id`` of the accordion content section.

    Returns:
        A deduplicated list of normalized bullet values from that section.
    """
    section = soup.find(id=section_id)
    if not section:
        return []

    raw_items: list[str] = []
    for raw_item in section.select("li.coh-list-item"):
        raw_text = raw_item.get_text("\n", strip=True)
        split_items = [
            normalize_text(part) for part in re.split(r"[\r\n]+", raw_text) if part.strip()
        ]
        raw_items.extend(split_items or [normalize_text(raw_text)])
    return unique_preserving_order(raw_items)


def parse_canonical_url(soup: BeautifulSoup) -> str:
    """Resolve the canonical URL from a product page.

    Args:
        soup: Parsed page DOM.

    Returns:
        The canonical URL string, or an empty string when unavailable.
    """
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        return canonical["href"]
    return ""


def format_iso_now() -> str:
    """Build the current UTC timestamp in ISO 8601 format.

    Args:
        None.

    Returns:
        The current UTC timestamp without microseconds.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_fractional_number(token: str) -> float:
    """Parse a decimal or fractional measurement token into a float.

    Args:
        token: Raw numeric token such as ``"1/2"`` or ``"0.5"``.

    Returns:
        The parsed numeric value as a float.
    """
    cleaned = token.strip().replace('"', "")
    if re.fullmatch(r"\d+/\d+", cleaned):
        numerator, denominator = cleaned.split("/")
        return int(numerator) / int(denominator)
    return float(cleaned)


def parse_float_value(raw_value: str | None) -> float | None:
    """Parse the first numeric token from a specification value.

    Args:
        raw_value: Raw specification string.

    Returns:
        The parsed float value, or ``None`` when no numeric token exists.
    """
    if not raw_value:
        return None
    for token in re.findall(r"\d+/\d+|\d+(?:\.\d+)?", raw_value):
        try:
            return parse_fractional_number(token)
        except ValueError:
            continue
    return None


def normalize_chuck_size_label(raw_value: str | None) -> str | None:
    """Normalize equivalent chuck-size labels to a single display value.

    Args:
        raw_value: Raw chuck-size specification string.

    Returns:
        A normalized fractional label such as ``"1/2"``, or ``None`` when unavailable.
    """
    if not raw_value:
        return None

    numeric_value = parse_float_value(raw_value)
    if numeric_value is None:
        return normalize_text(raw_value)

    fraction = Fraction(numeric_value).limit_denominator(16)
    if fraction.denominator == 1:
        return str(fraction.numerator)
    return f"{fraction.numerator}/{fraction.denominator}"


def parse_int_value(raw_value: str | None) -> int | None:
    """Parse the first integer-looking token from a specification value.

    Args:
        raw_value: Raw specification string.

    Returns:
        The parsed integer value, or ``None`` when no token exists.
    """
    float_value = parse_float_value(raw_value)
    if float_value is None:
        return None
    return int(float_value)


def parse_bool_value(raw_value: str | None) -> bool | None:
    """Parse a yes/no specification string into a boolean.

    Args:
        raw_value: Raw specification string.

    Returns:
        ``True`` or ``False`` when recognized, otherwise ``None``.
    """
    if raw_value is None:
        return None
    lowered = raw_value.strip().lower()
    if lowered == "yes":
        return True
    if lowered == "no":
        return False
    return None


def parse_specifications_table(soup: BeautifulSoup) -> dict[str, str]:
    """Parse the product specifications table into a label-value map.

    Args:
        soup: Parsed page DOM.

    Returns:
        A dictionary keyed by specification label.
    """
    specs: dict[str, str] = {}
    for row in soup.select("div.coh-container.coh-style-specifications table tr"):
        cells = row.select("td")
        if len(cells) < 2:
            continue
        label = get_soup_text(cells[0])
        value = get_soup_text(cells[1])
        if label and value:
            specs[label] = value
    return specs


def parse_series(title: str) -> list[str]:
    """Parse the marketing series tags embedded in a product title.

    Args:
        title: Product title string.

    Returns:
        An ordered list of matching series labels.
    """
    lowered = title.lower()
    series = []
    for needle, label in (
        ("atomic", "ATOMIC"),
        ("xr", "XR"),
        ("xtreme", "XTREME"),
        ("tool connect", "TOOL CONNECT"),
        ("flexvolt", "FLEXVOLT"),
        ("powerstack", "POWERSTACK"),
        ("powerpack", "POWERPACK"),
    ):
        if needle in lowered:
            series.append(label)
    return unique_preserving_order(series)


def parse_voltage_system(
    specs: dict[str, str],
    power_source: str,
    all_text: str,
) -> tuple[str | None, int | None]:
    """Parse the display voltage system and numeric max voltage.

    Args:
        specs: Parsed specification label-value map.
        power_source: Resolved power source for the product.
        all_text: Combined product text used as a fallback source.

    Returns:
        A tuple of formatted voltage-system label and max-voltage integer.
    """
    raw_value = specs.get("Battery Voltage [V]") or specs.get("Voltage [V]")
    max_voltage_v = parse_int_value(raw_value)
    if max_voltage_v is None:
        match = MAX_VOLTAGE_PATTERN.search(all_text)
        if match:
            max_voltage_v = int(match.group(1))

    if max_voltage_v is None:
        return None, None
    if power_source == "Cordless":
        return f"{max_voltage_v}V MAX", max_voltage_v
    return f"{max_voltage_v}V", max_voltage_v


def parse_nominal_voltage_v(
    disclaimers: list[str],
    max_voltage_v: int | None,
) -> float | None:
    """Parse the nominal battery voltage from product disclaimers.

    Args:
        disclaimers: List of disclaimer strings from the product page.
        max_voltage_v: Parsed maximum battery voltage.

    Returns:
        The nominal voltage value when available, otherwise ``None``.
    """
    disclaimer_text = " ".join(disclaimers)
    match = NOMINAL_VOLTAGE_PATTERN.search(disclaimer_text)
    if match:
        return float(match.group(1))
    if max_voltage_v == 20:
        return 18.0
    if max_voltage_v == 12:
        return 10.8
    return None


def parse_rpm_max(raw_value: str | None) -> int | None:
    """Parse the highest no-load-speed value from a specification string.

    Args:
        raw_value: Raw no-load-speed string.

    Returns:
        The maximum RPM value, or ``None`` when unavailable.
    """
    if not raw_value:
        return None
    values = [int(token.replace(",", "")) for token in RPM_PATTERN.findall(raw_value)]
    return max(values) if values else None


def parse_tool_length_in(specs: dict[str, str]) -> float | None:
    """Parse the preferred tool-length measurement from specifications.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        Tool length in inches, with product length as a fallback.
    """
    return parse_float_value(specs.get("Tool Length [in]")) or parse_float_value(
        specs.get("Product Length [in]")
    )


def parse_power_source(specs: dict[str, str], all_text: str) -> str:
    """Parse the power-source classification for a drill driver.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used as a fallback source.

    Returns:
        ``"Cordless"`` or ``"Corded"``.
    """
    power_source = specs.get("Power Source")
    if power_source:
        normalized = normalize_text(power_source)
        if normalized.lower().startswith("cordless"):
            return "Cordless"
        if normalized.lower().startswith("corded"):
            return "Corded"

    if specs.get("Battery Voltage [V]") or specs.get("Battery Type") or specs.get(
        "Battery Chemistry"
    ):
        return "Cordless"

    lowered = all_text.lower()
    if MAX_VOLTAGE_PATTERN.search(all_text):
        return "Cordless"
    if (
        "cordless" in lowered
        or "tool only" in lowered
        or "battery & charger sold separately" in lowered
        or "battery and charger sold separately" in lowered
        or "battery sold separately" in lowered
    ):
        return "Cordless"
    return "Corded"


def sku_looks_like_bare_tool(sku: str) -> bool:
    """Check whether a SKU follows DEWALT's bare-tool pattern.

    Args:
        sku: Product SKU string.

    Returns:
        ``True`` when the SKU ends in a bare-tool ``B`` suffix and does not contain
        a kit-style ``P`` marker, otherwise ``False``.
    """
    normalized_sku = re.sub(r"[^A-Z0-9]", "", sku.upper())
    if "P" in normalized_sku:
        return False
    return re.fullmatch(r"[A-Z]+[0-9]+[A-Z]*B", normalized_sku) is not None


def is_supported_drill_driver(row: dict[str, Any]) -> bool:
    """Apply the drill-driver product-scope rule for the dashboard.

    Args:
        row: Parsed drill-driver row.

    Returns:
        ``True`` for all corded drills and bare-tool cordless drill drivers.
    """
    if row["power_source"] != "Cordless":
        return True
    return bool(row["tool_only"])


def should_exclude_product(title: str, description: str) -> bool:
    """Determine whether a listed product should be excluded from this family.

    Args:
        title: Product title string.
        description: Product overview string.

    Returns:
        ``True`` when the product is outside the intended drill-driver scope.
    """
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    if "drill" not in lowered:
        return True
    for needle in ("hammer drill", "hammerdrill", "screw gun", "screwgun", "combo kit"):
        if needle in lowered:
            return True
    return False


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse a drill-driver product page into a structured row.

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
    no_load_speed = specs.get("No Load Speed [RPM]") or specs.get("Speed [rpm]")
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    tool_only = power_source == "Cordless" and (
        "tool only" in title.lower() or sku_looks_like_bare_tool(sku)
    )

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Drill Driver",
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
    """Fetch all paginated drill-driver catalog listing pages.

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
    """Collect unique product URLs from the drill-driver listing pages.

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
    """Build a drill-driver snapshot by scraping the live DEWALT catalog.

    Args:
        None.

    Returns:
        A JSON-serializable snapshot payload for drill drivers.
    """
    listing_pages = fetch_listing_pages()
    product_urls = collect_product_urls(listing_pages)

    rows = []
    for product_url in product_urls:
        html_text = fetch_url(product_url)
        parsed_row = parse_product_page(product_url, html_text)
        if parsed_row and is_supported_drill_driver(parsed_row):
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
    """Build a drill-driver snapshot from cached product-page HTML files.

    Args:
        source_dir: Directory containing saved DEWALT product-page HTML files.

    Returns:
        A JSON-serializable snapshot payload for drill drivers.
    """
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_drill_driver(parsed_row):
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
    """Persist a drill-driver snapshot to disk as formatted JSON.

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
    """Parse command-line arguments for the drill-driver scraper.

    Args:
        None.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Scrape DEWALT drill-driver product data.")
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
    """Run the drill-driver scraper CLI.

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
    print(f"Wrote {snapshot['product_count']} drill drivers to {args.output}")


if __name__ == "__main__":
    main()
