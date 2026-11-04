"""Derivatives book: Greeks, scenario grid and historical P&L.

Every figure is checked against something the module does not compute the
same way: central finite differences of the book's revalued value, put-call
parity in closed form, the cubic error order of a second-order Taylor
expansion, and the payoff of an option that settles inside the horizon.
"""
import copy
import json
import math
import runpy
from pathlib import Path

import pytest

from riskdesk.analytics import tail_risk
from riskdesk.derivatives import book_greeks, historical_pnl, scenario_grid

pytestmark = pytest.mark.unit

BASE = dict(as_of="2026-11-04", currency="USD", source="unit test", data_mode="synthetic")


def option(id, underlying, kind, strike, qty, t, vol, rate=0.04, carry=None, mult=100.0):
    p = dict(id=id, underlying=underlying, instrument_type="option", quantity=qty, multiplier=mult,
             kind=kind, strike=strike, year_fraction=t, implied_vol=vol, rate=rate)
    if carry is not None:
        p["carry_yield"] = carry
    return p


def linear(id, underlying, qty, mult=1.0):
    return dict(id=id, underlying=underlying, instrument_type="linear", quantity=qty, multiplier=mult)


def mixed_book():
    return dict(BASE, underlyings={"IDX": dict(price=100.0, price_type="spot"),
                                   "CL": dict(price=80.0, price_type="future")},
                positions=[option("c1", "IDX", "call", 105.0, 10, 0.5, 0.22, carry=0.015),
                           option("p1", "IDX", "put", 95.0, -5, 0.25, 0.27, carry=0.015),
                           linear("s1", "IDX", 200),
                           option("c2", "CL", "call", 85.0, 3, 0.75, 0.35, mult=1000.0),
                           option("p2", "CL", "put", 75.0, -2, 0.4, 0.38, mult=1000.0),
                           linear("f1", "CL", -4, mult=1000.0)])


def book_value(book):
    """Option model value plus linear notional per underlying: the quantity
    whose derivatives the Greeks claim to be."""
    rows = book_greeks(book)["by_underlying"]
    return {u: r["option_model_value"] + r["linear_notional"] for u, r in rows.items()}


def bumped(book, **change):
    out = copy.deepcopy(book)
    for name, fn in change.items():
        if name == "price":
            for u, f in fn.items():
                out["underlyings"][u]["price"] = f(out["underlyings"][u]["price"])
        else:
            for p in out["positions"]:
                if p["instrument_type"] == "option":
                    p[name] = fn(p[name])
    return out


def test_book_greeks_match_finite_differences_of_the_revalued_book():
    book = mixed_book()
    rows = book_greeks(book)["by_underlying"]
    for u in ("IDX", "CL"):
        S, e = book["underlyings"][u]["price"], 1e-3
        up = book_value(bumped(book, price={u: lambda s: s + e}))[u]
        mid = book_value(book)[u]
        dn = book_value(bumped(book, price={u: lambda s: s - e}))[u]
        assert rows[u]["cash_delta"] == pytest.approx((up - dn) / (2 * e) * S, rel=1e-7)
        assert rows[u]["cash_gamma_1pct"] == pytest.approx((up - 2 * mid + dn) / e**2 * S * S / 100, rel=1e-4)
    for field, key, h, scale in (("implied_vol", "vega_per_vol_point", 1e-5, 1 / 100),
                                 ("rate", "rho_per_rate_point", 1e-6, 1 / 100),
                                 ("year_fraction", "theta_per_day", 1e-6, -1 / 365)):
        up = book_value(bumped(book, **{field: lambda x: x + h}))
        dn = book_value(bumped(book, **{field: lambda x: x - h}))
        for u in ("IDX", "CL"):
            assert rows[u][key] == pytest.approx((up[u] - dn[u]) / (2 * h) * scale, rel=1e-6), (u, key)


def test_put_call_parity_book_matches_closed_form_for_spot_and_future():
    """Long call, short put, same strike: value, delta and rho in closed form,
    gamma and vega zero. Black-76 rho here is -t(F-K)e^{-rt}; an engine
    build before optiondesk-engine 4a282d9 gave K t e^{-rt} and fails this test."""
    S, F, K, t, r, q, n, m = 100.0, 80.0, 90.0, 0.6, 0.05, 0.02, 7, 50.0
    book = dict(BASE, underlyings={"S": dict(price=S, price_type="spot"), "F": dict(price=F, price_type="future")},
                positions=[option("sc", "S", "call", K, n, t, 0.3, r, q, m), option("sp", "S", "put", K, -n, t, 0.3, r, q, m),
                           option("fc", "F", "call", K, n, t, 0.3, r, mult=m), option("fp", "F", "put", K, -n, t, 0.3, r, mult=m)])
    rows = book_greeks(book)["by_underlying"]
    spot_value = n * m * (S * math.exp(-q * t) - K * math.exp(-r * t))
    fut_value = n * m * math.exp(-r * t) * (F - K)
    assert rows["S"]["option_model_value"] == pytest.approx(spot_value, rel=1e-12)
    assert rows["S"]["cash_delta"] == pytest.approx(n * m * S * math.exp(-q * t), rel=1e-12)
    assert rows["S"]["rho_per_rate_point"] == pytest.approx(n * m * K * t * math.exp(-r * t) / 100, rel=1e-12)
    assert rows["F"]["option_model_value"] == pytest.approx(fut_value, rel=1e-12)
    assert rows["F"]["cash_delta"] == pytest.approx(n * m * F * math.exp(-r * t), rel=1e-12)
    assert rows["F"]["rho_per_rate_point"] == pytest.approx(-t * fut_value / 100, rel=1e-12)
    for u in ("S", "F"):
        assert abs(rows[u]["cash_gamma_1pct"]) < 1e-9 and abs(rows[u]["vega_per_vol_point"]) < 1e-9


def test_totals_add_the_underlyings_and_envelope_keeps_provenance():
    result = book_greeks(mixed_book())
    for key in ("cash_delta", "vega_per_vol_point", "theta_per_day", "rho_per_rate_point"):
        assert result["total"][key] == pytest.approx(sum(r[key] for r in result["by_underlying"].values()))
    assert (result["currency"], result["as_of"], result["data_mode"]) == ("USD", "2026-11-04", "synthetic")
    assert result["degraded"] is False and len(result["input_sha256"]) == 64
    assert set(result["units"]) == {"cash_delta", "cash_gamma_1pct", "vega_per_vol_point", "theta_per_day", "rho_per_rate_point"}


def test_expiry_date_is_converted_act_365():
    book = mixed_book()
    dated = copy.deepcopy(book)
    del dated["positions"][0]["year_fraction"]
    dated["positions"][0]["expiry"] = "2027-05-05"  # 182 days after as_of
    book["positions"][0]["year_fraction"] = 182 / 365
    assert book_greeks(dated)["by_underlying"] == book_greeks(book)["by_underlying"]


def test_grid_parity_book_is_exact_under_every_spot_and_vol_shock():
    S, K, t, r, q = 100.0, 100.0, 0.5, 0.03, 0.01
    book = dict(BASE, underlyings={"S": dict(price=S, price_type="spot")},
                positions=[option("c", "S", "call", K, 1, t, 0.25, r, q), option("p", "S", "put", K, -1, t, 0.25, r, q)],
                spot_shocks=[-0.3, -0.05, 0.0, 0.1], vol_shocks=[-0.1, 0.0, 0.2])
    for cell in scenario_grid(book)["cells"]:
        exact = 100 * S * cell["spot_shock"] * math.exp(-q * t)
        assert cell["full_pnl"] == pytest.approx(exact, rel=1e-10, abs=1e-8)
        assert abs(cell["delta_gamma_error"]) < 1e-7 and abs(cell["delta_gamma_vega_error"]) < 1e-7


def test_grid_linear_book_approximations_are_exact_and_zero_cell_is_zero():
    book = dict(BASE, underlyings={"A": dict(price=50.0, price_type="spot")},
                positions=[linear("a", "A", 3, 10.0)], spot_shocks=[-0.2, 0.0, 0.15], vol_shocks=[0.0, 0.05])
    for cell in scenario_grid(book)["cells"]:
        assert cell["full_pnl"] == pytest.approx(30 * 50.0 * cell["spot_shock"])
        assert abs(cell["delta_gamma_error"]) < 1e-9 and abs(cell["delta_gamma_vega_error"]) < 1e-9
    zero = [c for c in scenario_grid(mixed_book() | dict(spot_shocks=[0.0], vol_shocks=[0.0]))["cells"]]
    assert zero[0]["full_pnl"] == 0.0 and zero[0]["delta_gamma_pnl"] == 0.0


def test_delta_gamma_error_is_third_order_in_the_spot_move():
    book = dict(BASE, underlyings={"S": dict(price=100.0, price_type="spot")},
                positions=[option("c", "S", "call", 100.0, 1, 0.5, 0.2, 0.03, 0.0)],
                spot_shocks=[0.005, 0.01], vol_shocks=[0.0])
    small, large = (c["delta_gamma_error"] for c in scenario_grid(book)["cells"])
    assert 7.0 < large / small < 9.0  # 2^3 for a cubic leading term


def test_vega_term_absorbs_a_pure_vol_shock():
    book = dict(BASE, underlyings={"S": dict(price=100.0, price_type="spot")},
                positions=[option("c", "S", "call", 100.0, 1, 0.5, 0.2, 0.03, 0.0),
                           option("p", "S", "put", 100.0, 1, 0.5, 0.2, 0.03, 0.0)],
                spot_shocks=[0.0], vol_shocks=[0.01])
    cell = scenario_grid(book)["cells"][0]
    assert abs(cell["delta_gamma_vega_error"]) < 0.01 * abs(cell["delta_gamma_error"])


def test_historical_fixed_time_parity_book_matches_closed_form_and_feeds_tail_risk():
    S, F, K, t, r, q = 100.0, 60.0, 95.0, 0.5, 0.03, 0.01
    returns = [-0.2, -0.07, -0.01, 0.0, 0.03, 0.12]
    book = dict(BASE, underlyings={"S": dict(price=S, price_type="spot"), "F": dict(price=F, price_type="future")},
                positions=[option("c", "S", "call", K, 2, t, 0.25, r, q), option("p", "S", "put", K, -2, t, 0.25, r, q),
                           linear("f", "F", -5, 10.0)],
                scenarios=[dict(spot_returns={"S": x, "F": -x}, vol_changes={"S": 0.1, "F": 0.0}) for x in returns],
                horizon_days=10, time_mode="fixed", confidence=0.9, portfolio_value=1e6)
    result = historical_pnl(book)
    for x, pnl in zip(returns, result["pnl"]):
        assert pnl == pytest.approx(200 * S * x * math.exp(-q * t) + 50 * F * x, rel=1e-10, abs=1e-8)
    direct = tail_risk(dict(BASE, pnl=result["pnl"], confidence=0.9, horizon_days=10, portfolio_value=1e6))
    assert (result["tail"]["var"], result["tail"]["expected_shortfall"]) == (direct["var"], direct["expected_shortfall"])
    assert result["degraded"] is True and "Fewer than 20" in result["degraded_reason"]


def test_historical_decay_mode_charges_theta_and_settles_expiring_options():
    book = mixed_book() | dict(scenarios=[dict(spot_returns={"IDX": 0.0, "CL": 0.0})] * 2,
                               horizon_days=1, time_mode="decay", confidence=0.5, portfolio_value=1e6)
    later = book_value(bumped(mixed_book(), year_fraction=lambda t: t - 1 / 365))
    assert historical_pnl(book)["pnl"][0] == pytest.approx(
        sum(later.values()) - sum(book_value(mixed_book()).values()), abs=1e-8)
    assert historical_pnl(book | dict(time_mode="fixed"))["pnl"] == [0.0, 0.0]

    short = dict(BASE, underlyings={"S": dict(price=100.0, price_type="spot")},
                 positions=[option("c", "S", "call", 100.0, 1, 5 / 365, 0.2, 0.0, 0.0)],
                 scenarios=[dict(spot_returns={"S": x}) for x in (-0.1, 0.08)],
                 horizon_days=10, time_mode="decay", confidence=0.5, portfolio_value=1e6)
    premium = book_greeks({k: short[k] for k in (*BASE, "underlyings", "positions")})["total"]["option_model_value"]
    result = historical_pnl(short)
    assert result["pnl"] == pytest.approx([-premium, 100 * 8.0 - premium], rel=1e-12)
    assert result["options_settled_within_horizon"] == ["c"]


BAD = [
    ("option without strike", lambda b: b["positions"][0].pop("strike"), "needs kind, strike"),
    ("both expiry forms", lambda b: b["positions"][0].update(expiry="2027-01-01"), "exactly one of expiry"),
    ("carry on a future", lambda b: b["positions"][3].update(carry_yield=0.0), "takes no carry_yield"),
    ("missing carry on spot", lambda b: b["positions"][0].pop("carry_yield"), "needs carry_yield"),
    ("unknown underlying", lambda b: b["positions"][2].update(underlying="X"), "unknown underlying"),
    ("option terms on linear", lambda b: b["positions"][2].update(strike=1.0), "must not carry option terms"),
    ("duplicate id", lambda b: b["positions"][1].update(id="c1"), "unique"),
    ("missing multiplier", lambda b: b["positions"][2].pop("multiplier"), "multiplier"),
    ("vol in percent", lambda b: b["positions"][0].update(implied_vol=22.0), "plausibility ceiling"),
    ("expired", lambda b: (b["positions"][0].pop("year_fraction"), b["positions"][0].update(expiry="2026-11-04")), "expires on or before"),
]


@pytest.mark.parametrize("name,change,message", BAD, ids=[b[0] for b in BAD])
def test_invalid_books_are_refused_with_a_plain_message(name, change, message):
    book = mixed_book()
    change(book)
    with pytest.raises(ValueError, match=message):
        book_greeks(book)


def test_invalid_shocks_and_scenarios_are_refused():
    with pytest.raises(ValueError, match="non-positive volatility"):
        scenario_grid(mixed_book() | dict(spot_shocks=[0.0], vol_shocks=[-0.3]))
    with pytest.raises(ValueError, match="above -100%"):
        scenario_grid(mixed_book() | dict(spot_shocks=[-1.0], vol_shocks=[0.0]))
    hist = mixed_book() | dict(horizon_days=1, time_mode="fixed", confidence=0.9, portfolio_value=1.0)
    with pytest.raises(ValueError, match="exactly the book underlyings"):
        historical_pnl(hist | dict(scenarios=[dict(spot_returns={"IDX": 0.0})] * 2))
    with pytest.raises(ValueError, match="time_mode"):
        historical_pnl(hist | dict(time_mode="sometimes", scenarios=[dict(spot_returns={"IDX": 0.0, "CL": 0.0})] * 2))
    with pytest.raises(ValueError, match="revaluations"):
        scenario_grid(mixed_book() | dict(spot_shocks=[0.0] * 101, vol_shocks=[0.0] * 101,
                                          positions=[option(f"o{i}", "IDX", "call", 100.0, 1, 0.5, 0.2, carry=0.0)
                                                     for i in range(200)]))


EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.mark.parametrize("name,handler", [("derivatives_book.json", book_greeks),
                                          ("derivatives_grid.json", scenario_grid),
                                          ("derivatives_historical.json", historical_pnl)])
def test_the_synthetic_examples_run_and_are_not_degraded(name, handler):
    result = handler(json.loads((EXAMPLES / name).read_text(encoding="utf-8")))
    assert (result["data_mode"], result["currency"], result["degraded"]) == ("synthetic", "USD", False)


def test_the_skill_checker_passes_real_results_and_catches_tampering():
    path = Path(__file__).resolve().parent.parent / "plugins/risk-desk/skills/risk-derivatives/scripts/check_artifact.py"
    problems = runpy.run_path(str(path))["problems"]  # run_path writes no __pycache__ into the skill
    results = [handler(json.loads((EXAMPLES / name).read_text(encoding="utf-8"))) for name, handler in
               (("derivatives_book.json", book_greeks), ("derivatives_grid.json", scenario_grid),
                ("derivatives_historical.json", historical_pnl))]
    assert [problems(r) for r in results] == [[], [], []]
    results[0]["total"]["cash_delta"] += 1.0
    results[1]["cells"][3]["delta_gamma_error"] += 1.0
    results[2]["pnl"].pop()
    assert all(problems(r) for r in results)
