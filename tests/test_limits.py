"""Limit checks and pre-trade what-if, against hand calculations on the shipped example book.

Book (examples/portfolio.json): A +600, B -200, NAV 1000, so gross 800, net 400,
gross leverage 0.8 and A's gross share 0.75.
"""
import importlib.util
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from riskdesk.analytics import portfolio_exposure, stress_test, tail_risk
from riskdesk.limits import check_limits, what_if

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def meta():
    return dict(as_of="2026-09-12", currency="USD", source="synthetic test", data_mode="synthetic")


def results():
    return dict(exposure=portfolio_exposure(load("portfolio.json")), stress=stress_test(load("stress.json")),
                tail=tail_risk(load("tail.json")))


def request(*limits, **kwargs):
    return dict(meta(), limits=list(limits), results=kwargs.get("results", results()))


def limit(name, metric, direction, value, warning=None, **scope):
    return dict(name=name, metric=metric, direction=direction, limit=value, warning=warning, **scope)


def by_name(result):
    return {row["name"]: row for row in result["limits"]}


def test_statuses_and_utilisation_match_hand_calculation():
    result = check_limits(request(
        limit("gross", "gross_exposure", "max", 1000, 700),        # 800 >= 700 warn, 800 <= 1000
        limit("net", "net_exposure", "max", 300),                  # 400 > 300
        limit("share", "gross_share", "max", .8, asset="A"),       # .75
        limit("lev", "gross_leverage", "max", .8),                 # equal to limit: within
        limit("stress", "stress_loss", "max", 15, scenario="combined_down"),  # loss 20
        limit("var", "var", "max", 60)))                           # tail.json VaR 50
    rows = by_name(result)
    assert [rows[n]["status"] for n in ("gross", "net", "share", "lev", "stress", "var")] == \
        ["warning", "breach", "within", "within", "breach", "within"]
    assert rows["gross"]["utilisation"] == pytest.approx(.8)
    assert rows["share"]["utilisation"] == pytest.approx(.75/.8)
    assert rows["share"]["scope"] == "asset"
    assert rows["stress"]["value"] == pytest.approx(20)
    assert rows["var"]["value"] == pytest.approx(50)
    assert rows["var"]["basis"] == dict(confidence=.625, horizon_days=1)
    assert result["overall_status"] == "breach"
    assert result["status_counts"] == dict(within=3, not_evaluated=0, warning=1, breach=2)
    assert result["degraded"] and "tail result is degraded" in result["degraded_reason"]


def test_min_limits_mirror_max_limits():
    rows = by_name(check_limits(request(
        limit("floor", "net_exposure", "min", 500),           # 400 < 500
        limit("near", "net_exposure", "min", 300, 450),       # 400 <= 450 warn, >= 300
        limit("ok", "net_exposure", "min", 100, 200))))
    assert [rows[n]["status"] for n in ("floor", "near", "ok")] == ["breach", "warning", "within"]


def test_missing_metric_is_reported_not_skipped():
    payload = results(); del payload["tail"]
    result = check_limits(request(limit("var", "var", "max", 60),
                                  limit("ghost", "gross_share", "max", .5, asset="Z"),
                                  limit("nos", "stress_loss", "max", 1, scenario="missing"),
                                  limit("ok", "gross_exposure", "max", 1000), results=payload))
    rows = by_name(result)
    assert rows["var"]["status"] == rows["ghost"]["status"] == rows["nos"]["status"] == "not_evaluated"
    assert "no tail result" in rows["var"]["reason"]
    assert "asset Z" in rows["ghost"]["reason"]
    assert "scenario missing" in rows["nos"]["reason"]
    assert rows["var"]["value"] is None
    assert result["overall_status"] == "not_evaluated"
    assert result["degraded"] and "3 of 4 limits not evaluated" in result["degraded_reason"]


def test_currency_mismatch_blocks_evaluation_and_as_of_mismatch_is_flagged():
    payload = results()
    payload["exposure"]["currency"] = "EUR"
    payload["stress"]["as_of"] = "2026-09-11"
    result = check_limits(request(limit("gross", "gross_exposure", "max", 1000),
                                  limit("stress", "stress_loss", "max", 100, scenario="combined_down"),
                                  results=payload))
    rows = by_name(result)
    assert rows["gross"]["status"] == "not_evaluated" and "EUR" in rows["gross"]["reason"]
    assert rows["stress"]["status"] == "within"
    assert "exposure result currency EUR differs from USD" in result["degraded_reason"]
    assert "stress result as-of 2026-09-11 differs from 2026-09-12" in result["degraded_reason"]


def test_error_envelope_is_not_evaluated():
    result = check_limits(request(limit("gross", "gross_exposure", "max", 1),
                                  results={"exposure": {"error": "ValidationError", "message": "bad",
                                                        "currency": "USD", "as_of": "2026-09-12"}}))
    assert result["limits"][0]["status"] == "not_evaluated"
    assert "error: bad" in result["limits"][0]["reason"]


@pytest.mark.parametrize("bad", [
    limit("x", "gross_exposure", "max", 100, 120),             # warning beyond a max limit
    limit("x", "net_exposure", "min", 100, 50),                # warning beyond a min limit
    limit("x", "gross_share", "max", .5),                      # asset missing
    limit("x", "gross_exposure", "max", 1, asset="A"),         # asset not allowed
    limit("x", "stress_loss", "max", 1),                       # scenario missing
    limit("x", "volatility", "max", 1),                        # unknown metric
    limit("x", "var", "up", 1),                                # unknown direction
    dict(limit("x", "var", "max", 1), surprise=1),
])
def test_invalid_limits_are_refused(bad):
    with pytest.raises(ValidationError):
        check_limits(request(bad))


def test_duplicate_limit_names_are_refused():
    with pytest.raises(ValidationError):
        check_limits(request(limit("x", "var", "max", 1), limit("x", "var", "max", 2)))


def test_non_finite_payload_value_is_refused():
    payload = results(); payload["exposure"]["gross_exposure"] = float("inf")
    with pytest.raises(ValueError):
        check_limits(request(limit("g", "gross_exposure", "max", 1), results=payload))


def whatif(**extra):
    book = load("portfolio.json")
    # Before P&L is tail.json's [-100, -50, 0, 50]: A carries it all (600 x r_A), B and C return zero.
    return dict(book, trades=[dict(asset="A", market_value_change=-100), dict(asset="C", market_value_change=300)],
                scenarios=[dict(name="down", shocks=dict(A=-.1, B=-.2, C=-.5))],
                asset_returns=dict(A=[-1/6, -1/12, 0, 1/12], B=[0]*4, C=[0]*4),
                confidence=.625, horizon_days=1, **extra)


def test_what_if_matches_hand_revaluation():
    result = what_if(whatif())
    before, after, change = result["before"], result["after"], result["change"]
    assert before["exposure"]["gross_exposure"] == pytest.approx(800)
    assert after["exposure"]["gross_exposure"] == pytest.approx(1000)   # 500 + 200 + 300
    assert after["exposure"]["net_exposure"] == pytest.approx(600)      # 500 - 200 + 300
    assert change["gross_leverage"] == pytest.approx(.2)
    # 600(-.1) - 200(-.2) = -20; 500(-.1) - 200(-.2) + 300(-.5) = -160
    assert before["stress"]["scenarios"][0]["loss"] == pytest.approx(20)
    assert after["stress"]["scenarios"][0]["loss"] == pytest.approx(160)
    assert change["stress_loss"] == {"down": pytest.approx(140)}
    # Before reproduces the hand-checked tail.json result; after scales A's P&L by 500/600.
    assert before["tail"]["var"] == pytest.approx(50)
    assert after["tail"]["var"] == pytest.approx(50*5/6)
    assert after["tail"]["expected_shortfall"] == pytest.approx((100 + .5*50)/1.5*5/6)
    assert change["var"] == pytest.approx(50*5/6 - 50)
    assert result["limits_after"] is None
    assert any("scale with its value" in a for a in result["assumptions"])
    assert result["degraded"] and "before tail" in result["degraded_reason"]


def test_what_if_limit_check_runs_on_the_after_book():
    result = what_if(whatif(limits=[limit("gross", "gross_exposure", "max", 900),
                                    limit("var", "var", "max", 45)]))
    rows = by_name(result["limits_after"])
    assert rows["gross"]["status"] == "breach" and rows["gross"]["value"] == pytest.approx(1000)
    assert rows["var"]["status"] == "within"
    assert result["limits_after"]["overall_status"] == "breach"


def test_what_if_exposure_only():
    payload = dict(load("portfolio.json"), trades=[dict(asset="B", market_value_change=200)])
    result = what_if(payload)
    assert result["after"]["exposure"]["gross_exposure"] == pytest.approx(600)
    assert set(result["after"]) == {"exposure"}
    assert result["degraded"] is False


@pytest.mark.parametrize("change", [
    {"confidence": None},                                     # partial tail inputs
    {"asset_returns": dict(A=[0, 0], B=[0, 0])},              # C missing
    {"asset_returns": dict(A=[0, 0], B=[0, 0], C=[0])},       # ragged
    {"trades": []},
    {"scenarios": [dict(name="down", shocks=dict(A=-.1, B=-.2))]},   # C unshocked after the trade
])
def test_what_if_refuses_incomplete_inputs(change):
    payload = whatif(); payload.update(change)
    with pytest.raises(ValueError):
        what_if(payload)


def test_a_sale_reduces_the_held_position_rather_than_offsetting_it():
    result = what_if(dict(load("portfolio.json"), trades=[dict(asset="A", market_value_change=-600)]))
    assert result["after"]["exposure"]["gross_exposure"] == pytest.approx(200)
    assert result["change"]["gross_exposure"] == pytest.approx(-600)


def test_an_asset_in_several_positions_needs_a_position_id():
    book = load("portfolio.json")
    book["positions"].append(dict(id="long2", asset="A", market_value=100, instrument_type="linear"))
    with pytest.raises(ValueError, match="name the position_id"):
        what_if(dict(book, trades=[dict(asset="A", market_value_change=-50)]))
    result = what_if(dict(book, trades=[dict(asset="A", market_value_change=-50, position_id="long2")]))
    assert result["after"]["exposure"]["gross_exposure"] == pytest.approx(850)   # 600 + 50 + 200


def test_what_if_new_position_id_cannot_collide_with_a_held_asset():
    payload = whatif(); payload["positions"][0]["id"] = "what-if-2"     # holds A; trade 2 opens C
    with pytest.raises(ValueError, match="holds A, not C"):
        what_if(payload)


def checker():
    spec = importlib.util.spec_from_file_location(
        "risk_limits_check", ROOT / "plugins/risk-desk/skills/risk-limits/scripts/check_artifact.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_artifact_checker_passes_real_results_and_catches_a_wrong_status():
    check = checker().check
    result = check_limits(request(limit("gross", "gross_exposure", "max", 1000, 700),
                                  limit("var", "var", "max", 60)))
    assert check(result) == []
    assert check(what_if(whatif(limits=[limit("g", "gross_exposure", "max", 900)]))) == []
    result["limits"][0]["status"] = "within"
    assert any("status within" in p for p in check(result))


def test_examples_parse_and_produce_results():
    for name, handler in (("limits_check.json", check_limits), ("limits_what_if.json", what_if)):
        result = handler(load(name))
        assert result["currency"] == "USD" and result["data_mode"] == "synthetic"
        assert checker().check(result) == []
