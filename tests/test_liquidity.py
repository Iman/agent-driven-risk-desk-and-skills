"""Days to liquidate, the schedule and the Bangia et al. (1999) spread add-on, against hand
calculations and a brute-force day-by-day liquidation."""
import importlib.util
import json
import random
from pathlib import Path

import pytest
from pydantic import ValidationError

from riskdesk.liquidity import liquidity_risk

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parent.parent


def book(**extra):
    payload = dict(as_of="2026-09-12", currency="USD", source="synthetic test", data_mode="synthetic", nav=1000,
                   positions=[dict(id="long", asset="A", market_value=600, instrument_type="linear"),
                              dict(id="short", asset="B", market_value=-200, instrument_type="linear")],
                   participation_rate=.2, spread_multiplier=3,
                   liquidity=dict(A=dict(average_daily_value=1000, mean_relative_spread=.002, spread_volatility=.001),
                                  B=dict(average_daily_value=400, mean_relative_spread=.01, spread_volatility=.004)))
    payload.update(extra)
    return payload


def test_days_schedule_and_cost_match_hand_calculation():
    result = liquidity_risk(book())
    a, b = result["by_asset"]["A"], result["by_asset"]["B"]
    assert a["daily_capacity"] == pytest.approx(200) and a["days_to_liquidate"] == pytest.approx(3)
    assert b["daily_capacity"] == pytest.approx(80) and b["days_to_liquidate"] == pytest.approx(2.5)
    # Day d holds max(0, 600 - 200d) + max(0, 200 - 80d).
    assert [row["held_value"] for row in result["schedule"]] == pytest.approx([800, 520, 240, 0])
    assert [row["assets_held"] for row in result["schedule"]] == [2, 2, 2, 0]
    assert result["schedule"][1]["held_fraction"] == pytest.approx(.65)
    # BDSS (1999) eq. (4), COL = 1/2 P (S + a sigma), per unit of mid value, times the position:
    # A: 0.5 x 600 x (0.002 + 3 x 0.001) = 1.5; B (short, absolute value): 0.5 x 200 x (0.01 + 3 x 0.004) = 2.2.
    assert a["cost_of_liquidity"] == pytest.approx(1.5)
    assert b["cost_of_liquidity"] == pytest.approx(2.2)
    assert result["cost_of_liquidity"] == pytest.approx(3.7)
    assert result["liquidity_adjusted_var"] is None
    assert result["degraded"] is False


def test_liquidity_adjusted_var_adds_the_spread_cost_to_historical_var():
    result = liquidity_risk(book(pnl=[-100, -50, 0, 50], confidence=.625, horizon_days=1))
    assert result["var"] == pytest.approx(50)                    # hand-checked in tests/test_risk.py
    assert result["liquidity_adjusted_var"] == pytest.approx(53.7)
    assert result["horizon_days"] == 1
    assert "A, B take longer to liquidate than the 1 day VaR horizon" in result["degraded_reason"]
    assert "tail: Fewer than 20 observations" in result["degraded_reason"]
    assert any("No horizon scaling" in a for a in result["assumptions"])


def test_positions_in_one_asset_share_its_volume():
    positions = [dict(id="l", asset="A", market_value=600, instrument_type="linear"),
                 dict(id="s", asset="A", market_value=-100, instrument_type="linear")]
    result = liquidity_risk(book(positions=positions, liquidity={"A": book()["liquidity"]["A"]}))
    assert result["by_asset"]["A"]["gross_value"] == pytest.approx(700)
    assert result["max_days_to_liquidate"] == pytest.approx(3.5)


def test_schedule_matches_brute_force_day_by_day_selling():
    rng = random.Random(7)
    positions, liquidity = [], {}
    for i in range(12):
        asset = "X{}".format(i)
        positions.append(dict(id=asset, asset=asset, market_value=rng.uniform(-5e6, 5e6), instrument_type="linear"))
        liquidity[asset] = dict(average_daily_value=rng.uniform(1e5, 5e6), mean_relative_spread=0,
                                spread_volatility=0)
    rate = .1
    result = liquidity_risk(book(positions=positions, liquidity=liquidity, participation_rate=rate))
    remaining = {p["asset"]: abs(p["market_value"]) for p in positions}
    for row in result["schedule"]:
        assert row["held_value"] == pytest.approx(sum(remaining.values()), rel=1e-12, abs=1e-6)
        for asset in remaining:
            remaining[asset] -= min(remaining[asset], rate*liquidity[asset]["average_daily_value"])
    assert result["schedule"][-1]["held_value"] == 0
    assert result["schedule"][-2]["held_value"] > 0


@pytest.mark.parametrize("change", [
    {"participation_rate": 0}, {"participation_rate": 1.5}, {"spread_multiplier": -1},
    {"liquidity": {"A": book()["liquidity"]["A"]}},
    {"pnl": [1, 2]},
    {"liquidity": dict(book()["liquidity"], B=dict(average_daily_value=0, mean_relative_spread=0,
                                                   spread_volatility=0))},
    {"liquidity": dict(book()["liquidity"], B=dict(average_daily_value=1, mean_relative_spread=-.1,
                                                   spread_volatility=0))},
])
def test_invalid_liquidity_inputs_are_refused(change):
    with pytest.raises(ValidationError):
        liquidity_risk(book(**change))


def test_implausible_liquidation_time_is_refused_as_a_unit_error():
    liquidity = dict(book()["liquidity"], A=dict(average_daily_value=.001, mean_relative_spread=0,
                                                 spread_volatility=0))
    with pytest.raises(ValueError, match="check the units"):
        liquidity_risk(book(liquidity=liquidity))


def checker():
    spec = importlib.util.spec_from_file_location(
        "risk_liquidity_check", ROOT / "plugins/risk-desk/skills/risk-liquidity/scripts/check_artifact.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_artifact_checker_passes_real_results_and_catches_tampering():
    check = checker().check
    result = liquidity_risk(book(pnl=[-100, -50, 0, 50], confidence=.625, horizon_days=1))
    assert check(result) == []
    result["liquidity_adjusted_var"] += 1
    assert any("not VaR + cost" in p for p in check(result))


def test_example_parses_and_passes_the_checker():
    example = json.loads((ROOT / "examples" / "liquidity_book.json").read_text(encoding="utf-8"))
    result = liquidity_risk(example)
    assert result["currency"] == "USD" and result["data_mode"] == "synthetic"
    assert checker().check(result) == []
