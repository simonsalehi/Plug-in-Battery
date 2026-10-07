import pandas as pd
from prophet import Prophet


def prepare_load_training_data(
        load_profile,
        var_p_peri,
        year
):
    """
    Take the 1 s load profile (HTW Berlin, array in W), add peripheral consumption,
    build a full-year timestamp index, prepend a shifted Nov/Dec block for
    seasonal context, and resample to 15-minute resolution.

    Call this once before the simulation day loop; the returned DataFrame is
    then passed to load_forecast() for every day, which avoids re-reading and
    re-resampling the profile on each call.
    """

    # 1 s resolution data
    df_sec = pd.DataFrame({"y": load_profile + var_p_peri})  # [W]

    df_sec["ds"] = pd.date_range(
        start=f"{year}-01-01 00:00:00",
        end=f"{year}-12-31 23:59:59",
        freq="s"
    )

    # Extract November and December
    df_nov_dec = df_sec[df_sec["ds"].dt.month.isin([11, 12])].copy()

    # Shift them back one year (to Nov-Dec of the prior year)
    df_nov_dec["ds"] = df_nov_dec["ds"] - pd.DateOffset(years=1)

    # Prepend to original dataframe
    df_sec = pd.concat([df_nov_dec, df_sec], ignore_index=True)

    # Ensure chronological order
    df_sec = df_sec.sort_values("ds").reset_index(drop=True)

    # Resample to 15-minute resolution
    df_15min = df_sec.set_index("ds").resample("15min").mean().reset_index()

    return df_15min


def load_forecast(
        df_15min,
        days_training,
        forecast_day
):
    """
    Takes the pre-resampled 15-minute training series (from
    prepare_load_training_data) and returns the load forecast for a single
    forecast_day.
    """

    # Define training range
    train_end_dt = forecast_day - pd.Timedelta(minutes=15)
    train_start_dt = train_end_dt - pd.Timedelta(days=days_training)

    # Slice training data
    train = df_15min[(df_15min["ds"] >= train_start_dt) & (df_15min["ds"] <= train_end_dt)].copy()

    # Fit Prophet model
    m = Prophet(seasonality_mode='multiplicative')
    m.fit(train[["ds", "y"]])

    # Forecast for the day (96 periods of 15 min)
    future = m.make_future_dataframe(periods=96, freq="15min")
    forecast = m.predict(future)
    forecast["yhat"] = forecast["yhat"].clip(lower=0)

    # Keep only the forecasted day (96 points)
    df_load_forecast = forecast.tail(96)[
        ["ds", "yhat"]
    ].copy()

    return df_load_forecast
