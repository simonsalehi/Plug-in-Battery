import numpy as np
import cvxpy as cp


def charging_schedule_trading(
        const_price_dyn,      # ct/kWh
        service_fee,          # ct/kWh
        day_ahead_data_day,
        var_e_bat,            # Wh
        var_p_bat_c,          # W
        var_p_bat_d,          # W
        var_soc0,             # 0-1
        var_eta_c,
        var_eta_d,
        var_eta_bat
):
    """
    Takes the day-ahead price and returns an optimal battery
    charging/discharging schedule for trading (mixed-integer linear program).
    """

    # ---------------------------
    # FORECASTS
    # ---------------------------

    df_price = day_ahead_data_day

    price_c = (df_price["price ct/kWh"].values + (service_fee / 2)) / 1000 / 100  # EUR/Wh
    price_d = (df_price["price ct/kWh"].values - service_fee / 2) / 1000 / 100  # EUR/Wh

    # ---------------------------
    # PARAMETERS
    # ---------------------------

    n_timesteps = len(df_price)

    dt = 0.25  # hours

    # var_eta_bat is applied as sqrt() symmetrically on charging and discharging,
    # matching the physics used in fn_battery_simulation_trading.py
    sqrt_eta_bat = np.sqrt(var_eta_bat)

    # ---------------------------
    # DECISION VARIABLES
    # ---------------------------

    p_charge = cp.Variable(n_timesteps, nonneg=True)
    p_discharge = cp.Variable(n_timesteps, nonneg=True)

    # Binary variable: u = 1 -> charging, u = 0 -> discharging
    u = cp.Variable(n_timesteps, boolean=True)

    e_bat = cp.Variable(n_timesteps + 1)

    # ---------------------------
    # CONSTRAINTS
    # ---------------------------

    constraints = []

    # Initial battery energy
    constraints += [
        e_bat[0] == var_soc0 * var_e_bat
    ]

    for t in range(n_timesteps):

        # Battery dynamics
        constraints += [
            e_bat[t + 1]
            == e_bat[t]
            + var_eta_c * sqrt_eta_bat * p_charge[t] * dt
            - (1 / var_eta_d) / sqrt_eta_bat * p_discharge[t] * dt
        ]

        # Battery limits
        constraints += [
            e_bat[t + 1] >= 0,
            e_bat[t + 1] <= var_e_bat,
        ]

        # Prevent simultaneous charging/discharging
        constraints += [
            p_charge[t] <= var_p_bat_c * u[t],
            p_discharge[t] <= var_p_bat_d * (1 - u[t]),
        ]

    # ---------------------------
    # OBJECTIVE
    # ---------------------------

    cost = cp.sum(cp.multiply(price_c, p_charge) * dt)
    revenue = cp.sum(cp.multiply(price_d, p_discharge) * dt)

    objective = cp.Minimize(cost - revenue)

    # ---------------------------
    # SOLVE
    # ---------------------------

    problem = cp.Problem(objective, constraints)

    # Requires: pip install highspy
    problem.solve(solver=cp.HIGHS)

    # ---------------------------
    # RESULTS
    # ---------------------------

    def clean(x, tol=10):
        x = np.asarray(x).copy()
        x[np.abs(x) < tol] = 0.0
        return x

    p_charge = clean(p_charge.value)
    p_discharge = clean(p_discharge.value)

    return p_charge, p_discharge
