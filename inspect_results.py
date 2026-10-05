import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from edit_simulation_parameters import simulation_parameters

W_TO_KWH = 1 / 1000 / 3600  # W * 1 s -> kWh
RED, RESET = "\033[31m", "\033[0m"


def energy_kwh(power_w):
    """Sum of a 1 s power series [W] -> energy [kWh]."""
    return np.sum(power_w) * W_TO_KWH


def cost_eur(price_ct_kwh, power_w):
    """Cost [EUR] of a 1 s power series [W] at a price [ct/kWh] (scalar or series)."""
    return np.sum(price_ct_kwh * power_w) * W_TO_KWH / 100


# -------------------------------
# Load parameters and results
# -------------------------------
par = simulation_parameters()

df = pd.read_csv(f"data/results/battery_simulation_results_Pl_{par.htw_profile_number}.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

n_months = len(par.path_price_files)
n_days = df["timestamp"].dt.floor("D").nunique()

price_dyn = df["dynamic_price_ct_kWh"].values        # ct/kWh (day-ahead, without const. price)
price_dyn_total = price_dyn + par.const_price_dyn    # ct/kWh (incl. const. price)
p_load = df["load_power_W"].values                   # W
p_aux = df["aux_power_W"].values                     # W
p_load_total = p_load + p_aux                        # W (load + peripherals)

base_stat = par.base_price_stat * n_months / 100     # EUR (total base price)
base_dyn = par.base_price_dyn * n_months / 100       # EUR (total base price)

# -------------------------------
# Cost: static tariff, dynamic tariff, dynamic tariff + battery
# -------------------------------
p_bat = df["battery_ac_power_W"].values              # W (+ charging / - discharging)
p_grid_battery = np.maximum(p_load_total + p_bat, 0)  # W

cost_stat = cost_eur(par.const_price_stat, p_load) + base_stat
cost_dyn = cost_eur(price_dyn_total, p_load) + base_dyn
cost_dyn_battery = cost_eur(price_dyn_total, p_grid_battery) + base_dyn

energy_charged_kWh = energy_kwh(np.maximum(p_bat, 0))
energy_discharged_kWh = energy_kwh(-np.minimum(p_bat, 0))
average_charging_power_W = np.mean(p_bat[p_bat > 0])
average_discharging_power_W = -np.mean(p_bat[p_bat < 0])

print(f"{RED}Cost static tariff: {cost_stat:.2f} EUR{RESET}")
print(f"{RED}Cost dynamic tariff: {cost_dyn:.2f} EUR{RESET}")
print("Results without trading:")
print(f"{RED}Cost dynamic tariff with battery: {cost_dyn_battery:.2f} EUR{RESET}")
print(f"Energy charged: {energy_charged_kWh:.2f} kWh")
print(f"Energy discharged: {energy_discharged_kWh:.2f} kWh")
print(f"Average charging power: {average_charging_power_W:.2f} W")
print(f"Average discharging power: {average_discharging_power_W:.2f} W")

# -------------------------------
# Cost trading
# -------------------------------
# Price per kWh:
#   load + aux from grid ............ dyn + const
#   load + aux from battery ......... const - 0.5 * service fee   (self-consumption)
#   battery losses .................. 0.5 * service fee
#   battery charging ................ dyn + 0.5 * service fee
#   battery discharging (trading) ... dyn - 0.5 * service fee     (revenue)
half_fee = par.service_fee / 2

p_bat_t = df["battery_ac_power_trading_W"].values     # W (+ charging / - discharging)
p_charge_t = np.maximum(p_bat_t, 0)                   # charging from grid
p_discharge_t = np.maximum(-p_bat_t, 0)               # discharging
p_self_t = np.minimum(p_discharge_t, np.maximum(p_load_total, 0))  # discharge covering the load
p_export_t = p_discharge_t - p_self_t                 # discharge sold to grid
p_grid_load_t = np.maximum(p_load_total, 0) - p_self_t  # load covered by grid

e_charged_t = energy_kwh(p_charge_t)
e_discharged_t = energy_kwh(p_discharge_t)
e_self_t = energy_kwh(p_self_t)
e_export_t = energy_kwh(p_export_t)
e_losses_t = e_charged_t - e_discharged_t

cost_load_grid_t = cost_eur(price_dyn_total, p_grid_load_t)
cost_load_battery_t = e_self_t * (par.const_price_dyn - half_fee) / 100
cost_losses_t = e_losses_t * half_fee / 100
cost_charging_t = cost_eur(price_dyn + half_fee, p_charge_t)
revenue_t = cost_eur(price_dyn - half_fee, p_export_t)

cost_dyn_battery_trading = (
    cost_load_grid_t
    + cost_load_battery_t
    + cost_losses_t
    + cost_charging_t
    + base_dyn
    - revenue_t
)

average_charging_power_trading_W = np.mean(p_bat_t[p_bat_t > 0])
average_discharging_power_trading_W = -np.mean(p_bat_t[p_bat_t < 0])

print("Results with trading:")
print(f"Revenue dynamic tariff with battery and trading: {revenue_t:.2f} EUR")
print(f"{RED}Cost dynamic tariff with battery and trading: {cost_dyn_battery_trading:.2f} EUR{RESET}")
print(f"Energy charged with trading: {e_charged_t:.2f} kWh")
print(f"Energy discharged with trading: {e_discharged_t:.2f} kWh")
print(f"  of which self-consumption: {e_self_t:.2f} kWh")
print(f"  of which sold (trading): {e_export_t:.2f} kWh")
print(f"Average charging power: {average_charging_power_trading_W:.2f} W")
print(f"Average discharging power: {average_discharging_power_trading_W:.2f} W")

# -------------------------------
# Daily costs and savings (static tariff vs. dynamic tariff + battery)
# -------------------------------
df["cost_static"] = par.const_price_stat * p_load * W_TO_KWH / 100
df["cost_dyn_battery"] = price_dyn_total * p_grid_battery * W_TO_KWH / 100

daily = df.groupby(df["timestamp"].dt.floor("D"))[["cost_static", "cost_dyn_battery"]].sum()
daily["cost_static"] += base_stat / n_days
daily["cost_dyn_battery"] += base_dyn / n_days
daily["savings"] = daily["cost_static"] - daily["cost_dyn_battery"]
daily["cum_savings"] = daily["savings"].cumsum()

# -------------------------------
# Plots
# -------------------------------
sns.set_style("whitegrid")
fig, axs = plt.subplots(4, 1, figsize=(15, 12), sharex=True)

# 1. Price
axs[0].plot(df["timestamp"], price_dyn_total, color="tab:red")
axs[0].set_ylabel("Price [ct/kWh]")
axs[0].set_title("Dynamic electricity price")

# 2. Battery power
axs[1].plot(df["timestamp"], p_bat, color="tab:orange", label="Battery AC power")
axs[1].plot(df["timestamp"], p_load_total, color="tab:blue", alpha=0.3, label="Household load")
axs[1].set_ylabel("Power [W]")
axs[1].set_title("Battery charging/discharging (simulation without trading)")
axs[1].set_ylim(-1000, 1800)
axs[1].legend(loc="upper right")

# 3. State of charge
axs[2].plot(df["timestamp"], df["soc"] * 100, color="tab:green")
axs[2].set_ylabel("SOC [%]")
axs[2].set_title("Battery SOC (simulation without trading)")

# 4. Daily savings
colors = np.where(daily["savings"] >= 0, "tab:green", "tab:red")
axs[3].bar(daily.index, daily["savings"], color=colors, width=0.8, alpha=0.8, label="Daily savings")
axs[3].plot(daily.index, daily["cum_savings"], color="tab:blue", linewidth=2, label="Cumulative savings")
axs[3].axhline(0, color="black", linewidth=0.8)
axs[3].set_ylabel("Savings [EUR]")
axs[3].set_xlabel("Date")
axs[3].set_title("Savings compared to static tariff (simulation without trading)")
axs[3].legend(loc="upper left")

plt.tight_layout()
plt.show()
