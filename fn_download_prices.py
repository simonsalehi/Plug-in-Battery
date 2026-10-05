"""
Download monthly day-ahead prices (DE-LU) from the Energy-Charts API.

The month of each file is taken from its name: energy-charts_day_ahead_2026_3.csv
is filled with the prices of March 2026. Existing files are skipped.

Data: Bundesnetzagentur | SMARD.de, CC BY 4.0, via Energy-Charts.info (attribution required).
"""

import time
from pathlib import Path

import pandas as pd
import requests


def download_price_files(files):
    downloaded = False

    for file in files:
        if Path(file).exists():
            continue

        # The API allows 2 requests per minute -> wait between requests
        if downloaded:
            time.sleep(30)

        # "..._2026_3.csv" -> year 2026, month 3
        year, month = Path(file).stem.split("_")[-2:]
        year, month = int(year), int(month)

        # First and last quarter hour of the month in German local time, given in UTC
        # (the API wants e.g. start=2026-01-01T17:00Z)
        start = pd.Timestamp(year=year, month=month, day=1, tz="Europe/Berlin")
        end = start + pd.DateOffset(months=1) - pd.Timedelta(minutes=15)

        # One request = one month of 15 min prices
        response = requests.get(
            "https://api.energy-charts.info/v2/price",
            params={
                "bzn": "DE-LU",
                "start": start.tz_convert("UTC").strftime("%Y-%m-%dT%H:%MZ"),
                "end": end.tz_convert("UTC").strftime("%Y-%m-%dT%H:%MZ"),
            },
            timeout=60,
        )
        response.raise_for_status()

        # Keep only timestamp and price, same columns as the Energy-Charts CSV export
        rows = [(e["timestamp"], e["values"]["day_ahead_price"]) for e in response.json()["data"]]
        df = pd.DataFrame(rows, columns=["Datum", "Day Ahead Auktion DE-LU (EUR/MWh)"])

        Path(file).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(file, index=False)
        downloaded = True
        print(f"Downloaded {year}-{month:02d} -> {file}")


if __name__ == "__main__":
    from edit_simulation_parameters import simulation_parameters

    download_price_files(simulation_parameters().path_price_files)
