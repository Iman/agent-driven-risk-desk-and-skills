import copy
import pytest

pytestmark = pytest.mark.unit
from riskdesk.analytics import tail_risk, portfolio_exposure, stress_test


def meta():
    return dict(as_of="2026-09-12", currency="USD", source="synthetic test", data_mode="synthetic")


def tail():
    return dict(**meta(), pnl=[-100, -50, 0, 50], confidence=.625, horizon_days=1, portfolio_value=1000)


def portfolio():
    return dict(**meta(), nav=1000, positions=[
        {"id": "long", "asset": "A", "market_value": 600, "instrument_type": "linear"},
        {"id": "short", "asset": "B", "market_value": -200, "instrument_type": "linear"}])


def test_fractional_tail_mass_matches_hand_calculation():
    result = tail_risk(tail())
    assert result["var"] == pytest.approx(50)
    assert result["expected_shortfall"] == pytest.approx((100 + .5*50)/1.5)
    assert result["degraded"]
    assert result["horizon_days"] == 1


@pytest.mark.parametrize('count,confidence,var,es,mass',[
    (20,.95,20,20,1),(100,.99,100,100,1),(100,.95,96,98,5),(40,.975,40,40,1)])
def test_exact_integer_tail_boundary_is_not_shifted_by_float_rounding(count,confidence,var,es,mass):
    request=tail();request.update(pnl=list(range(-count,0)),confidence=confidence)
    result=tail_risk(request)
    assert result['var']==pytest.approx(var)
    assert result['expected_shortfall']==pytest.approx(es)
    assert result['tail_probability_mass']==mass


def test_gain_only_sample_does_not_become_positive_loss():
    request = tail(); request["pnl"] = [10,20,30,40]
    assert tail_risk(request)["var"] < 0


@pytest.mark.parametrize("change", [
    {"pnl": [1, float("nan")]}, {"pnl": [1]}, {"confidence": 1},
    {"confidence": 0}, {"portfolio_value": 0}, {"horizon_days": 0}, {"surprise": 1},
])
def test_invalid_tail_inputs_are_refused(change):
    request = tail(); request.update(change)
    with pytest.raises(ValueError): tail_risk(request)


def test_exposure_sign_scaling_and_concentration():
    result = portfolio_exposure(portfolio())
    assert result["gross_exposure"] == 800
    assert result["net_exposure"] == 400
    assert result["gross_leverage"] == .8
    assert result["gross_shares"]["A"] == .75


def test_stress_all_positions_including_short_are_revalued():
    request = portfolio(); request["scenarios"] = [{"name":"down", "shocks":{"A":-.1,"B":-.2}}]
    result = stress_test(request)
    assert result["scenarios"][0]["pnl"] == pytest.approx(-20)
    assert result["scenarios"][0]["loss"] == pytest.approx(20)


def test_missing_shock_is_not_zero():
    request = portfolio(); request["scenarios"] = [{"name":"down", "shocks":{"A":-.1}}]
    with pytest.raises(ValueError): stress_test(request)


def test_derivatives_cannot_be_treated_as_linear_holdings():
    request = portfolio(); request["positions"][0]["instrument_type"] = "option"
    with pytest.raises(ValueError): portfolio_exposure(request)


def test_duplicate_positions_are_refused():
    request = portfolio(); request["positions"].append(copy.deepcopy(request["positions"][0]))
    with pytest.raises(ValueError): portfolio_exposure(request)
