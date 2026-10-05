import numpy as np
import pandas as pd
from fn_charging_schedule import charging_schedule
from fn_load_forecast import prepare_load_training_data, load_forecast
from fn_day_ahead_data import day_ahead_data


def battery_simulation(
        const_price_dyn,
        load_profile,
        path_price_files,
        days_training,
        var_e_bat,
        var_p_bat_c,
        var_p_bat_d,
        var_eta_c,
        var_eta_d,
        var_eta_bat,
        var_p_peri
):
    """
    Performance simulation model for AC-coupled battery systems.

    A load forecast is generated for every simulated day, an optimal
    charging schedule is derived from it, and the battery is then simulated
    in 1 s resolution against the measured load.
    """

    dt = 1.0  # Time step [s]

    # --------------------------------------------------
    # Cut load profile to simulation length
    # --------------------------------------------------

    # Get simulation dates to apply to load profile
    var_price_dyn, day_ahead_days, simulation_dates = day_ahead_data(
        files=path_price_files
    )

    var_price_dyn = np.repeat(var_price_dyn, 900)  # Dynamic price in ct/kWh (1 s resolution)

    # First and last timestamp
    first_ts = simulation_dates[0]
    last_ts = simulation_dates[-1] + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    # Load 1 s resolution data
    df_load_profile = pd.DataFrame({"power": load_profile})  # [W], 1 s resolution

    year = first_ts.year

    df_load_profile["ts"] = pd.date_range(
        start=f"{year}-01-01 00:00:00",
        end=f"{year}-12-31 23:59:59",
        freq="s"
    )

    df_load_profile = df_load_profile[(df_load_profile["ts"] >= first_ts) & (df_load_profile["ts"] <= last_ts)].copy()

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    ts = df_load_profile['ts'].values  # Timestamp
    pl = df_load_profile['power'].values  # Load power [W]
    pperi = np.zeros_like(pl, dtype=float) + var_p_peri  # Auxiliary consumption/standby [W]

    pbat = np.zeros_like(pl, dtype=float)  # Battery DC power [W]
    pbs = np.zeros_like(pl, dtype=float)  # Battery AC power [W]

    soc = np.zeros_like(pl, dtype=float)  # State of charge [-]

    var_soc0 = 0.0  # Initial SOC

    del df_load_profile

    # --------------------------------------------------
    # Prepare load training data once (before the day loop)
    # --------------------------------------------------

    df_15min = prepare_load_training_data(
        load_profile=load_profile,
        var_p_peri=var_p_peri,
        year=first_ts.year
    )

    # --------------------------------------------------
    # Battery simulation
    # --------------------------------------------------

    current_simulation_day = -1
    soc0 = var_soc0
    seconds_per_day = 86400

    for t1 in range(len(pl)):

        t2 = t1 % seconds_per_day  # 0 -> 86399

        # Start of a new day: load forecast and charging schedule
        if t2 == 0:

            current_simulation_day = current_simulation_day + 1

            df_load_forecast = load_forecast(
                df_15min=df_15min,
                days_training=days_training,
                forecast_day=simulation_dates[current_simulation_day]
            )

            p_charge, p_discharge = charging_schedule(
                const_price_dyn=const_price_dyn,
                df_load_forecast=df_load_forecast,  # W
                day_ahead_data_day=day_ahead_days[simulation_dates[current_simulation_day]],
                var_e_bat=var_e_bat,  # Wh
                var_p_bat_c=var_p_bat_c,  # W
                var_p_bat_d=var_p_bat_d,  # W
                var_soc0=soc0,  # Between 0 and 1
                var_eta_c=var_eta_c,
                var_eta_d=var_eta_d,
                var_eta_bat=var_eta_bat
            )

            pc_schedule = np.repeat(p_charge, 900)  # Charging power [W] (1 s resolution)
            pd_schedule = np.repeat(p_discharge, 900)  # Discharging power [W] (1 s resolution)

            print("Simulation day:", current_simulation_day)

        e_b0 = soc0 * var_e_bat  # Battery energy [Wh]
        pr = - pl[t1] - pperi[t1]  # Residual power [W]

        # Charging
        if float(pc_schedule[t2]) > 0.0 and soc0 < 1.0:
            p_bs = min(float(pc_schedule[t2]), var_p_bat_c)
            p_bat = p_bs * var_eta_c

        # Discharging
        elif float(pd_schedule[t2]) > 0.0 and pr < 0.0 and soc0 > 0.0:
            p_bs = max(pr, -var_p_bat_d)
            p_bat = p_bs * (1 / var_eta_d)

        # No battery action
        else:
            p_bs = 0.0
            p_bat = 0.0

        # Battery energy update
        if p_bat > 0:
            e_b = e_b0 + p_bat * np.sqrt(var_eta_bat) * dt / 3600.0
        elif p_bat < 0:
            e_b = e_b0 + p_bat / np.sqrt(var_eta_bat) * dt / 3600.0
        else:
            e_b = e_b0

        pbat[t1] = p_bat
        pbs[t1] = p_bs
        soc0 = e_b / var_e_bat
        soc[t1] = soc0

    # --------------------------------------------------
    # Outputs
    # --------------------------------------------------

    return var_price_dyn, ts, pl, pperi, pbat, pbs, soc
