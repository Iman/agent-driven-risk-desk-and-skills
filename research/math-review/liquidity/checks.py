"""Independent checks of riskdesk.liquidity.liquidity_risk: days to liquidate, the Bangia et al.
exogenous cost of liquidity, the schedule, and L-VaR as VaR plus total cost. The additive
L-VaR form rests on a secondary source (reference.md:57-69); this check confirms only that the
module computes that form, not that the form is the paper's.
"""
from fractions import Fraction
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _review import Review  # noqa: E402
from riskdesk.liquidity import liquidity_risk  # noqa: E402  (called for comparison only)

META = dict(as_of="2026-11-04", currency="USD", source="independent math review", data_mode="synthetic")
REF = "plugins/risk-desk/skills/risk-liquidity/reference.md"


def main():
    r = Review("liquidity", "Liquidation horizon, spread cost and L-VaR: independent numerical review", __file__)
    positions = [dict(id="a1", asset="A", market_value=5_000_000.0, instrument_type="linear"),
                 dict(id="a2", asset="A", market_value=-1_000_000.0, instrument_type="linear"),
                 dict(id="b1", asset="B", market_value=2_000_000.0, instrument_type="linear")]
    liq = dict(A=dict(average_daily_value=4_000_000.0, mean_relative_spread=0.002, spread_volatility=0.0005),
               B=dict(average_daily_value=500_000.0, mean_relative_spread=0.01, spread_volatility=0.004))
    rate, mult = 0.25, 3.0
    pnl = (np.random.default_rng(7).standard_normal(500) * 50_000).tolist()
    out = liquidity_risk(dict(META, nav=6_000_000.0, positions=positions, participation_rate=rate,
                              spread_multiplier=mult, liquidity=liq, pnl=pnl, confidence=0.99, horizon_days=10))
    gross = dict(A=6_000_000.0, B=2_000_000.0)  # absolute values summed per asset (REF:21-22)
    days = {a: gross[a] / (rate * liq[a]["average_daily_value"]) for a in gross}
    cost = {a: 0.5 * gross[a] * (liq[a]["mean_relative_spread"] + mult * liq[a]["spread_volatility"]) for a in gross}
    for a in gross:
        r.close(f"days-{a}", f"days to liquidate {a} = V / (q ADV)", f"{REF}:16", days[a],
                out["by_asset"][a]["days_to_liquidate"], rel_tol=1e-12)
        r.close(f"col-{a}", f"cost of liquidity {a} = V (S + a sigma) / 2", f"Bangia et al. eq. (4), {REF}:37-45",
                cost[a], out["by_asset"][a]["cost_of_liquidity"], rel_tol=1e-12)
    held = [sum(max(0.0, gross[a] - rate * liq[a]["average_daily_value"] * d) for a in gross)
            for d in range(math.ceil(max(days.values())) + 1)]
    r.equal("schedule", "end-of-day held value, day by day", f"{REF}:17-19", held,
            [row["held_value"] for row in out["schedule"]])
    losses = sorted((-x for x in pnl), reverse=True)
    var = losses[math.ceil(len(losses) * (1 - Fraction("0.99"))) - 1]
    r.close("lvar-additive", "L-VaR = historical VaR + total cost (form from a secondary source)",
            f"{REF}:57-69", var + sum(cost.values()), out["liquidity_adjusted_var"], rel_tol=1e-12)
    return r.write()


if __name__ == "__main__":
    main()
