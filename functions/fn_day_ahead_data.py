import re

import numpy as np
import pandas as pd


def detect_year(first_datum, first_file):
    """
    Detect the start year of the price data: first from the first "Datum" value
    of the first file (any format containing a 4-digit year), otherwise from
    the file name (e.g. energy-charts_day_ahead_2026_1.csv).
    """
    pattern = r"(?<!\d)(20\d{2})(?!\d)"
    match = re.search(pattern, str(first_datum)) or re.search(pattern, str(first_file))
    if match is None:
        raise ValueError(
            f"Could not detect the year from '{first_datum}' or '{first_file}'."
        )
    return int(match.group(1))


def day_ahead_data(
        files
):
    """
    Read monthly day-ahead price CSV files (Energy-Charts), ignore the original
    timestamps, generate a continuous 15-minute timestamp index starting on
    January 1st of the year detected in the first price file, and return the
    complete series together with the daily data.

    Parameters
    ----------
    files : list of str
        List of monthly CSV files in chronological order.

    Returns
    -------
    day_ahead_all : numpy.ndarray
        Complete price series (ct/kWh).

    day_ahead_days : dict
        Dictionary mapping each day (Timestamp) to a DataFrame.

    simulation_dates : numpy.ndarray
        Sorted array of simulation dates.
    """

    # Read and concatenate all monthly files
    df_all = pd.concat(
        (pd.read_csv(file) for file in files),
        ignore_index=True
    )

    # Detect the start year from the first file (before the column is dropped)
    year_price = detect_year(df_all["Datum"].iloc[0], files[0])

    # Rename price column
    df_all = df_all.rename(columns={
        "Day Ahead Auktion DE-LU (EUR/MWh)": "price ct/kWh"
    })

    # Convert EUR/MWh -> ct/kWh
    df_all["price ct/kWh"] = df_all["price ct/kWh"] * 100 / 1000

    # Ignore original timestamps ("Datum" column of the Energy-Charts export)
    df_all = df_all.drop(columns="Datum")

    # Generate new timestamps (15 min resolution)
    df_all.index = pd.date_range(
        start=f"{year_price}-01-01 00:00",
        periods=len(df_all),
        freq="15min"
    )
    df_all.index.name = "timestamp"

    # Group by day
    day_ahead_days = {}
    for date, daily_df in df_all.groupby(df_all.index.date):
        day_ahead_days[pd.Timestamp(date)] = daily_df.reset_index()

    # Sorted simulation dates
    simulation_dates = np.array(sorted(day_ahead_days.keys()))

    # Complete price array
    day_ahead_all = df_all["price ct/kWh"].values  # ct/kWh

    return day_ahead_all, day_ahead_days, simulation_dates
