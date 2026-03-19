from __future__ import annotations

import argparse
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter


CATALOG_URL = "https://www.dewalt.com/products/power-tools/grinders-polishers/angle-grinders"
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "dewalt_angle_grinders.json"
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
WHEEL_PATTERN = re.compile(r'(\d+(?:[ -]\d+/\d+)?(?:\.\d+)?)\s*(?:in\.|")', re.I)
RPM_PATTERN = re.compile(r"(\d[\d,]{2,5})\s*rpm", re.I)
AMP_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*amp\b", re.I)
HP_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*hp\b", re.I)
MWO_PATTERN = re.compile(r"(\d[\d,]*)\s*mwo\b", re.I)
WATTS_OUT_PATTERN = re.compile(r"(\d[\d,]*)\s*(?:max\s+)?watts?\s+out", re.I)
POWER_INPUT_PATTERN = re.compile(r"power input:\s*(\d[\d,]*)\s*watts", re.I)
MAX_VOLTAGE_PATTERN = re.compile(r"(\d{2,3})\s*v\s*max", re.I)
NOMINAL_VOLTAGE_PATTERN = re.compile(r"nominal voltage is\s*(\d{2,3})", re.I)


def fetch_url(url: str, timeout: int = 30) -> str:
    """Fetch a DEWALT page with ``requests``.

    Args:
        url: Fully qualified page URL to request.
        timeout: Maximum request time in seconds.

    Returns:
        The decoded HTML body as a string.
    """
    response = SESSION.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def normalize_text(raw_text: str) -> str:
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
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def get_soup_text(node: Any) -> str:
    if not node:
        return ""
    return normalize_text(node.get_text("\n", strip=True))


def extract_text_items(soup: BeautifulSoup, selector: str) -> list[str]:
    items = [get_soup_text(node) for node in soup.select(selector)]
    return unique_preserving_order(items)


def extract_section_items(soup: BeautifulSoup, section_id: str) -> list[str]:
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


def parse_mixed_number(token: str) -> float:
    token = token.strip().replace('"', "")
    if re.fullmatch(r"\d+\s+\d+/\d+", token):
        whole, fraction = token.split()
        numerator, denominator = fraction.split("/")
        return int(whole) + int(numerator) / int(denominator)
    if re.fullmatch(r"\d+-\d+/\d+", token):
        whole, fraction = token.split("-", 1)
        numerator, denominator = fraction.split("/")
        return int(whole) + int(numerator) / int(denominator)
    if re.fullmatch(r"\d+/\d+", token):
        numerator, denominator = token.split("/")
        return int(numerator) / int(denominator)
    return float(token)


def parse_wheel_range(title: str) -> tuple[float | None, float | None]:
    values: list[float] = []
    for token in WHEEL_PATTERN.findall(title):
        try:
            values.append(parse_mixed_number(token))
        except ValueError:
            continue

    if not values:
        return None, None
    if len(values) == 1:
        return values[0], values[0]
    return values[0], values[1]


def parse_switch_type(text: str) -> str | None:
    lowered = text.lower()
    if "rat tail" in lowered:
        return "Rat tail"
    for needle, label in (
        ("paddle-switch", "Paddle"),
        ("paddle switch", "Paddle"),
        ("slide-switch", "Slide"),
        ("slide switch", "Slide"),
        ("trigger-switch", "Trigger"),
        ("trigger switch", "Trigger"),
        ("trigger grip", "Trigger grip"),
        ("two stage trigger", "Two-stage trigger"),
        ("trigger handle", "Trigger"),
    ):
        if needle in lowered:
            return label
    return None


def parse_rpm(text: str) -> int | None:
    values = [int(value.replace(",", "")) for value in RPM_PATTERN.findall(text)]
    return max(values) if values else None


def parse_amp_rating(text: str) -> float | None:
    values = [float(value) for value in AMP_PATTERN.findall(text)]
    return max(values) if values else None


def parse_horsepower(text: str) -> float | None:
    values = [float(value) for value in HP_PATTERN.findall(text)]
    return max(values) if values else None


def parse_max_watts_out(text: str) -> int | None:
    values = [int(value.replace(",", "")) for value in MWO_PATTERN.findall(text)]
    values.extend(int(value.replace(",", "")) for value in WATTS_OUT_PATTERN.findall(text))
    return max(values) if values else None


def parse_power_input_watts(applications: list[str], text: str) -> int | None:
    for item in applications:
        match = POWER_INPUT_PATTERN.search(item)
        if match:
            return int(match.group(1).replace(",", ""))
    match = POWER_INPUT_PATTERN.search(text)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def parse_max_voltage_v(text: str) -> int | None:
    match = MAX_VOLTAGE_PATTERN.search(text)
    return int(match.group(1)) if match else None


def parse_nominal_voltage_v(disclaimers: list[str], max_voltage_v: int | None) -> int | None:
    disclaimer_text = " ".join(disclaimers)
    match = NOMINAL_VOLTAGE_PATTERN.search(disclaimer_text)
    if match:
        return int(match.group(1))
    if max_voltage_v == 20:
        return 18
    if max_voltage_v == 60:
        return 54
    return None


def parse_series(title: str) -> list[str]:
    lowered = title.lower()
    series = []
    for needle, label in (
        ("atomic", "ATOMIC"),
        (" xr ", "XR"),
        ("xr ", "XR"),
        ("flexvolt advantage", "FLEXVOLT ADVANTAGE"),
        ("flexvolt", "FLEXVOLT"),
        ("powerstack", "POWERSTACK"),
        ("powerpack", "POWERPACK"),
    ):
        if needle in lowered:
            series.append(label)
    return unique_preserving_order(series)


def parse_power_source(all_text: str, max_voltage_v: int | None) -> str:
    lowered = all_text.lower()
    if max_voltage_v or "cordless" in lowered or "battery" in lowered:
        return "Cordless"
    return "Corded"


def sku_looks_like_bare_tool(sku: str) -> bool:
    return "B" in sku.upper()


def is_bare_tool(row: dict[str, Any]) -> bool:
    if row["power_source"] != "Cordless":
        return True
    title_lower = row["title"].lower()
    return "tool only" in title_lower or sku_looks_like_bare_tool(row["sku"])


def parse_canonical_url(soup: BeautifulSoup) -> str:
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        return canonical["href"]
    return ""


def format_iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_product_page(url: str, html_text: str) -> dict[str, Any] | None:
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

    title_and_description = f"{title} {description}".lower()
    if "side handle" in title.lower() and "grinder" not in title.lower():
        return None
    if "grinder" not in title_and_description and "grinding" not in title_and_description:
        return None

    primary_features = extract_text_items(soup, "li.feature-list-li")
    additional_features = extract_text_items(soup, "li.additional-feature-list-li")
    includes = extract_section_items(soup, "product-includes-accordion")
    applications = extract_section_items(soup, "product-applications-data")
    disclaimers = extract_section_items(soup, "disclaimer")

    all_text_parts = [
        title,
        description,
        *primary_features,
        *additional_features,
        *includes,
        *applications,
        *disclaimers,
    ]
    all_text = " ".join(part for part in all_text_parts if part)
    lowered = all_text.lower()
    max_voltage_v = parse_max_voltage_v(all_text)
    nominal_voltage_v = parse_nominal_voltage_v(disclaimers, max_voltage_v)
    wheel_min_in, wheel_max_in = parse_wheel_range(title)
    sku = url.rstrip("/").split("/product/")[-1].split("/", 1)[0].upper()
    power_source = parse_power_source(all_text, max_voltage_v)
    tool_only = power_source == "Cordless" and (
        "tool only" in title.lower() or sku_looks_like_bare_tool(sku)
    )

    return {
        "sku": sku,
        "title": title,
        "url": url,
        "category": "Angle Grinder",
        "series": parse_series(title),
        "power_source": power_source,
        "voltage_system": f"{max_voltage_v}V MAX" if max_voltage_v else None,
        "max_voltage_v": max_voltage_v,
        "nominal_voltage_v": nominal_voltage_v,
        "amp_rating": parse_amp_rating(all_text),
        "horsepower_hp": parse_horsepower(all_text),
        "max_watts_out": parse_max_watts_out(all_text),
        "power_input_watts": parse_power_input_watts(applications, all_text),
        "wheel_min_in": wheel_min_in,
        "wheel_max_in": wheel_max_in,
        "switch_type": parse_switch_type(title + " " + description + " " + " ".join(primary_features)),
        "rpm_max": parse_rpm(all_text),
        "brushless": "brushless" in lowered,
        "variable_speed": "variable speed" in lowered,
        "kit": " kit" in title.lower() or title.lower().endswith("kit"),
        "tool_only": tool_only,
        "battery_included": any("battery" in item.lower() for item in includes),
        "charger_included": any("charger" in item.lower() for item in includes),
        "anti_rotation_system": "anti-rotation" in lowered,
        "e_clutch": "e-clutch" in lowered,
        "kickback_brake": "kickback brake" in lowered,
        "wireless_tool_control": "wireless tool control" in lowered,
        "tool_connect_ready": "tool connect" in lowered or "chip ready" in lowered,
        "power_loss_reset": "power loss reset" in lowered,
        "no_volt_switch": "no-volt switch" in lowered,
        "lanyard_ready": "lanyard ready" in lowered,
        "description": description,
        "features": primary_features,
        "additional_features": additional_features,
        "includes": includes,
        "applications": applications,
        "disclaimers": disclaimers,
    }


def fetch_listing_pages() -> dict[str, str]:
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
    urls: list[str] = []
    for html_text in listing_pages.values():
        urls.extend(PRODUCT_URL_PATTERN.findall(html_text))
    return sorted(set(urls))


def build_snapshot_from_live_catalog() -> dict[str, Any]:
    listing_pages = fetch_listing_pages()
    product_urls = collect_product_urls(listing_pages)

    rows = []
    for product_url in product_urls:
        html_text = fetch_url(product_url)
        parsed_row = parse_product_page(product_url, html_text)
        if parsed_row and is_bare_tool(parsed_row):
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
    rows = []
    html_files = sorted(source_dir.glob("*.html"))
    for html_file in html_files:
        html_text = html_file.read_text()
        canonical_url = parse_canonical_url(BeautifulSoup(html_text, "html.parser"))
        if not canonical_url:
            continue
        parsed_row = parse_product_page(canonical_url, html_text)
        if parsed_row and is_bare_tool(parsed_row):
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape DEWALT angle grinder product data.")
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
    args = parse_args()
    if args.source_dir:
        snapshot = build_snapshot_from_directory(args.source_dir)
    else:
        snapshot = build_snapshot_from_live_catalog()

    save_snapshot(snapshot, args.output)
    print(f"Wrote {snapshot['product_count']} grinders to {args.output}")


if __name__ == "__main__":
    main()
