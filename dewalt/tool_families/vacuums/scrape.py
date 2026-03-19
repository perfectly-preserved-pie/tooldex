from __future__ import annotations

import argparse
from bs4 import BeautifulSoup
from fractions import Fraction
import json
from pathlib import Path
import re
import time
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
    parse_int_value,
    parse_nominal_voltage_v,
    parse_series,
    parse_specifications_table,
    sku_looks_like_bare_tool,
    unique_preserving_order,
)


CATALOG_URL = "https://www.dewalt.com/products/power-tools/dust-management/vacuums"
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "dewalt_vacuums.json"
SESSION = requests.Session()
MEASUREMENT_PATTERN = re.compile(r"\d+(?:-\d+/\d+|\s+\d+/\d+)|\d+/\d+|\d+(?:\.\d+)?")
GALLON_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\s+\d+/\d+)?|\d+/\d+|\d+(?:\.\d+)?)\s*(?:gallon|gallons|gal\b)",
    re.I,
)
PEAK_HP_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:php|peak\s*horsepower|hp)", re.I)
CFM_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*cfm", re.I)
AIR_WATTS_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*air\s*watts?", re.I)
DUAL_VOLTAGE_PATTERN = re.compile(r"(\d{2,3})\s*/\s*(\d{2,3})\s*v\s*max", re.I)
HOSE_LENGTH_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:ft\.?|foot|feet|')\s*(?:x\s*\d+(?:-\d+/\d+|\s+\d+/\d+)?|"
    r"x\s*\d+/\d+|x\s*\d+(?:\.\d+)?)?\s*(?:in\.?|inch|inches|\")?\s*(?:diameter\s*)?"
    r"(?:long\s*)?(?:anti[- ]static\s*)?(?:flexible\s*)?(?:heavy[- ]duty\s*)?"
    r"(?:crush[- ]resistant\s*)?(?:durable\s*)?hose",
    re.I,
)
ALT_HOSE_LENGTH_PATTERN = re.compile(
    r"hose[^.]{0,80}?up to\s*(\d+(?:\.\d+)?)\s*(?:ft\.?|foot|feet)",
    re.I,
)
HOSE_DIAMETER_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\s+\d+/\d+)?|\d+/\d+|\d+(?:\.\d+)?)\s*"
    r"(?:in\.?|inch|inches|\")\s*(?:x\s*\d+(?:\.\d+)?\s*(?:ft\.?|foot|feet|'))?\s*"
    r"(?:diameter\s*)?(?:durable\s*)?(?:flexible\s*)?hose",
    re.I,
)
CORD_LENGTH_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:ft\.?|foot|feet)\s*power cord",
    re.I,
)


def is_error_page(html_text: str) -> bool:
    """Check whether a DEWALT response body is the branded error page.

    Args:
        html_text: Raw HTML response body.

    Returns:
        ``True`` when the body matches DEWALT's error-page template.
    """
    lowered = html_text.lower()
    return "error/styles/styles.css" in lowered or "404 page | dewalt" in lowered


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
            response = SESSION.get(url, timeout=request_timeout)
            response.raise_for_status()
            if is_error_page(response.text):
                SESSION.get(CATALOG_URL, timeout=request_timeout)
                time.sleep(0.25)
                last_error = RuntimeError(f"DEWALT returned an error page for {url}")
                continue
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
    """Format a numeric measurement as an integer or mixed fraction label.

    Args:
        value: Numeric measurement value.

    Returns:
        A display label such as ``"1/2"`` or ``"1-1/4"``, or ``None`` when missing.
    """
    if value is None:
        return None

    fraction = Fraction(value).limit_denominator(16)
    whole = fraction.numerator // fraction.denominator
    remainder = fraction.numerator % fraction.denominator
    if remainder == 0:
        return str(whole)
    if whole == 0:
        return f"{remainder}/{fraction.denominator}"
    return f"{whole}-{remainder}/{fraction.denominator}"


def parse_vacuum_series(title: str) -> list[str]:
    """Parse the marketing series tags embedded in a vacuum title.

    Args:
        title: Product title string.

    Returns:
        An ordered list of matching series labels.
    """
    series = list(parse_series(title))
    if "stealthsonic" in title.lower():
        series.append("STEALTHSONIC")
    return unique_preserving_order(series)


def parse_vacuum_type(title: str, description: str) -> str:
    """Parse the vacuum subtype from the title and description.

    Args:
        title: Product title string.
        description: Product overview string.

    Returns:
        A normalized vacuum subtype label.
    """
    lowered = f"{title} {description}".lower()
    if "dust extractor" in lowered:
        return "Dust Extractor"
    if "hand vacuum" in lowered:
        return "Hand Vacuum"
    if "wall-mounted" in lowered or "wall mounted" in lowered:
        return "Wall-Mounted Vacuum"
    if "wet/dry" in lowered or "wet-dry" in lowered or "wet dry" in lowered:
        return "Wet/Dry Vacuum"
    return "Vacuum"


def parse_power_source(specs: dict[str, str], all_text: str) -> str:
    """Parse the vacuum power-source classification.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        ``"Corded"``, ``"Cordless"``, or ``"Corded/Cordless"``.
    """
    raw_value = specs.get("Power Source")
    if raw_value:
        lowered_value = normalize_text(raw_value).lower()
        if "cordless/corded" in lowered_value or "corded/cordless" in lowered_value:
            return "Corded/Cordless"
        if lowered_value.startswith("cordless"):
            return "Cordless"
        if lowered_value.startswith("corded"):
            return "Corded"

    lowered = all_text.lower()
    if any(
        needle in lowered
        for needle in (
            "cordless/corded",
            "corded/cordless",
            "battery powered or outlet powered",
            "go battery powered or outlet powered",
        )
    ):
        return "Corded/Cordless"
    if (
        MAX_VOLTAGE_PATTERN.search(all_text)
        or "tool only" in lowered
        or "battery & charger sold separately" in lowered
        or "battery and charger sold separately" in lowered
        or "battery sold separately" in lowered
    ):
        return "Cordless"
    return "Corded"


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
    dual_match = DUAL_VOLTAGE_PATTERN.search(all_text)
    if dual_match:
        voltages = sorted({int(dual_match.group(1)), int(dual_match.group(2))})
        return f"{voltages[0]}/{voltages[1]}V MAX", max(voltages)

    voltage_matches = sorted({int(token) for token in MAX_VOLTAGE_PATTERN.findall(all_text)})
    if voltage_matches:
        if len(voltage_matches) > 1:
            return (
                f"{'/'.join(str(token) for token in voltage_matches)}V MAX",
                max(voltage_matches),
            )
        return (
            f"{voltage_matches[0]}V MAX"
            if power_source != "Corded"
            else f"{voltage_matches[0]}V",
            voltage_matches[0],
        )

    raw_voltage = parse_int_value(specs.get("Voltage [V]"))
    if raw_voltage is None:
        return None, None
    if power_source == "Corded":
        return f"{raw_voltage}V", raw_voltage
    return f"{raw_voltage}V MAX", raw_voltage


def build_tank_capacity(
    specs: dict[str, str],
    all_text: str,
) -> tuple[float | None, str | None]:
    """Parse the tank capacity in gallons plus a friendly display label.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used as a fallback source.

    Returns:
        A tuple containing gallon capacity and a display label.
    """
    raw_gallon_value = specs.get("Tank Capacity [gal]")
    if raw_gallon_value:
        gallons = parse_measurement_value(raw_gallon_value)
        label = format_fraction_label(gallons)
        return gallons, f"{label} gal" if label else None

    raw_liter_value = specs.get("Tank Capacity [l]")
    if raw_liter_value:
        liters = parse_measurement_value(raw_liter_value)
        gallons = round(liters / 3.78541, 2) if liters is not None else None
        return gallons, f"{normalize_text(raw_liter_value)} L"

    match = GALLON_PATTERN.search(all_text)
    if not match:
        return None, None

    gallons = parse_measurement_value(match.group(1))
    label = format_fraction_label(gallons)
    return gallons, f"{label} gal" if label else None


def parse_peak_hp(all_text: str) -> float | None:
    """Parse the advertised peak horsepower from product text.

    Args:
        all_text: Combined product text used for pattern matching.

    Returns:
        The parsed peak horsepower value, or ``None`` when unavailable.
    """
    match = PEAK_HP_PATTERN.search(all_text)
    if not match:
        return None
    return float(match.group(1))


def parse_airflow_cfm(all_text: str) -> int | None:
    """Parse the vacuum airflow value in CFM.

    Args:
        all_text: Combined product text used for pattern matching.

    Returns:
        The parsed airflow value, or ``None`` when unavailable.
    """
    match = CFM_PATTERN.search(all_text)
    if not match:
        return None
    return int(float(match.group(1)))


def parse_air_watts(all_text: str) -> int | None:
    """Parse the advertised air-watts value from product text.

    Args:
        all_text: Combined product text used for pattern matching.

    Returns:
        The parsed air-watts value, or ``None`` when unavailable.
    """
    match = AIR_WATTS_PATTERN.search(all_text)
    if not match:
        return None
    return int(float(match.group(1)))


def build_hose_diameter(specs: dict[str, str], all_text: str) -> tuple[float | None, str | None]:
    """Parse the hose diameter in inches plus a friendly display label.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used as a fallback source.

    Returns:
        A tuple containing hose diameter in inches and a display label.
    """
    raw_value = specs.get("Hose Diameter [in]")
    if raw_value:
        hose_diameter_in = parse_measurement_value(raw_value)
        label = format_fraction_label(hose_diameter_in)
        return hose_diameter_in, f"{label} in." if label else None

    match = HOSE_DIAMETER_PATTERN.search(all_text)
    if not match:
        return None, None

    hose_diameter_in = parse_measurement_value(match.group(1))
    label = format_fraction_label(hose_diameter_in)
    return hose_diameter_in, f"{label} in." if label else None


def parse_hose_length_ft(all_text: str) -> float | None:
    """Parse the hose length in feet from product text.

    Args:
        all_text: Combined product text used for pattern matching.

    Returns:
        The parsed hose length, or ``None`` when unavailable.
    """
    for pattern in (HOSE_LENGTH_PATTERN, ALT_HOSE_LENGTH_PATTERN):
        match = pattern.search(all_text)
        if match:
            return float(match.group(1))
    return None


def parse_cord_length_ft(specs: dict[str, str], all_text: str) -> float | None:
    """Parse the power-cord length in feet.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used as a fallback source.

    Returns:
        The parsed cord length, or ``None`` when unavailable.
    """
    raw_value = specs.get("Cord Length [ft]")
    if raw_value:
        return parse_measurement_value(raw_value)

    match = CORD_LENGTH_PATTERN.search(all_text)
    if not match:
        return None
    return float(match.group(1))


def parse_weight_lbs(specs: dict[str, str]) -> float | None:
    """Parse the preferred vacuum weight in pounds.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        The product weight in pounds, or ``None`` when unavailable.
    """
    weight_lbs = parse_measurement_value(specs.get("Product Weight [lbs]"))
    if weight_lbs is not None:
        return weight_lbs

    weight_oz = parse_measurement_value(specs.get("Product Weight [oz]"))
    if weight_oz is not None:
        return round(weight_oz / 16, 2)
    return None


def parse_wet_dry(lowered_text: str) -> bool | None:
    """Parse whether the vacuum supports wet/dry cleanup.

    Args:
        lowered_text: Lower-cased combined product text.

    Returns:
        ``True`` or ``False`` when the product text makes the answer clear.
    """
    if any(
        needle in lowered_text
        for needle in ("wet/dry", "wet-dry", "wet dry", "wet or dry", "wet and dry")
    ):
        return True
    if "dry hand vacuum" in lowered_text:
        return False
    return None


def should_exclude_product(title: str, description: str) -> bool:
    """Determine whether a listed product should be excluded from this family.

    Args:
        title: Product title string.
        description: Product overview string.

    Returns:
        ``True`` when the product is outside the intended vacuum scope.
    """
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    return not any(keyword in lowered for keyword in ("vacuum", "portable vac", "dust extractor"))


def listing_card_is_candidate(card: dict[str, str]) -> bool:
    """Exclude obvious non-vacuum cards before fetching product pages.

    Args:
        card: Listing-card dictionary with title and URL metadata.

    Returns:
        ``True`` when the listing card looks like a vacuum or dust extractor.
    """
    return not should_exclude_product(card["title"], "")


def is_tool_only_product(
    sku: str,
    title: str,
    all_text: str,
) -> bool:
    """Infer whether a cordless or hybrid vacuum listing is bare-tool or tool-only.

    Args:
        sku: Product SKU string.
        title: Product title string.
        all_text: Combined product text used for fallback matching.

    Returns:
        ``True`` when the product looks like a tool-only cordless SKU.
    """
    lowered = all_text.lower()
    return any(
        (
            "tool only" in title.lower(),
            "battery & charger sold separately" in lowered,
            "battery and charger sold separately" in lowered,
            "battery sold separately" in lowered,
            "charger sold separately" in lowered,
            sku_looks_like_bare_tool(sku),
        )
    )


def is_supported_vacuum(row: dict[str, Any]) -> bool:
    """Apply the vacuum product-scope rule for the dashboard.

    Args:
        row: Parsed vacuum row.

    Returns:
        ``True`` for all corded vacuums and tool-only cordless or hybrid vacuums.
    """
    if row["power_source"] in {"Cordless", "Corded/Cordless"}:
        return bool(row["tool_only"]) and not bool(row["kit"])
    return row["power_source"] == "Corded"


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse a vacuum product page into a structured row.

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
    tank_capacity_gal, tank_capacity_display = build_tank_capacity(specs, all_text)
    hose_diameter_in, hose_diameter_display = build_hose_diameter(specs, all_text)
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    battery_included = any(
        "battery" in item.lower() and "sold separately" not in item.lower()
        for item in includes
    )
    charger_included = any(
        "charger" in item.lower() and "sold separately" not in item.lower()
        for item in includes
    )
    tool_only = power_source in {"Cordless", "Corded/Cordless"} and is_tool_only_product(
        sku,
        title,
        all_text,
    )
    kit = (
        " kit" in title.lower()
        or title.lower().endswith("kit")
        or battery_included
        or charger_included
    )

    wireless_tool_control = parse_bool_value(specs.get("Has Wireless Tool Control - WTC?"))
    if wireless_tool_control is None:
        wireless_tool_control = any(
            needle in lowered
            for needle in (
                "wireless tool control",
                "wireless on/off control",
                "wireless on/off capability",
            )
        )

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Vacuum",
        "series": parse_vacuum_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": specs.get("Battery Type"),
        "battery_capacity_ah": parse_measurement_value(specs.get("Battery Capacity [Ah]")),
        "vacuum_type": parse_vacuum_type(title, description),
        "tank_capacity_gal": tank_capacity_gal,
        "tank_capacity_display": tank_capacity_display,
        "peak_hp": parse_peak_hp(all_text),
        "airflow_cfm": parse_airflow_cfm(all_text),
        "air_watts": parse_air_watts(all_text),
        "max_watts_out": parse_int_value(specs.get("Max. Watts Out [W]")),
        "hose_diameter_in": hose_diameter_in,
        "hose_diameter_display": hose_diameter_display,
        "hose_length_ft": parse_hose_length_ft(all_text),
        "cord_length_ft": parse_cord_length_ft(specs, all_text),
        "weight_lbs": parse_weight_lbs(specs),
        "hepa_filter": "hepa" in lowered,
        "wet_dry": parse_wet_dry(lowered),
        "quiet_operation": any(
            needle in lowered for needle in ("quiet", "stealthsonic", "low noise", "muffler")
        ),
        "wireless_tool_control": wireless_tool_control,
        "blower_port": "blower port" in lowered or "blow sawdust" in lowered,
        "automatic_filter_cleaning": "automatic filter cleaning" in lowered,
        "kit": kit,
        "tool_only": tool_only,
        "battery_included": battery_included,
        "charger_included": charger_included,
        "description": description,
        "features": primary_features,
        "additional_features": additional_features,
        "includes": includes,
        "applications": applications,
        "disclaimers": disclaimers,
    }


def fetch_listing_pages() -> dict[str, str]:
    """Fetch all paginated vacuum catalog listing pages.

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
    """Collect unique product cards from the vacuum listing pages.

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
    """Build a vacuum snapshot by scraping the live DEWALT catalog.

    Args:
        None.

    Returns:
        A JSON-serializable snapshot payload for vacuums.
    """
    listing_pages = fetch_listing_pages()
    product_cards = collect_product_cards(listing_pages)
    candidate_cards = [card for card in product_cards if listing_card_is_candidate(card)]

    rows = []
    for card in candidate_cards:
        html_text = fetch_url(card["url"])
        parsed_row = parse_product_page(card["url"], html_text)
        if parsed_row and is_supported_vacuum(parsed_row):
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
    """Build a vacuum snapshot from cached product-page HTML files.

    Args:
        source_dir: Directory containing saved DEWALT product-page HTML files.

    Returns:
        A JSON-serializable snapshot payload for vacuums.
    """
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_vacuum(parsed_row):
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
    """Persist a vacuum snapshot to disk as formatted JSON.

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
    """Parse command-line arguments for the vacuum scraper.

    Args:
        None.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Scrape DEWALT vacuum product data.")
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
    """Run the vacuum scraper CLI.

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
    print(f"Wrote {snapshot['product_count']} vacuums to {args.output}")


if __name__ == "__main__":
    main()
