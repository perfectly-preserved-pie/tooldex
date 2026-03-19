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
    parse_series,
    parse_specifications_table,
    parse_voltage_system,
    sku_looks_like_bare_tool,
)


CATALOG_URL = (
    "https://www.dewalt.com/products/power-tools/nailers-staplers/finish-brad-nailers"
)
DATA_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "dewalt_finish_brad_nailers.json"
)
MEASUREMENT_PATTERN = re.compile(r"\d+(?:-\d+/\d+|\s+\d+/\d+)|\d+/\d+|\d+(?:\.\d+)?")
GAUGE_PATTERN = re.compile(r"(\d+)\s*(?:ga|gauge)", re.I)
FASTENER_RANGE_PATTERN = re.compile(
    r"(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*(?:in\.|\")?\s*(?:-|to)\s*(\d+(?:-\d+/\d+|\.\d+)?|\d+/\d+)\s*(?:in\.|\")",
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


def parse_power_source(specs: dict[str, str], all_text: str) -> str:
    """Parse the finish/brad-nailer power-source classification.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        ``"Cordless"``, ``"Pneumatic"``, or ``"Corded"``.
    """
    raw_value = specs.get("Power Source")
    if raw_value:
        lowered = normalize_text(raw_value).lower()
        if lowered.startswith("cordless") or lowered == "battery":
            return "Cordless"
        if lowered.startswith("corded"):
            return "Corded"
        if "pneumatic" in lowered or "air" in lowered:
            return "Pneumatic"

    lowered = all_text.lower()
    if MAX_VOLTAGE_PATTERN.search(all_text) or "cordless" in lowered or "tool only" in lowered:
        return "Cordless"
    if "pneumatic" in lowered or "psi" in lowered or "air" in lowered:
        return "Pneumatic"
    return "Corded"


def parse_battery_type(specs: dict[str, str]) -> str | None:
    """Parse the finish/brad-nailer battery chemistry label when present.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        The battery type label, or ``None`` when unavailable.
    """
    value = specs.get("Battery Chemistry") or specs.get("Battery Type")
    if value and MAX_VOLTAGE_PATTERN.search(value):
        return None
    return value


def parse_nailer_type(title: str) -> str | None:
    """Parse the finish/brad/pin nailer subtype from the title.

    Args:
        title: Product title string.

    Returns:
        ``"Brad Nailer"``, ``"Finish Nailer"``, or ``"Pin Nailer"``.
    """
    lowered = title.lower()
    if "pin nailer" in lowered:
        return "Pin Nailer"
    if "brad nailer" in lowered:
        return "Brad Nailer"
    if "finish nailer" in lowered:
        return "Finish Nailer"
    return None


def parse_gauge(specs: dict[str, str], title: str) -> int | None:
    """Parse the nail gauge from the title or specs.

    Args:
        specs: Parsed specification label-value map.
        title: Product title string.

    Returns:
        The nail gauge, or ``None`` when unavailable.
    """
    for raw_value in specs.values():
        if not raw_value:
            continue
        match = GAUGE_PATTERN.search(raw_value)
        if match:
            return int(match.group(1))

    match = GAUGE_PATTERN.search(title)
    if match:
        return int(match.group(1))
    return None


def parse_fastener_max_length(specs: dict[str, str], all_text: str) -> float | None:
    """Parse the supported maximum fastener length in inches.

    Args:
        specs: Parsed specification label-value map.
        all_text: Combined product text used for fallback matching.

    Returns:
        The maximum supported fastener length, or ``None`` when unavailable.
    """
    value = parse_measurement_value(specs.get("Nail Length [in]"))
    if value is not None:
        return value

    match = FASTENER_RANGE_PATTERN.search(all_text)
    if match:
        return parse_measurement_value(match.group(2))
    return None


def parse_weight_lbs(specs: dict[str, str]) -> float | None:
    """Parse the preferred tool weight in pounds.

    Args:
        specs: Parsed specification label-value map.

    Returns:
        Tool weight in pounds, or ``None`` when unavailable.
    """
    value = parse_float_value(specs.get("Product Weight [lbs]"))
    if value is not None:
        return value

    weight_oz = parse_float_value(specs.get("Product Weight [oz]"))
    if weight_oz is not None:
        return round(weight_oz / 16, 2)
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
        ``True`` when the product is outside the intended finish/brad-nailer scope.
    """
    lowered = f"{title} {description}".lower()
    if not title or title == "404 Page | DEWALT":
        return True
    for needle in (
        "duplex nailer",
        "concrete nailer",
        "powder-actuated",
        "magazine for",
        "replacement driver blade",
    ):
        if needle in lowered:
            return True
    return not any(needle in lowered for needle in ("finish nailer", "brad nailer", "pin nailer"))


def is_tool_only_cordless(
    sku: str,
    title: str,
    description: str,
    specs: dict[str, str],
) -> bool:
    """Infer whether a cordless finish/brad nailer is the bare-tool SKU.

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
    return any(
        (
            "tool only" in lowered,
            "battery sold separately" in lowered,
            "charger sold separately" in lowered,
            is_set is False,
            sku_looks_like_bare_tool(sku),
        )
    )


def is_supported_finish_brad_nailer(row: dict[str, Any]) -> bool:
    """Apply the finish/brad-nailer product-scope rule for the dashboard.

    Args:
        row: Parsed finish/brad-nailer row.

    Returns:
        ``True`` for pneumatic/corded nailers and bare-tool cordless nailers.
    """
    if row["power_source"] != "Cordless":
        return True
    return bool(row["tool_only"])


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
    """Parse a finish/brad-nailer product page into a structured row.

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
        "category": "Finish/Brad Nailer",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": voltage_system,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": parse_nominal_voltage_v(disclaimers, max_voltage_v),
        "battery_type": parse_battery_type(specs),
        "battery_capacity_ah": parse_float_value(specs.get("Battery Capacity [Ah]")),
        "nailer_type": parse_nailer_type(title),
        "gauge": parse_gauge(specs, title),
        "magazine_angle_deg": parse_measurement_value(specs.get("Magazine Angle [deg]")),
        "magazine_loading": specs.get("Magazine Loading"),
        "magazine_capacity": parse_int_value(specs.get("Magazine Capacity")),
        "fastener_max_length_in": parse_fastener_max_length(specs, all_text),
        "weight_lbs": parse_weight_lbs(specs),
        "brushless": parse_bool_feature(specs, "Is Brushless?", lowered, ("brushless",)),
        "led_light": parse_bool_feature(specs, "Has LED Light?", lowered, ("led light",)),
        "jam_clearing": parse_bool_feature(
            specs,
            "Has Jam Clearing?",
            lowered,
            ("jam release", "jam clearing"),
        ),
        "tool_free_depth_adjust": any(
            needle in lowered
            for needle in (
                "tool-free depth adjustment",
                "tool-free depth-of-drive adjustment",
                "tool-free depth adjust",
            )
        ),
        "low_nail_lockout": "low nail lockout" in lowered,
        "selectable_trigger": any(
            needle in lowered
            for needle in (
                "selectable trigger",
                "sequential or contact actuation",
            )
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
    """Fetch all paginated finish/brad-nailer catalog listing pages.

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
    """Collect unique product cards from the finish/brad-nailer listing pages.

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
    """Build a finish/brad-nailer snapshot by scraping the live DEWALT catalog.

    Args:
        None.

    Returns:
        A JSON-serializable snapshot payload for finish/brad nailers.
    """
    listing_pages = fetch_listing_pages()
    product_cards = collect_product_cards(listing_pages)

    rows = []
    for card in product_cards:
        html_text = fetch_url(card["url"])
        parsed_row = parse_product_page(card["url"], html_text)
        if parsed_row and is_supported_finish_brad_nailer(parsed_row):
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
    """Build a finish/brad-nailer snapshot from cached product-page HTML files.

    Args:
        source_dir: Directory containing saved DEWALT product-page HTML files.

    Returns:
        A JSON-serializable snapshot payload for finish/brad nailers.
    """
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_supported_finish_brad_nailer(parsed_row):
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
    """Persist a finish/brad-nailer snapshot to disk as formatted JSON.

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
    """Parse command-line arguments for the finish/brad-nailer scraper.

    Args:
        None.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Scrape DEWALT finish/brad-nailer product data."
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
    """Run the finish/brad-nailer scraper CLI.

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
    print(f"Wrote {snapshot['product_count']} finish/brad nailers to {args.output}")


if __name__ == "__main__":
    main()
