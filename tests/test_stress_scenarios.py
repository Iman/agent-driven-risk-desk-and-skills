"""Historical replay, scenario library, reverse stress and scenario scaling.

Each calculation is checked against something it does not share code with:
hand arithmetic, an exhaustive search over every pair of dates, an explicit
matrix inverse, a grid over the feasible line, or a seeded simulation.
"""
import copy
import importlib.util
import itertools
import math
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from riskdesk.analytics import stress_test
from riskdesk.scenarios import (SCENARIO_LIBRARY, historical_replay, reverse_stress, scale_scenario,
                                scenario_library)

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parent.parent


def book(*positions):
    positions = positions or (("long", "A", 600), ("short", "B", -200))
    return dict(as_of="2026-09-12", currency="USD", source="synthetic test", data_mode="synthetic", nav=1000,
                positions=[dict(id=i, asset=a, market_value=v, instrument_type="linear") for i, a, v in positions])


def replay(**change):
    request = dict(book(), scenario_name="window", start="2020-01-01", end="2020-01-04", prices={
        "A": {"2020-01-01": 100, "2020-01-02": 120, "2020-01-03": 60, "2020-01-04": 90},
        "B": {"2020-01-01": 50, "2020-01-02": 40, "2020-01-03": 60, "2020-01-04": 30}})
    request.update(change)
    return request


# ---------------------------------------------------------------- replay

def test_end_over_start_replay_matches_hand_arithmetic():
    result = historical_replay(replay())
    # A: 90/100 - 1 = -0.10; B: 30/50 - 1 = -0.40; P&L = 600*-0.10 + -200*-0.40 = +20
    assert result["shocks"] == pytest.approx({"A": -0.1, "B": -0.4})
    assert result["scenarios"][0]["pnl"] == pytest.approx(20)
    assert result["scenarios"][0]["loss"] == pytest.approx(-20)
    assert result["series"]["A"]["from_date"] == "2020-01-01" and result["series"]["A"]["to_date"] == "2020-01-04"
    assert not result["degraded"]
    assert (result["currency"], result["as_of"], result["data_mode"]) == ("USD", "2026-09-12", "synthetic")


def test_worst_peak_to_trough_matches_hand_arithmetic_and_is_labelled():
    result = historical_replay(replay(measure="worst_peak_to_trough"))
    # A: 120 -> 60 is -50%. B: 50 -> 40 is -20%, then 60 -> 30 is -50%.
    assert result["shocks"] == pytest.approx({"A": -0.5, "B": -0.5})
    assert (result["series"]["B"]["from_date"], result["series"]["B"]["to_date"]) == ("2020-01-03", "2020-01-04")
    assert any("need not coincide" in text for text in result["assumptions"])


def test_worst_peak_to_trough_equals_an_exhaustive_search_over_date_pairs():
    rng = np.random.default_rng(7)
    for _ in range(50):
        levels = np.exp(np.cumsum(rng.normal(0, 0.05, 40))) * 100
        days = [date.fromordinal(737425 + i).isoformat() for i in range(40)]
        request = replay(start=days[0], end=days[-1], prices={"A": dict(zip(days, levels.tolist())),
                                                              "B": dict(zip(days, levels.tolist()))})
        request["measure"] = "worst_peak_to_trough"
        brute = min(min(levels[j] / levels[i] - 1 for i, j in itertools.combinations(range(40), 2)), 0.0)
        assert historical_replay(request)["shocks"]["A"] == pytest.approx(brute, rel=1e-12, abs=1e-15)


def test_levels_outside_the_window_are_ignored():
    prices = replay()["prices"]
    prices["A"]["2020-01-05"] = 1  # a crash after the window must not count
    prices["A"]["2019-12-31"] = 1000  # nor a peak before it
    result = historical_replay(replay(prices=prices, measure="worst_peak_to_trough"))
    assert result["shocks"]["A"] == pytest.approx(-0.5)


def test_a_rising_series_has_no_fall_rather_than_a_missing_value():
    prices = replay()["prices"]
    prices["A"] = {"2020-01-01": 1, "2020-01-04": 2}
    assert historical_replay(replay(prices=prices, measure="worst_peak_to_trough"))["shocks"]["A"] == 0


def test_a_proxy_is_reported_and_degrades_the_result():
    prices = replay()["prices"]
    prices["B_proxy"] = prices.pop("B")
    result = historical_replay(replay(prices=prices, proxies={"B": "B_proxy"}))
    assert result["degraded"] and "B replayed with proxy series B_proxy" in result["degraded_reason"]
    assert result["series"]["B"]["series"] == "B_proxy"
    assert result["shocks"]["B"] == pytest.approx(-0.4)


@pytest.mark.parametrize("change,message", [
    ({"prices": {"A": {"2020-01-01": 1, "2020-01-04": 2}}}, "no price series for B"),
    ({"end": "2020-01-05"}, "has no level on 2020-01-05"),
    ({"start": "2020-01-04"}, "window start must be before"),
    ({"proxies": {"C": "A"}}, "proxies may only map portfolio assets"),
    ({"prices": {"A": {"2020-01-01": 0, "2020-01-04": 2}, "B": {"2020-01-01": 1, "2020-01-04": 2}}}, "greater than 0"),
    ({"prices": {"A": {"2020-01-01": float("inf"), "2020-01-04": 2}, "B": {"2020-01-01": 1, "2020-01-04": 2}}},
     "finite"),
    ({"measure": "average"}, "measure"),
])
def test_invalid_replays_are_refused(change, message):
    with pytest.raises(ValueError, match=message):
        historical_replay(replay(**change))


def test_a_missing_start_date_is_an_error_not_a_nearest_date():
    prices = replay()["prices"]
    del prices["B"]["2020-01-01"]
    with pytest.raises(ValueError, match="B has no level on 2020-01-01"):
        historical_replay(replay(prices=prices))


def test_the_replay_input_hash_covers_the_prices():
    changed = replay()
    changed["prices"]["A"]["2020-01-02"] = 121
    assert historical_replay(replay())["input_sha256"] != historical_replay(changed)["input_sha256"]


# ---------------------------------------------------------------- library

def test_the_library_holds_dates_and_sources_only():
    windows = scenario_library()["windows"]
    assert [w["id"] for w in windows] == ["lehman-2008", "covid-2020", "uk-gilt-ldi-2022"]
    for window in windows:
        assert set(window) == {"id", "name", "start", "end", "reason", "sources"}
        assert date.fromisoformat(window["start"]) < date.fromisoformat(window["end"])
        assert window["sources"] and all(s["url"].startswith("https://") for s in window["sources"])


def test_the_library_dates_are_the_ones_cited_in_reference_md():
    text = (ROOT / "plugins/risk-desk/skills/risk-stress/reference.md").read_text(encoding="utf-8")
    assert [(w["start"], w["end"]) for w in SCENARIO_LIBRARY] == [
        ("2008-09-12", "2008-10-31"), ("2020-02-19", "2020-03-23"), ("2022-09-22", "2022-10-14")]
    for window in SCENARIO_LIBRARY:
        assert window["id"] in text and window["start"] in text and window["end"] in text


def test_the_library_returns_a_copy():
    scenario_library()["windows"][0]["sources"][0]["url"] = "changed"
    assert SCENARIO_LIBRARY[0]["sources"][0]["url"].startswith("https://")


def test_a_library_window_replays_with_caller_prices():
    window = scenario_library()["windows"][2]
    prices = {a: {window["start"]: 100, window["end"]: 90} for a in "AB"}
    result = historical_replay(dict(book(), scenario_name=window["id"], start=window["start"],
                                    end=window["end"], prices=prices))
    assert result["scenarios"][0]["name"] == "uk-gilt-ldi-2022"
    assert result["scenarios"][0]["pnl"] == pytest.approx(600 * -0.1 + -200 * -0.1)


# ---------------------------------------------------------------- reverse stress

def reverse(target=50.0, sigma=((0.04, 0.01), (0.01, 0.09)), **change):
    request = dict(book(), target_loss=target, horizon_days=10, assets=["A", "B"],
                   covariance=[list(row) for row in sigma])
    request.update(change)
    return request


def random_case(seed, n=4):
    rng = np.random.default_rng(seed)
    factor = rng.normal(0, 0.05, (n, n))
    sigma = factor @ factor.T + np.eye(n) * 1e-4
    w = rng.normal(0, 1000, n)
    names = [f"X{i}" for i in range(n)]
    request = dict(book(*[(f"p{i}", names[i], float(w[i])) for i in range(n)]), target_loss=100.0,
                   horizon_days=1, assets=names, covariance=sigma.tolist())
    return request, sigma, w


def test_one_asset_reverse_stress_matches_hand_arithmetic():
    request = dict(book(("only", "A", 1000)), target_loss=100, horizon_days=1, assets=["A"], covariance=[[0.04]])
    result = reverse_stress(request)
    # s = -L / w = -0.1; distance = L / (|w| sigma) = 100 / (1000 * 0.2) = 0.5
    assert result["shocks"]["A"] == pytest.approx(-0.1)
    assert result["mahalanobis_distance"] == pytest.approx(0.5)
    assert result["loss_exceedance_probability_if_normal"] == pytest.approx(0.3085375387259869)  # 1 - Phi(0.5)


@pytest.mark.parametrize("seed", range(5))
def test_closed_form_reaches_the_loss_and_beats_every_other_shock_with_that_loss(seed):
    request, sigma, w = random_case(seed)
    request["covariance"] = (np.asarray(request["covariance"]) * 1e-4).tolist()  # keep shocks inside the floors
    sigma = np.asarray(request["covariance"])
    result = reverse_stress(request)
    assert result["solution"] == "closed form"
    s = np.array([result["shocks"][a] for a in request["assets"]])
    inverse = np.linalg.inv(sigma)
    distance = math.sqrt(s @ inverse @ s)
    assert result["scenarios"][0]["loss"] == pytest.approx(100.0, rel=1e-12)
    assert result["mahalanobis_distance"] == pytest.approx(distance, rel=1e-9)
    assert result["mahalanobis_distance"] == pytest.approx(100.0 / math.sqrt(w @ sigma @ w), rel=1e-9)
    # Any other shock with the same loss differs by v with w'v = 0, and must be further away.
    rng = np.random.default_rng(seed + 100)
    for v in rng.normal(0, 1e-3, (2000, len(w))):
        v -= (w @ v) / (w @ w) * w
        assert math.sqrt((s + v) @ inverse @ (s + v)) >= distance * (1 - 1e-12)


def test_the_normal_probability_agrees_with_a_seeded_simulation():
    request, sigma, w = random_case(3)
    result = reverse_stress(request)
    draws = np.random.default_rng(11).multivariate_normal(np.zeros(len(w)), sigma, 400_000)
    observed = float(np.mean(-(draws @ w) >= 100.0))
    p = result["loss_exceedance_probability_if_normal"]
    assert abs(observed - p) < 4 * math.sqrt(p * (1 - p) / 400_000)
    assert any(text.startswith("ASSUMPTION:") for text in result["assumptions"])


def test_a_binding_minus_100_floor_matches_a_grid_over_the_feasible_line():
    # Two long assets of 1000. Unbounded, s_A = -L (0.25*1000 + 0.01*1000) / (w' S w) < -1.
    sigma = ((0.25, 0.01), (0.01, 0.01))
    request = dict(book(("a", "A", 1000), ("b", "B", 1000)), target_loss=1500, horizon_days=1, assets=["A", "B"],
                   covariance=[list(r) for r in sigma])
    w, s0 = np.array([1000.0, 1000.0]), np.array(sigma)
    assert (-1500 * s0 @ w / (w @ s0 @ w))[0] < -1
    result = reverse_stress(request)
    assert result["solution"].startswith("bounded") and result["binding_floors"] == ["A"]
    inverse = np.linalg.inv(s0)
    grid = np.linspace(-1, 0.5, 300_001)  # s_A = t, s_B = (-1500 - 1000 t) / 1000
    line = np.stack([grid, (-1500 - 1000 * grid) / 1000], axis=1)
    feasible = line[(line >= -1).all(axis=1)]
    best = feasible[np.argmin(np.einsum("ij,jk,ik->i", feasible, inverse, feasible))]
    assert [result["shocks"]["A"], result["shocks"]["B"]] == pytest.approx(best.tolist(), abs=1e-5)
    assert result["scenarios"][0]["loss"] == pytest.approx(1500, rel=1e-7)
    assert result["mahalanobis_distance"] >= result["unbounded_mahalanobis_distance"]


def test_a_supplied_floor_binds_and_satisfies_the_optimality_conditions():
    request, sigma, w = random_case(4, n=3)
    unbounded = reverse_stress(request)["shocks"]
    target = min(unbounded, key=unbounded.get)
    request["floors"] = {target: unbounded[target] / 2}
    result = reverse_stress(request)
    s = np.array([result["shocks"][a] for a in request["assets"]])
    assert target in result["binding_floors"]
    assert result["shocks"][target] == pytest.approx(request["floors"][target], abs=1e-9)
    # KKT: Sigma^-1 s = lambda w + mu, with mu zero off the binding floor and non-negative on it.
    gradient = np.linalg.solve(sigma, s)
    free = [i for i, a in enumerate(request["assets"]) if a not in result["binding_floors"]]
    lam = gradient[free[0]] / w[free[0]]
    assert gradient[free] == pytest.approx(lam * w[free], rel=1e-5, abs=1e-8)
    bound = request["assets"].index(target)
    assert gradient[bound] - lam * w[bound] >= -1e-8


def test_a_loss_beyond_what_the_floors_allow_is_refused():
    request = dict(book(("a", "A", 1000)), target_loss=1001, horizon_days=1, assets=["A"], covariance=[[0.04]])
    with pytest.raises(ValueError, match="largest loss reachable within the floors"):
        reverse_stress(request)


def test_losing_the_whole_long_book_is_reachable_exactly():
    request = dict(book(("a", "A", 1000)), target_loss=1000, horizon_days=1, assets=["A"], covariance=[[4.0]])
    assert reverse_stress(request)["shocks"]["A"] == pytest.approx(-1)


@pytest.mark.parametrize("change,message", [
    ({"covariance": [[0.04, 0.01], [0.01, -0.09]]}, "positive definite"),
    ({"covariance": [[0.04, 0.02], [0.01, 0.09]]}, "symmetric"),
    ({"covariance": [[0.04, 0.01]]}, "square"),
    ({"covariance": [[0.04, float("nan")], [0.01, 0.09]]}, "finite"),
    ({"assets": ["A", "C"]}, "each portfolio asset exactly once"),
    ({"assets": ["A", "A"]}, "each portfolio asset exactly once"),
    ({"floors": {"C": -0.5}}, "floors may only name"),
    ({"floors": {"A": -1.5}}, "below -100%"),
    ({"target_loss": 0}, "greater than 0"),
    ({"horizon_days": 0}, "greater than 0"),
])
def test_invalid_reverse_stress_requests_are_refused(change, message):
    with pytest.raises(ValueError, match=message):
        reverse_stress(reverse(**change))


def test_a_book_with_no_net_exposure_is_refused():
    request = reverse()
    request["positions"] = [dict(id="x", asset="A", market_value=100, instrument_type="linear"),
                            dict(id="y", asset="A", market_value=-100, instrument_type="linear"),
                            dict(id="z", asset="B", market_value=0, instrument_type="linear")]
    with pytest.raises(ValueError, match="no P&L variance"):
        reverse_stress(request)


# ---------------------------------------------------------------- scaling

def scale(target=50.0, shocks=None):
    return dict(book(), target_loss=target, scenario=dict(name="down", shocks=shocks or {"A": -0.1, "B": -0.2}))


def test_scaling_matches_hand_arithmetic():
    result = scale_scenario(scale())
    # Base loss: -(600*-0.1 + -200*-0.2) = 20. k = 50/20 = 2.5.
    assert result["base_loss"] == pytest.approx(20)
    assert result["multiple"] == pytest.approx(2.5)
    assert result["shocks"] == pytest.approx({"A": -0.25, "B": -0.5})
    assert [row["loss"] for row in result["scenarios"]] == pytest.approx([20, 50])
    independent = stress_test(dict(book(), scenarios=[dict(name="x", shocks=result["shocks"])]))
    assert independent["scenarios"][0]["loss"] == pytest.approx(50)


@pytest.mark.parametrize("request_,message", [
    (scale(shocks={"A": 0.1, "B": 0.0}), "does not lose money"),
    (scale(target=120), r"multiple 6 takes B below -100%"),  # A -0.6, B -1.2
    (scale(shocks={"A": -0.1}), "exactly the portfolio assets"),
])
def test_invalid_scaling_is_refused(request_, message):
    with pytest.raises(ValueError, match=message):
        scale_scenario(request_)


def test_unknown_fields_are_refused_everywhere():
    for handler, request in ((historical_replay, replay()), (reverse_stress, reverse()), (scale_scenario, scale())):
        with pytest.raises(ValidationError):
            handler(dict(copy.deepcopy(request), surprise=1))


# ---------------------------------------------------------------- examples and checker

@pytest.fixture(scope="module")
def checker():
    path = ROOT / "plugins/risk-desk/skills/risk-stress/scripts/check_artifact.py"
    spec = importlib.util.spec_from_file_location("risk_stress_check_artifact", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name,handler", [("stress_replay.json", historical_replay),
                                          ("stress_reverse.json", reverse_stress),
                                          ("stress_scale.json", scale_scenario)])
def test_each_example_runs_and_passes_the_checker(name, handler, checker):
    import json
    result = handler(json.loads((ROOT / "examples" / name).read_text(encoding="utf-8")))
    assert result["data_mode"] == "synthetic"
    assert checker.problems(result) == []


def test_the_checker_catches_a_tampered_result(checker):
    result = reverse_stress(reverse())
    result["scenarios"][0]["loss"] += 1
    assert checker.problems(result)
    scaled = scale_scenario(scale())
    scaled["shocks"]["A"] = -0.3
    assert checker.problems(scaled)
    replayed = historical_replay(replay())
    replayed["series"]["A"]["to_level"] = 95
    assert checker.problems(replayed)
