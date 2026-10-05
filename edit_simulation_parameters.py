from dataclasses import dataclass


@dataclass
class SimulationParameters:
    const_price_dyn: float
    const_price_stat: float
    service_fee: float
    base_price_dyn: float
    base_price_stat: float
    htw_profile_number: int
    path_htw_files: list[str]
    path_price_files: list[str]
    days_training: int
    var_e_bat: float
    var_p_bat_c: float
    var_p_bat_d: float
    var_eta_c: float
    var_eta_d: float
    var_eta_bat: float
    var_p_peri: float


def simulation_parameters() -> SimulationParameters:
    """
    Define and return all parameters required for the battery simulation.
    """
    return SimulationParameters(
        const_price_dyn=21,  # ct/kWh, energy price component on top of day-ahead price (E.ON 7/26)
        const_price_stat=31,  # ct/kWh, static tariff energy price (E.ON 7/26)
        service_fee=6,  # ct/kWh (trading)
        base_price_dyn=133 / 12 * 100,  # ct/month, base price dynamic tariff (E.ON 7/26)
        base_price_stat=150 / 12 * 100,  # ct/month, base price static tariff (E.ON 7/26)
        htw_profile_number=43,  # HTW household profile (1-74), 1 s resolution (HTW Berlin)
        path_htw_files=[
            "data/CSV_74_Loadprofiles_1s_W_var/PL1.csv",
            "data/CSV_74_Loadprofiles_1s_W_var/PL2.csv",
            "data/CSV_74_Loadprofiles_1s_W_var/PL3.csv",
        ],  # Raw HTW phase files, summed to the total load (PL1 + PL2 + PL3)
        path_price_files=[
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2026_1.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2026_2.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2026_3.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2026_4.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2026_5.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2026_6.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2026_7.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2026_8.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2026_9.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2025_10.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2025_11.csv",
            "data/energy-charts_day_ahead/energy-charts_day_ahead_2025_12.csv",
        ],  # Monthly day-ahead auction prices, 15 min (Energy-Charts), chronological order
        days_training=35,  # Number of days in the training data set (max. 61 days)
        var_e_bat=2500,  # Battery capacity in Wh (1000-5000 Wh)
        var_p_bat_c=1600,  # Charging power in W
        var_p_bat_d=800,  # Discharging power in W
        var_eta_c=0.97,  # Charging efficiency
        var_eta_d=0.96,  # Discharging efficiency
        var_eta_bat=0.95,  # Battery round-trip efficiency
        var_p_peri=0,  # Peripheral consumption in W
    )
