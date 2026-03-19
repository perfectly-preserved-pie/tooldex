# (Unofficial) DEWALT Tool Table

## This project is not affiliated with, endorsed by, or sponsored by DEWALT, Stanley Black & Decker, or any of their affiliates.

[![Build and Publish](https://github.com/perfectly-preserved-pie/tooldex/actions/workflows/build_and_push.yml/badge.svg)](https://github.com/perfectly-preserved-pie/tooldex/actions/workflows/build_and_push.yml)

DeWalt's website is trash and comically slow to browse and it PISSES me off. So I wanted to build a website that would allow me to quickly compare tools across categories without having to click through dozens of slow pages.

Anyways, this website allows users to filter, sort, and compare tools based on factual attributes such as voltage, dimensions, runtime-related specs, and other structured fields.

I'm using Dash Mantine Components, Dash Bootstrap Components, and Dash AG Grid for the frontend.

The backend is just JSON files.

## AI Disclosure

This app was created entirely with GPT-5.4.
![lulz](assets/aislop.png)

## Run

```bash
uv sync
uv run python3 app.py
```

## Data

Every tool family (drills, circular saws, impact drivers, etc.) has its own dataset stored as a JSON in `data/`.

To refresh a dataset, run the scraper module for that tool family. Examples:

```bash
uv run python3 -m dewalt.scrape # Scrapes all tool families
uv run python3 -m dewalt.tool_families.drill_drivers.scrape # Scrapes just drill drivers
uv run python3 -m dewalt.tool_families.circular_saws.scrape # Scrapes just circular saws
```

## Contributing

Please open an issue or submit a pull request with improvements, bug fixes, or new features.
Alternatively, you can email hey@xxxxxxxxxx
