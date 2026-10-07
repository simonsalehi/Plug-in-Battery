import pandas as pd
from functions.fn_battery_simulation import battery_simulation
from functions.fn_battery_simulation_trading import battery_simulation_trading
from pathlib import Path
from edit_simulation_parameters import simulation_parameters
from functions.fn_htw_profiles import load_htw_profile
from functions.fn_download_prices import download_price_files

"""
Load parameters, load the selected HTW load profile, run two battery simulations (AC-coupled system) and save the results:

1) Standard simulation (fn_battery_simulation):
   Generates daily load forecasts from historic load data. The 1 s load profile
   is read once and prepared for training (prepare_load_training_data) before the
   daily simulation loop. The daily load forecasts are passed together with the
   day-ahead auction data (15 min) to fn_charging_schedule, which generates an
   optimized charging schedule (charging and discharging windows) that minimizes
   grid cost given the forecast load. With this schedule and the real (measured)
   load data, battery charging and discharging is simulated in 1 s resolution.

2) Trading simulation (fn_battery_simulation_trading):
   No load measurement or load forecast is used. Instead, fn_charging_schedule_trading
   generates a schedule purely from the day-ahead auction price (15 min): charging
   when the price is low and discharging (selling) when the price is high, net of
   the service fee. The battery is then simulated in 1 s resolution against this
   price-driven schedule.

Both simulations use the same day-ahead price data and battery parameters. Their
results (including SOC and battery power) are combined into a single results CSV
for comparison.
"""

# -------------------------------
# Load simulation parameters
# -------------------------------
par = simulation_parameters()

# -------------------------------
# Download missing day-ahead price files (Energy-Charts API)
# -------------------------------
download_price_files(par.path_price_files)

# -------------------------------
# Load HTW load profile (selected in the parameters, summed over the three phases)
# -------------------------------
load_profile = load_htw_profile(
        profile_number=par.htw_profile_number,
        input_files=par.path_htw_files
)

# -------------------------------
# Run simulation
# -------------------------------
var_price_dyn, ts, pl, pperi, pbat, pbs, soc = battery_simulation(
        const_price_dyn=par.const_price_dyn,
        load_profile=load_profile,
        path_price_files=par.path_price_files,
        days_training=par.days_training,
        var_e_bat=par.var_e_bat,  # Wh
        var_p_bat_c=par.var_p_bat_c,  # W
        var_p_bat_d=par.var_p_bat_d,  # W
        var_eta_c=par.var_eta_c,
        var_eta_d=par.var_eta_d,
        var_eta_bat=par.var_eta_bat,
        var_p_peri=par.var_p_peri
)

# -------------------------------
# Run trading simulation
# -------------------------------
var_price_dyn, ts, pl, pperi, pbat_t, pbs_t, soc_t = battery_simulation_trading(
        const_price_dyn=par.const_price_dyn,
        service_fee=par.service_fee,
        load_profile=load_profile,
        path_price_files=par.path_price_files,
        var_e_bat=par.var_e_bat,  # Wh
        var_p_bat_c=par.var_p_bat_c,  # W
        var_p_bat_d=par.var_p_bat_d,  # W
        var_eta_c=par.var_eta_c,
        var_eta_d=par.var_eta_d,
        var_eta_bat=par.var_eta_bat,
        var_p_peri=par.var_p_peri
)

# -------------------------------
# Save the results to CSV
# -------------------------------
df_results = pd.DataFrame({
    "timestamp": ts,
    "dynamic_price_ct_kWh": var_price_dyn,
    "load_power_W": pl,
    "aux_power_W": pperi,
    "battery_dc_power_W": pbat,
    "battery_ac_power_W": pbs,
    "soc": soc,
    "battery_dc_power_trading_W": pbat_t,
    "battery_ac_power_trading_W": pbs_t,
    "soc_trading": soc_t
})

Path("data/results").mkdir(parents=True, exist_ok=True)
df_results.to_csv(
    f"data/results/battery_simulation_results_Pl_{par.htw_profile_number}.csv",
    index=False
)
