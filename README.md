# Plug-in Battery Simulation with Dynamic Electricity Tariff

Simulation of a plug-in (AC-coupled) home battery storage system in 1 s resolution. The project compares the
electricity cost of a household under:

1. a **static tariff** (no battery)
2. a **dynamic tariff** (day-ahead price + fixed price component, no battery)
3. a **dynamic tariff with battery**, optimized against a daily load forecast
4. a **dynamic tariff with battery and trading**, optimized purely on day-ahead prices (including a service fee)

## Data sources

| Data | Source                                                                               | Resolution |
|------|--------------------------------------------------------------------------------------|------------|
| Day-ahead auction prices (DE-LU) | [Energy-Charts](https://www.energy-charts.info)                                      | 15 min, monthly CSV files (downloaded automatically) |
| Household load profile (one of 74, default `Pl_43`) | [HTW Berlin](https://solar.htw-berlin.de/elektrische-lastprofile-fuer-wohngebaeude/) | 1 s, one full year |

Expected input files (paths are set in `edit_simulation_parameters.py`):

```
data/
├── CSV_74_Loadprofiles_1s_W_var/          # raw HTW Berlin download (only PL1.csv, PL2.csv, PL3.csv needed)
│   ├── PL1.csv
│   ├── PL2.csv
│   └── PL3.csv
├── energy-charts_day_ahead/
│   └── energy-charts_day_ahead_<year>_<month>.csv   # downloaded automatically; columns: "Datum", "Day Ahead Auktion DE-LU (EUR/MWh)"
└── results/                               # output directory (must exist)
```

The selected load profile is read directly from the raw HTW Berlin files, see [Preparing the HTW Berlin load profiles](#preparing-the-htw-berlin-load-profiles).

## Project structure

The scripts (`run_simulation.py`, `inspect_results.py`, `edit_simulation_parameters.py`) are in the project root, all function modules (`fn_*.py`) are in the `functions/` folder. Run all commands from the project root.

| File | Purpose |
|------|---------|
| `edit_simulation_parameters.py` | All parameters (tariffs, battery, data paths, training length) |
| `functions/fn_htw_profiles.py` | Loads the selected HTW Berlin profile: reads its column from PL1/PL2/PL3 and sums the three phases |
| `run_simulation.py` | Runs both simulations and writes the results CSV |
| `inspect_results.py` | Computes costs/savings from the results CSV and plots them |
| `functions/fn_battery_simulation.py` | 1 s battery simulation using a load forecast based schedule |
| `functions/fn_battery_simulation_trading.py` | 1 s battery simulation using a price-only (trading) schedule |
| `functions/fn_charging_schedule.py` | MILP: minimizes grid cost given forecast load and prices |
| `functions/fn_charging_schedule_trading.py` | MILP: maximizes trading revenue net of service fee |
| `functions/fn_load_forecast.py` | Prepares training data and creates the daily load forecast (Prophet) |
| `functions/fn_day_ahead_data.py` | Reads and splits the day-ahead price files into daily data |
| `functions/fn_download_prices.py` | Downloads missing monthly day-ahead price files from the Energy-Charts API |

## Installation

Python 3.9+ is recommended. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Preparing the HTW Berlin load profiles

The household load profiles are not included in this repository. The raw files only have to be downloaded once;
no further preprocessing or intermediate files are needed.

> **License:** The HTW Berlin load profiles are licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

1. **Download the zip file.** Open the
   [HTW Berlin page on electrical load profiles for residential buildings](https://solar.htw-berlin.de/elektrische-lastprofile-fuer-wohngebaeude/)
   and download `CSV_74_Loadprofiles_1s_W_var.zip` (1 s resolution, 74 profiles, one full year).
   The file is large, so make sure enough disk space is available.

2. **Unzip it.** Only three of the extracted files are needed (the three phases of all 74 profiles):

   - `PL1.csv`
   - `PL2.csv`
   - `PL3.csv`

   All other files in the archive can be deleted.

3. **Place the files in the data folder:**

   ```
   data/CSV_74_Loadprofiles_1s_W_var/PL1.csv
   data/CSV_74_Loadprofiles_1s_W_var/PL2.csv
   data/CSV_74_Loadprofiles_1s_W_var/PL3.csv
   ```

   The paths are set in `path_htw_files` in `edit_simulation_parameters.py`. Adjust them if your layout differs.

4. **Select a profile.** Set `htw_profile_number` (1-74) in `edit_simulation_parameters.py`.

### Yearly energy consumption of the profiles

The 15 profiles with the lowest yearly energy consumption, to help choosing `htw_profile_number`:

| `htw_profile_number` | Yearly energy (kWh) |
|---------------------:|--------------------:|
|                    6 | 1398.9 |
|                   24 | 1847.4 |
|                   43 | 2296.4 |
|                   51 | 2391.9 |
|                   44 | 2629.9 |
|                    4 | 2663.4 |
|                    7 | 2937.9 |
|                   34 | 3081.4 |
|                    5 | 3196.4 |
|                   16 | 3196.7 |
|                    1 | 3238.7 |
|                   14 | 3259.7 |
|                   10 | 3369.7 |
|                   53 | 3390.9 |
|                   15 | 3402.6 |

When `run_simulation.py` starts, `functions.fn_htw_profiles.load_htw_profile()` reads only the column of the selected
profile from the three files (chunk by chunk, RAM-friendly) and sums the phases (PL1 + PL2 + PL3). This takes a
moment, since the raw files are large. The profile is not saved separately: it is stored together with the
simulation results in the column `load_power_W`.

## Day-ahead prices

The price files are downloaded from the [Energy-Charts API](https://api.energy-charts.info) (endpoint `/v2/price`,
bidding zone DE-LU) at the start of `run_simulation.py`.

- The months to download are taken from the file names in `path_price_files`: `energy-charts_day_ahead_2026_3.csv`
  contains March 2026 (names must end with `_<year>_<month>.csv`).
- Files that already exist are skipped.
- The API allows 2 requests per minute, so the script waits 30 s between requests.
- Only complete months can be downloaded.
- To download without running the simulation: `python -m functions.fn_download_prices`

Data source: Bundesnetzagentur | SMARD.de, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
provided by [Energy-Charts.info](https://www.energy-charts.info) (attribution required when publishing results).

## Usage

1. Download the raw HTW Berlin load profile files (see [Preparing the HTW Berlin load profiles](#preparing-the-htw-berlin-load-profiles)).
   The day-ahead price files are downloaded automatically (see [Day-ahead prices](#day-ahead-prices)).
2. Adjust the parameters in `edit_simulation_parameters.py` (including `htw_profile_number`)
3. Run the simulation:

   ```bash
   python run_simulation.py
   ```

4. Inspect the results:

   ```bash
   python inspect_results.py
   ```

## Parameters

Defined in `edit_simulation_parameters.py`:

| Parameter | Unit | Description |
|-----------|------|-------------|
| `const_price_dyn` | ct/kWh | Price component added to the day-ahead price (dynamic tariff) |
| `const_price_stat` | ct/kWh | Energy price of the static tariff |
| `service_fee` | ct/kWh | Service fee for trading (half applied on charging, half on discharging) |
| `base_price_dyn`, `base_price_stat` | ct/month | Monthly base price of the respective tariff |
| `htw_profile_number` | – | Number (1-74) of the HTW Berlin household load profile to simulate |
| `path_htw_files` | – | The three raw HTW Berlin phase files (`PL1.csv`, `PL2.csv`, `PL3.csv`) |
| `path_price_files` | – | Monthly day-ahead price files in chronological order |
| `days_training` | days | Length of the load forecast training window (max. 61 days) |
| `var_e_bat` | Wh | Battery capacity |
| `var_p_bat_c`, `var_p_bat_d` | W | Maximum charging / discharging power |
| `var_eta_c`, `var_eta_d` | – | Charging / discharging efficiency |
| `var_eta_bat` | – | Battery efficiency (applied as `sqrt` on both charging and discharging) |
| `var_p_peri` | W | Constant consumption of peripherals |

## Method

- **Time resolution:** The schedule is optimized in 15 min steps (day-ahead resolution) and applied to the battery model in 1 s steps.
- **Daily loop:** For each day, a schedule is computed from the battery SOC at the end of the previous day.
- **Load forecast (standard simulation):** A Prophet model (multiplicative seasonality) is trained on the last `days_training` days of the 15 min load series and forecasts the next 96 steps. The Nov/Dec block of the profile is shifted back one year and prepended to provide training data at the start of the year.
- **Schedule optimization:** A mixed-integer linear program (CVXPY with HiGHS) with battery dynamics, SOC and power limits, and a binary variable preventing simultaneous charging and discharging.
  - Standard: minimize grid cost `sum((day-ahead + const_price_dyn) * p_grid)`.
  - Trading: minimize `cost of charging - revenue from discharging`, with the service fee split evenly between both.
- **Battery simulation:** The 1 s simulation follows the schedule. In the standard simulation, discharging only covers the measured household load; in the trading simulation, discharging follows the schedule regardless of the load.
- **Evaluation:** `inspect_results.py` splits the trading discharge into self-consumption and sales and computes the costs of all variants, the daily savings versus the static tariff, and plots the results.

## Output

`data/results/battery_simulation_results_Pl_<profile number>.csv` (e.g. `..._Pl_43.csv`) with the columns:

`timestamp`, `dynamic_price_ct_kWh`, `load_power_W`, `aux_power_W`, `battery_dc_power_W`, `battery_ac_power_W`, `soc`,
`battery_dc_power_trading_W`, `battery_ac_power_trading_W`, `soc_trading`

Battery power is positive when charging and negative when discharging.

> **Note:** The column `load_power_W` contains the selected HTW Berlin load profile.

## Results

Costs for one year with the current default settings (profile `Pl_43`).

| Variant | Cost (EUR) | Savings vs. static (EUR) |
|---------|-----------:|-------------------------:|
| Static tariff (no battery) | 861.87 | – |
| Dynamic tariff (no battery) | 859.59 | 2.28 |
| Dynamic tariff with battery | 802.38 | 59.49 |
| Dynamic tariff with battery and trading | 784.26 | 77.61 |

## Notes

- `functions/fn_day_ahead_data.py` ignores the timestamps of the Energy-Charts files and generates a continuous 15 min index starting on January 1st of the year detected automatically from the first price file (first `Datum` value, fallback: file name). The files must therefore be complete and in chronological order.
- The load profile is mapped onto the same year, so price and load data are aligned by position, not by their original dates.
- In the default configuration, the months October to December are taken from the 2025 price files.

## License and attribution

- **Code:** See the [LICENSE](LICENSE) file.
- **Household load profiles:** HTW Berlin, licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), source: [HTW Berlin](https://solar.htw-berlin.de/elektrische-lastprofile-fuer-wohngebaeude/).
- **Day-ahead prices:** Bundesnetzagentur | SMARD.de, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
  provided by [Energy-Charts.info](https://www.energy-charts.info).
