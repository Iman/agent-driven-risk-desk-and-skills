"""The shipped example files are inputs the documentation points at.

A README that says "run this on examples/energy_book.json" is a promise
about a file, so the file is checked here: it parses under the real
contract, it produces a result, and its degraded status is the one the
documentation describes rather than whatever it happens to be today.
"""
import json
from pathlib import Path

import pytest

from riskdesk.analytics import portfolio_exposure, stress_test, tail_risk
from riskdesk.summaries import summarise

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

pytestmark = pytest.mark.unit


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name,handler", [
    ("tail.json", tail_risk),
    ("energy_tail.json", tail_risk),
    ("portfolio.json", portfolio_exposure),
    ("energy_book.json", portfolio_exposure),
    ("stress.json", stress_test),
    ("energy_stress.json", stress_test),
])
def test_every_example_parses_and_produces_a_result(name, handler):
    result = handler(load(name))
    assert result["currency"] == "USD"
    assert result["data_mode"] == "synthetic"


def test_the_energy_examples_are_not_degraded():
    """The energy book is the example a reader is shown first. If it were
    degraded, the page they land on would carry a warning banner."""
    for name, handler in (("energy_tail.json", tail_risk),
                          ("energy_book.json", portfolio_exposure),
                          ("energy_stress.json", stress_test)):
        result = handler(load(name))
        assert result["degraded"] is False, name
        assert result["degraded_reason"] is None, name


def test_the_four_sample_teaching_example_stays_degraded():
    """Its small sample is the point: it exercises the warning path."""
    result = tail_risk(load("tail.json"))
    assert result["degraded"] is True
    assert "Fewer than 20 observations" in result["degraded_reason"]


def test_the_energy_book_covers_the_six_named_commodity_legs():
    assets = {p["asset"] for p in load("energy_book.json")["positions"]}
    assert assets == {"WTI_CRUDE_FUTURE", "BRENT_CRUDE_FUTURE",
                      "HENRY_HUB_GAS", "TTF_GAS", "JKM_LNG",
                      "PJM_WEST_POWER"}


def test_the_energy_book_and_its_stress_describe_the_same_positions():
    book = {(p["id"], p["asset"], p["market_value"])
            for p in load("energy_book.json")["positions"]}
    stress = {(p["id"], p["asset"], p["market_value"])
              for p in load("energy_stress.json")["positions"]}
    assert book == stress
    assert load("energy_book.json")["nav"] == load("energy_stress.json")["nav"]


def test_the_converted_currency_is_stated_in_the_file():
    """A TTF leg is quoted in EUR per MWh upstream. The contract requires
    the conversion to be done before submission, so the file has to say it
    was, or the number is unattributable."""
    for name in ("energy_book.json", "energy_stress.json"):
        source = load(name)["source"]
        assert "USD per EUR" in source
        assert "not market data" in source


def test_the_energy_scenarios_state_a_shape_and_claim_no_probability():
    source = load("energy_stress.json")["source"]
    assert "neither carrying a probability" in source
    assert "neither a forecast" in source
    assert "not fitted to a dated episode" in source \
        or "neither fitted to a dated episode" in source
    names = [s["name"] for s in load("energy_stress.json")["scenarios"]]
    assert names == ["european_gas_supply_dislocation_shape",
                     "global_energy_demand_collapse_shape"]


def test_the_energy_stress_has_a_scenario_the_book_loses_in():
    """A stress example every scenario of which is profitable would
    demonstrate nothing about loss."""
    losses = [s["loss"] for s in stress_test(load("energy_stress.json"))
              ["scenarios"]]
    assert max(losses) > 0


def test_the_summary_lines_state_the_sign_convention_and_the_flag():
    lines = summarise("tail", tail_risk(load("tail.json")))
    assert any("loss is positive" in line for line in lines)
    assert any(line.startswith("  DEGRADED:") for line in lines)
    lines = summarise("stress", stress_test(load("energy_stress.json")))
    assert any("degraded:  no" in line for line in lines)
    assert any("worst three positions" in line for line in lines)


def test_the_summary_refuses_an_error_envelope():
    with pytest.raises(ValueError):
        summarise("tail", {"error": "ValidationError", "message": "no"})
