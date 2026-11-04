"""Covariance, Euler allocation and factor exposure, each against an independent check.

The checks are closed forms, a brute-force recomputation, a published formula
reimplemented here from the paper's own lemmas, or an existing implementation
(risk_tail via skfolio, scikit-learn LinearRegression). Sources are in
plugins/risk-desk/skills/risk-attribution/reference.md.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError
from scipy.integrate import quad
from scipy.stats import norm
from sklearn.linear_model import LinearRegression

from riskdesk.analytics import tail_risk
from riskdesk.decomposition import (covariance_estimate, factor_exposure, historical_es,
                                    parametric_var)

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(7)


def meta():
    return dict(as_of="2026-11-04", currency="EUR", source="synthetic test", data_mode="synthetic")


def position(pid, asset, value):
    return dict(id=pid, asset=asset, market_value=value, instrument_type="linear")


def history(rows=60, assets=("A", "B", "C")):
    returns = RNG.normal(0, 0.01, (rows, len(assets))) + RNG.normal(0, 0.01, (rows, 1))
    return dict(**meta(), assets=list(assets), returns=returns.tolist(), horizon_days=1)


def book():
    return dict(nav=1000, positions=[position("p1", "A", 500), position("p2", "B", -300),
                                     position("p3", "A", 200), position("p4", "C", 100)])


# Covariance ----------------------------------------------------------------

def test_sample_covariance_matches_brute_force_sum():
    request = history() | dict(method="sample")
    r = np.asarray(request["returns"])
    centred = r - r.mean(axis=0)
    brute = sum(np.outer(row, row) for row in centred) / (len(r) - 1)
    result = covariance_estimate(request)
    assert np.allclose(result["covariance"], brute, rtol=1e-12, atol=0)
    assert result["positive_definite"] and not result["degraded"] and result["repair"] is None
    assert np.allclose(np.diag(result["correlation"]), 1)


def test_ewma_matches_riskmetrics_recursion():
    """RiskMetrics 1996 Eq. [5.6] run from zero gives (1-l) sum l^i r r'; dividing by
    1-l^T is the finite normalisation of Eq. [5.2]."""
    request = history() | dict(method="ewma", decay=0.94)
    r = np.asarray(request["returns"])
    state = np.zeros((3, 3))
    for row in r:
        state = 0.94 * state + 0.06 * np.outer(row, row)
    result = covariance_estimate(request)
    assert np.allclose(result["covariance"], state / (1 - 0.94 ** len(r)), rtol=1e-12, atol=0)
    assert result["decay"] == 0.94


def test_ledoit_wolf_matches_the_paper_lemmas():
    """Ledoit and Wolf, Lemmas 3.2 to 3.5 and Eq. (14), with the norm of
    Definitions 1 and 2, ||A||^2 = tr(AA')/p, on demeaned data with S = X'X/n."""
    request = history(rows=15, assets=tuple("ABCDEFGHIJ")) | dict(method="ledoit_wolf")
    x = np.asarray(request["returns"])
    x = x - x.mean(axis=0)
    n, p = x.shape
    s = x.T @ x / n
    norm2 = lambda a: np.trace(a @ a.T) / p
    m = np.trace(s) / p
    d2 = norm2(s - m * np.eye(p))
    b2 = min(sum(norm2(np.outer(k, k) - s) for k in x) / n**2, d2)
    expected = b2 / d2 * m * np.eye(p) + (d2 - b2) / d2 * s
    result = covariance_estimate(request)
    assert result["shrinkage"] == pytest.approx(b2 / d2, rel=1e-10)
    assert np.allclose(result["covariance"], expected, rtol=1e-10, atol=0)


def test_singular_sample_is_flagged_not_repaired_and_shrinkage_is_positive_definite():
    request = history(rows=3, assets=tuple("ABCDE"))
    sample = covariance_estimate(request | dict(method="sample"))
    assert not sample["positive_definite"] and sample["degraded"]
    assert "no repair" in sample["degraded_reason"] and sample["repair"] is None
    r = np.asarray(request["returns"])
    assert np.allclose(sample["covariance"], np.cov(r, rowvar=False))
    shrunk = covariance_estimate(request | dict(method="ledoit_wolf"))
    assert shrunk["positive_definite"] and not shrunk["degraded"]


def test_zero_variance_asset_has_no_correlation():
    request = history() | dict(method="sample")
    for row in request["returns"]:
        row[2] = 0.0
    result = covariance_estimate(request)
    assert result["correlation"][0][2] is None and result["correlation"][2][2] is None
    assert result["correlation"][0][1] is not None


@pytest.mark.parametrize("change", [
    dict(method="ewma"), dict(method="sample", decay=0.94), dict(method="ewma", decay=1),
    dict(method="sample", assets=["A", "A", "C"]), dict(method="sample", returns=[[0, 0, 0], [0, 0]]),
    dict(method="sample", returns=[[0, 0, -1.5], [0, 0, 0]]), dict(method="sample", horizon_days=0),
    dict(method="garch"), dict(method="sample", surprise=1)])
def test_invalid_covariance_requests_are_refused(change):
    with pytest.raises(ValidationError):
        covariance_estimate(history() | change)


# Parametric Euler ------------------------------------------------------------

def parametric(confidence=0.99):
    cov = [[0.0004, 0.00012, 0.0], [0.00012, 0.0009, -0.00006], [0.0, -0.00006, 0.0001]]
    return dict(**meta(), **book(), assets=["A", "B", "C"], covariance=cov,
                confidence=confidence, horizon_days=10)


def test_two_asset_closed_form_and_es_by_quadrature():
    request = parametric(0.975)
    request["positions"] = [position("x", "A", 700), position("y", "B", -300)]
    s1, s2, rho = 0.02, 0.03, 0.2
    sigma = np.sqrt(700**2 * s1**2 + 300**2 * s2**2 - 2 * 700 * 300 * rho * s1 * s2)
    result = parametric_var(request)
    assert result["portfolio_std"] == pytest.approx(sigma, rel=1e-12)
    assert result["var"] == pytest.approx(norm.ppf(0.975) * sigma, rel=1e-12)
    # Tasche 2008 Eq. (3.10a): ES is the average of VaR over levels above the confidence.
    integral, _ = quad(norm.ppf, 0.975, 1)
    assert result["expected_shortfall"] == pytest.approx(integral / 0.025 * sigma, rel=1e-8)
    assert result["horizon_days"] == 10 and result["currency"] == "EUR"


@pytest.mark.parametrize("confidence", [0.95, 0.99, 0.999])
def test_components_sum_to_totals(confidence):
    result = parametric_var(parametric(confidence))
    rows = result["positions"]
    assert sum(r["component_var"] for r in rows) == pytest.approx(result["var"], rel=1e-12)
    assert sum(r["component_es"] for r in rows) == pytest.approx(result["expected_shortfall"], rel=1e-12)
    assert sum(r["percentage_var"] for r in rows) == pytest.approx(1, rel=1e-12)
    assert sum(r["percentage_es"] for r in rows) == pytest.approx(1, rel=1e-12)


def test_marginal_matches_central_finite_difference():
    request = parametric()
    base = parametric_var(request)
    for i, row in enumerate(base["positions"]):
        h = 1e-5 * abs(row["market_value"])
        up, down = json.loads(json.dumps(request)), json.loads(json.dumps(request))
        up["positions"][i]["market_value"] += h
        down["positions"][i]["market_value"] -= h
        hi, lo = parametric_var(up), parametric_var(down)
        assert row["marginal_var"] == pytest.approx((hi["var"] - lo["var"]) / (2 * h), rel=1e-7)
        assert row["marginal_es"] == pytest.approx(
            (hi["expected_shortfall"] - lo["expected_shortfall"]) / (2 * h), rel=1e-7)


def test_incremental_matches_recomputing_without_the_position():
    request = parametric()
    base = parametric_var(request)
    for i, row in enumerate(base["positions"]):
        reduced = json.loads(json.dumps(request))
        del reduced["positions"][i]
        assert row["incremental_var"] == pytest.approx(base["var"] - parametric_var(reduced)["var"], rel=1e-10)


def test_positions_on_one_asset_share_a_marginal_and_a_single_position_owns_everything():
    rows = parametric_var(parametric())["positions"]
    assert rows[0]["marginal_var"] == pytest.approx(rows[2]["marginal_var"], rel=1e-15)
    single = parametric()
    single["positions"] = [position("only", "B", -250)]
    row, = (result := parametric_var(single))["positions"]
    assert row["component_var"] == pytest.approx(result["var"]) and row["percentage_var"] == pytest.approx(1)
    assert row["incremental_var"] == pytest.approx(result["var"])


@pytest.mark.parametrize("change,message", [
    (dict(covariance=[[0.0004, 0.0001, 0], [0.0002, 0.0009, 0], [0, 0, 0.0001]]), "symmetric"),
    (dict(covariance=[[0.0001, 0.001, 0], [0.001, 0.0001, 0], [0, 0, 0.0001]]), "semidefinite"),
    (dict(positions=[position("z", "A", 0)]), "zero"),
    (dict(positions=[position("z", "Q", 10)]), "no data: Q"),
    (dict(positions=[position("z", "A", 1e200)]), "numerical limits"),
])
def test_invalid_parametric_inputs_are_refused(change, message):
    with pytest.raises(ValueError, match=message):
        parametric_var(parametric() | change)


@pytest.mark.parametrize("change", [
    dict(covariance=[[0.0004, 0], [0, 0.0009]]), dict(assets=["A", "A", "C"]), dict(confidence=1),
    dict(confidence=0.5),
    dict(covariance=[[0.0004, float("nan"), 0], [0, 0.0009, 0], [0, 0, 0.0001]])])
def test_malformed_parametric_contracts_are_refused(change):
    with pytest.raises(ValidationError):
        parametric_var(parametric() | change)


# Historical Euler ES -----------------------------------------------------------

def historical(rows=200, confidence=0.95):
    return history(rows) | book() | dict(confidence=confidence)


@pytest.mark.parametrize("rows,confidence", [(200, 0.95), (20, 0.95), (100, 0.99), (50, 0.97),
                                             (40, 0.975), (1000, 0.975), (7, 0.6)])
def test_components_sum_to_the_risk_tail_es_on_the_same_scenarios(rows, confidence):
    request = historical(rows, confidence)
    result = historical_es(request)
    assert sum(p["component_es"] for p in result["positions"]) == pytest.approx(
        result["expected_shortfall"], rel=1e-12)
    r = np.asarray(request["returns"])
    index = {a: i for i, a in enumerate(request["assets"])}
    pnl = sum(p["market_value"] * r[:, index[p["asset"]]] for p in request["positions"])
    tail = tail_risk(dict(**meta(), pnl=pnl.tolist(), confidence=confidence, horizon_days=1,
                          portfolio_value=request["nav"]))
    assert result["expected_shortfall"] == pytest.approx(tail["expected_shortfall"], rel=1e-10)
    assert result["tail_probability_mass"] == tail["tail_probability_mass"]


def test_hand_calculated_fractional_tail():
    """Four scenarios at 62.5%: tail mass 1.5, worst loss weight 1, next 0.5."""
    request = dict(**meta(), nav=100, positions=[position("a", "A", 100), position("b", "B", 100)],
                   assets=["A", "B"], horizon_days=1, confidence=0.625,
                   returns=[[-0.6, -0.4], [-0.1, 0.6], [0.2, -0.7], [0.3, 0.3]])
    # losses per scenario: a = 60,10,-20,-30; b = 40,-60,70,-30; totals 100,-50,50,-60
    result = historical_es(request)
    assert result["expected_shortfall"] == pytest.approx((100 + 0.5 * 50) / 1.5)
    a, b = result["positions"]
    assert a["component_es"] == pytest.approx((60 + 0.5 * -20) / 1.5)
    assert b["component_es"] == pytest.approx((40 + 0.5 * 70) / 1.5)
    assert [s["index"] for s in result["tail_scenarios"]] == [0, 2]
    assert result["degraded"]  # tail mass 1.5 is below the reporting threshold


def test_component_es_is_the_derivative_of_historical_es():
    request = historical(400, 0.97)
    base = historical_es(request)
    for i, row in enumerate(base["positions"]):
        h = 1e-6 * abs(row["market_value"])
        bumped = json.loads(json.dumps(request))
        bumped["positions"][i]["market_value"] += h
        slope = (historical_es(bumped)["expected_shortfall"] - base["expected_shortfall"]) / h
        assert slope * row["market_value"] == pytest.approx(row["component_es"], rel=1e-6)


def test_tied_tail_boundary_is_flagged():
    request = dict(**meta(), nav=100, positions=[position("a", "A", 100), position("b", "B", 100)],
                   assets=["A", "B"], horizon_days=1, confidence=0.75,
                   returns=[[-0.5, 0.0], [0.0, -0.5], [0.1, 0.1], [0.2, 0.2]])
    result = historical_es(request)
    assert "straddle" in result["degraded_reason"]
    assert result["expected_shortfall"] == pytest.approx(50)


def test_large_sample_is_not_degraded_and_positions_need_data():
    assert not historical_es(historical(1000, 0.975))["degraded"]
    request = historical()
    request["positions"].append(position("p5", "Z", 1))
    with pytest.raises(ValueError, match="no data: Z"):
        historical_es(request)


# Factor exposure ---------------------------------------------------------------

def factor_request(rows=120, noise=0.004):
    f = RNG.normal(0, [0.01, 0.005], (rows, 2))
    betas = np.array([[1.2, -0.3], [0.8, 0.5], [0.1, 1.0]])
    r = 0.0002 + f @ betas.T + RNG.normal(0, noise, (rows, 3))
    return dict(**meta(), **book(), assets=["A", "B", "C"], returns=r.tolist(), horizon_days=1,
                factors=["MKT", "RATES"], factor_returns=f.tolist()), betas


def test_noiseless_returns_recover_betas_and_have_no_idiosyncratic_variance():
    request, betas = factor_request(noise=0)
    result = factor_exposure(request)
    for i, asset in enumerate("ABC"):
        assert list(result["assets"][asset]["betas"].values()) == pytest.approx(betas[i], abs=1e-12)
        assert result["assets"][asset]["alpha"] == pytest.approx(0.0002, abs=1e-12)
    assert result["variance"]["idiosyncratic"] == pytest.approx(0, abs=1e-12)
    assert result["systematic_share"] == pytest.approx(1, rel=1e-10)


def test_betas_match_scikit_learn_and_variance_parts_add_up():
    request, _ = factor_request()
    result = factor_exposure(request)
    r, f = np.asarray(request["returns"]), np.asarray(request["factor_returns"])
    fit = LinearRegression().fit(f, r)
    for i, asset in enumerate("ABC"):
        assert list(result["assets"][asset]["betas"].values()) == pytest.approx(fit.coef_[i], rel=1e-9)
        single = LinearRegression().fit(f, r[:, i])
        assert result["assets"][asset]["r_squared"] == pytest.approx(single.score(f, r[:, i]), rel=1e-9)
    exposure = np.array([700, -300, 100])  # A carries p1 + p3
    v = result["variance"]
    assert v["total"] == pytest.approx(np.var(r @ exposure, ddof=1), rel=1e-12)
    assert v["systematic"] + v["idiosyncratic"] == pytest.approx(v["total"], rel=1e-10)
    assert v["specific"] + v["residual_cross"] == pytest.approx(v["idiosyncratic"], rel=1e-12)
    loading = fit.coef_.T @ exposure
    assert list(result["portfolio_factor_exposure"].values()) == pytest.approx(loading, rel=1e-9)
    assert list(result["portfolio_factor_beta"].values()) == pytest.approx(loading / 1000, rel=1e-9)


def test_collinear_factors_and_short_histories_are_refused():
    request, _ = factor_request()
    request["factor_returns"] = [[x, 2 * x] for x, _ in request["factor_returns"]]
    with pytest.raises(ValueError, match="collinear"):
        factor_exposure(request)
    short, _ = factor_request(rows=3)
    with pytest.raises(ValidationError):
        factor_exposure(short)
    mismatched, _ = factor_request()
    mismatched["factor_returns"] = mismatched["factor_returns"][:-1]
    with pytest.raises(ValidationError):
        factor_exposure(mismatched)


# Examples and the artifact checker ------------------------------------------------

CHECKER = ROOT / "plugins/risk-desk/skills/risk-attribution/scripts/check_artifact.py"
EXAMPLES = [("decomposition_covariance.json", covariance_estimate),
            ("decomposition_parametric.json", parametric_var),
            ("decomposition_historical.json", historical_es),
            ("decomposition_factor.json", factor_exposure)]


def checker():
    spec = importlib.util.spec_from_file_location("check_artifact", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name,handler", EXAMPLES)
def test_examples_are_synthetic_undegraded_and_pass_the_checker(name, handler, tmp_path, capsys):
    payload = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
    result = handler(payload)
    assert result["data_mode"] == "synthetic" and not result["degraded"]
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert checker().main(str(path)) == 0
    assert capsys.readouterr().out.startswith("OK ")


@pytest.mark.parametrize("name,handler,break_it", [
    ("decomposition_parametric.json", parametric_var, lambda r: r["positions"][0].update(component_var=0)),
    ("decomposition_historical.json", historical_es, lambda r: r.update(expected_shortfall=1)),
    ("decomposition_factor.json", factor_exposure, lambda r: r["variance"].update(systematic=0)),
    ("decomposition_covariance.json", covariance_estimate, lambda r: r["covariance"][0].__setitem__(1, 9)),
])
def test_checker_fails_an_artifact_whose_parts_do_not_add_up(name, handler, break_it, tmp_path, capsys):
    result = handler(json.loads((ROOT / "examples" / name).read_text(encoding="utf-8")))
    break_it(result)
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert checker().main(str(path)) == 1
    assert capsys.readouterr().out.startswith("FAIL ")
